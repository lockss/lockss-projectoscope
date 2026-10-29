#!/usr/bin/env python3

# Copyright (c) 2000-2026, Board of Trustees of Leland Stanford Jr. University
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
# may be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from contextlib import asynccontextmanager, AsyncExitStack
from datetime import datetime, timedelta, UTC
import os
from secrets import token_bytes
from typing import Annotated, Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import APIKeyCookie, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_ldap import LDAPAuth, LDAPConnectionError, LDAPSettings, LDAPUser, get_current_user as ldap_get_current_user
from jwt import PyJWTError, decode as jwt_decode, encode as jwt_encode
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import SQLModel
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_303_SEE_OTHER, HTTP_401_UNAUTHORIZED, HTTP_503_SERVICE_UNAVAILABLE, HTTP_403_FORBIDDEN
from starlette_admin.contrib.sqlmodel import Admin
from starlette_admin.views import Link

from .auth import StarletteAdminAuthProvider
from .db import AsyncSessionMaker, make_sqlalchemy_async_engine, make_sqlalchemy_async_session_maker
from .views.organizations import OrganizationView
from .views.preservation_projects import PreservationProjectView
from .views.users import UserView, ProfileView


load_dotenv()


class MyApp:

    engine: AsyncEngine
    session_maker: AsyncSessionMaker
    app: FastAPI
    templates: Jinja2Templates

    def __init__(self):
        self.engine = make_sqlalchemy_async_engine(echo=True)
        self.session_maker = make_sqlalchemy_async_session_maker(self.engine)
        self.app = FastAPI(lifespan=self.lifespan)
        self.app.mount('/static/css', StaticFiles(directory='src/lockss/projectoscope/static/css'), name='css')
        self.app.mount('/static/images', StaticFiles(directory='src/lockss/projectoscope/static/images'), name='images')
        self.app.mount('/static/js', StaticFiles(directory='src/lockss/projectoscope/static/js'), name='js')
        self.templates = Jinja2Templates(directory='src/lockss/projectoscope/templates')
        self.app.add_middleware(SessionMiddleware, secret_key=os.environ['STARLETTE_ADMIN_SECRET_KEY'])

        class MyAdmin(Admin):
            async def _find_object_or_404(self, request: Request, view: "BaseModelView", key: str | None, pk: str | None, action: str) -> Any:
                if isinstance(view, ProfileView) and key == 'profile' and (action == 'detail' or action == 'edit'):
                    upk = str(request.state.admin_user.user.id) # FIXME pk:str/pk:UUID inconsistencies
                    if pk and pk != upk:
                        raise HTTPException(HTTP_403_FORBIDDEN)
                    pk = upk
                return await super()._find_object_or_404(request, view, key, pk, action)

        admin = MyAdmin(self.engine, auth_provider=StarletteAdminAuthProvider(self.session_maker), title='Projectoscope Admin', secret_key=os.environ['STARLETTE_ADMIN_SECRET_KEY'])
        admin.add_view(PreservationProjectView())
        admin.add_view(OrganizationView())
        admin.add_view(UserView())
        admin.add_view(ProfileView()) # FIXME Would like to not be visible in the menu
        admin.add_link(Link(menu_label='My Profile', icon=ProfileView.icon, url=f'{admin.base_url}/{ProfileView.key}/detail'))
        admin.mount_to(self.app)

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        async with AsyncExitStack() as stack:
            await stack.enter_async_context(self.lifespan_db(app))
            await stack.enter_async_context(self.lifespan_ldap(app))
            yield

    @asynccontextmanager
    async def lifespan_db(self, app: FastAPI):
        async with self.engine.begin() as conn:
            # await conn.run_sync(SQLModel.metadata.drop_all)
            await conn.run_sync(SQLModel.metadata.create_all)
        yield
        await self.engine.dispose()

    @asynccontextmanager
    async def lifespan_ldap(self, app: FastAPI):
        async with LDAPAuth(LDAPSettings()).lifespan(app):
            yield
        pass


_ONE_TIME_SECRET_KEY: bytes = token_bytes(32)


JWT_ALGORITHM: str = 'HS256'


JWT_DURATION: timedelta = timedelta(hours=8)


SESSION_COOKIE_NAME: str = 'projectoscope_session'


cookie_scheme: APIKeyCookie = APIKeyCookie(name=SESSION_COOKIE_NAME)


conditional_cookie_scheme: APIKeyCookie = APIKeyCookie(name=SESSION_COOKIE_NAME, auto_error=False)


myapp: MyApp = MyApp()


app: FastAPI = myapp.app # To be auto-detectable by FastAPI


async def get_current_user(token: Annotated[str, Depends(cookie_scheme)]) -> LDAPUser:
    try:
        payload = jwt_decode(token, _ONE_TIME_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except PyJWTError as je:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail='Invalid token')
    try:
        return await ldap_get_current_user(HTTPBasicCredentials(username=payload.get('sub'), password=payload.get('x-pas')))
    except LDAPConnectionError as lce:
        raise HTTPException(HTTP_503_SERVICE_UNAVAILABLE, detail='LDAP backend unavailable') from lce
    except HTTPException as he:
        # Intercept the WWW-Authenticate:Basic header fastapi-ldap returns with 401
        if he.status_code == HTTP_401_UNAUTHORIZED and he.headers:
            # he.headers is a Mapping, not a MutableMapping
            he.headers = {k: v for k, v in he.headers if k != 'WWW-Authenticate'} or None
        raise


async def get_current_user_or_none(token: Annotated[str | None, Depends(conditional_cookie_scheme)]) -> LDAPUser | None:
    if token is None:
        return None
    try:
        return await get_current_user(token)
    except HTTPException as he:
        if he.status_code == HTTP_401_UNAUTHORIZED:
            return None
        raise


def redirect_to_login() -> RedirectResponse:
    return RedirectResponse('/login', status_code=HTTP_303_SEE_OTHER)


@app.get('/')
def root(user: Annotated[LDAPUser | None, Depends(get_current_user)]) -> RedirectResponse:
    return RedirectResponse('/home' if user else '/login', status_code=HTTP_303_SEE_OTHER)


@app.get('/home')
def home(req: Request, user: LDAPUser = Depends(get_current_user)) -> HTMLResponse:
    return myapp.templates.TemplateResponse(req, 'layout-sidebar-left.html', context=dict(ldap_user=user))


@app.get('/login', response_model=None)
def login(user: Annotated[LDAPUser | None, Depends(get_current_user_or_none)], req: Request) -> RedirectResponse | HTMLResponse:
    return RedirectResponse('/home', status_code=HTTP_303_SEE_OTHER) if user else myapp.templates.TemplateResponse(req, 'login.html')


@app.post("/login", response_model=None)
async def login(form_data: Annotated[HTTPBasicCredentials, Form()], req: Request) -> RedirectResponse | HTMLResponse:
    try:
        ldap_user: LDAPUser = await ldap_get_current_user(form_data)
    except LDAPConnectionError as lce:
        raise HTTPException(HTTP_503_SERVICE_UNAVAILABLE, detail='LDAP backend unavailable') from lce
    except HTTPException as he:
        if he.status_code == (sc401 := HTTP_401_UNAUTHORIZED):
            return myapp.templates.TemplateResponse(req, 'login.html', status_code=sc401, context={'alert_type': 'danger', 'alert': 'Error: Invalid username or password.'})
        raise he
    payload = {'sub': form_data.username, 'x-pas': form_data.password, 'exp': (exp := datetime.now(UTC) + JWT_DURATION)}
    token: str = jwt_encode(payload, _ONE_TIME_SECRET_KEY, JWT_ALGORITHM)
    resp = RedirectResponse('/home', status_code=HTTP_303_SEE_OTHER)
    resp.set_cookie(key=SESSION_COOKIE_NAME, value=token, httponly=True, secure=False, samesite='lax', expires=exp) # FIXME
    return resp


@app.get('/logout')
def logout() -> RedirectResponse:
    resp: RedirectResponse = redirect_to_login()
    resp.delete_cookie(SESSION_COOKIE_NAME)
    return resp


@app.get('/ldap-test')
async def ldap_test(user: LDAPUser = Depends(get_current_user)):
    return user
