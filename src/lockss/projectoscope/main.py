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

from datetime import datetime, timedelta, UTC
from secrets import token_bytes
from typing import Annotated

from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response, status as HttpStatus
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import APIKeyCookie, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_ldap import LDAPAuth, LDAPConnectionError, LDAPSettings, LDAPUser, get_current_user as ldap_get_current_user, require_groups
from jwt import PyJWTError, decode as jwt_decode, encode as jet_encode


_ONE_TIME_SECRET_KEY: bytes = token_bytes(32)


JWT_ALGORITHM: str = 'HS256'


JWT_DURATION: timedelta = timedelta(hours=8)


SESSION_COOKIE_NAME: str = 'projectoscope_session'


cookie_scheme: APIKeyCookie = APIKeyCookie(name=SESSION_COOKIE_NAME)


conditional_cookie_scheme: APIKeyCookie = APIKeyCookie(name=SESSION_COOKIE_NAME, auto_error=False)


settings = LDAPSettings(
    ldap_url='ldaps://sul-lockss-thibvm1.stanford.edu:636',
    ldap_base_dn=(bdn := 'dc=lockss,dc=org'),
    bind_dn=f'uid=admin,cn=users,cn=accounts,{bdn}', # FIXME
    tls_ca_cert_file='ca.crt',
    user_search_base=f'cn=users,cn=accounts,{bdn}',
    group_search_base=f'cn=groups,cn=accounts,{bdn}',
)


ldap_auth = LDAPAuth(settings)


app = FastAPI(lifespan=ldap_auth.lifespan)
app.mount('/static/css', StaticFiles(directory='src/lockss/projectoscope/static/css'), name='css')
app.mount('/static/images', StaticFiles(directory='src/lockss/projectoscope/static/images'), name='images')
app.mount('/static/js', StaticFiles(directory='src/lockss/projectoscope/static/js'), name='js')
templates = Jinja2Templates(directory='src/lockss/projectoscope/templates')


async def get_current_user(token: Annotated[str, Depends(cookie_scheme)]) -> LDAPUser:
    try:
        payload = jwt_decode(token, _ONE_TIME_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except PyJWTError as je:
        raise HTTPException(status_code=HttpStatus.HTTP_401_UNAUTHORIZED, detail='Invalid token')
    try:
        return await ldap_get_current_user(HTTPBasicCredentials(username=payload.get('sub'), password=payload.get('x-pas')))
    except LDAPConnectionError as lce:
        raise HTTPException(HttpStatus.HTTP_503_SERVICE_UNAVAILABLE, detail='LDAP backend unavailable') from lce
    except HTTPException as he:
        # Intercept the WWW-Authenticate:Basic header fastapi-ldap returns with 401
        if he.status_code == HttpStatus.HTTP_401_UNAUTHORIZED and he.headers:
            # he.headers is a Mapping, not a MutableMapping
            he.headers = {k: v for k, v in he.headers if k != 'WWW-Authenticate'} or None
        raise


async def get_current_user_or_none(token: Annotated[str | None, Depends(conditional_cookie_scheme)]) -> LDAPUser | None:
    if token is None:
        return None
    try:
        return await get_current_user(token)
    except HTTPException as he:
        if he.status_code == HttpStatus.HTTP_401_UNAUTHORIZED:
            return None
        raise


def redirect_to_login() -> RedirectResponse:
    return RedirectResponse('/login', status_code=HttpStatus.HTTP_303_SEE_OTHER)


@app.get('/')
def root(user: Annotated[LDAPUser | None, Depends(get_current_user)]) -> RedirectResponse:
    return RedirectResponse('/home' if user else '/login', status_code=HttpStatus.HTTP_303_SEE_OTHER)


@app.get('/home')
def home(req: Request, user: LDAPUser = Depends(get_current_user)) -> HTMLResponse:
    return templates.TemplateResponse(req, 'layout-sidebar-left.html', context=dict(ldap_user=user))


@app.get('/login', response_model=None)
def login(user: Annotated[LDAPUser | None, Depends(get_current_user_or_none)], req: Request) -> RedirectResponse | HTMLResponse:
    return RedirectResponse('/home', status_code=HttpStatus.HTTP_303_SEE_OTHER) if user else templates.TemplateResponse(req, 'login.html')


@app.post("/login", response_model=None)
async def login(form_data: Annotated[HTTPBasicCredentials, Form()], req: Request) -> RedirectResponse | HTMLResponse:
    try:
        ldap_user: LDAPUser = await ldap_get_current_user(form_data)
    except LDAPConnectionError as lce:
        raise HTTPException(HttpStatus.HTTP_503_SERVICE_UNAVAILABLE, detail='LDAP backend unavailable') from lce
    except HTTPException as he:
        if he.status_code == (sc401 := HttpStatus.HTTP_401_UNAUTHORIZED):
            return templates.TemplateResponse(req, 'login.html', status_code=sc401, context={'alert_type': 'danger', 'alert': 'Error: Invalid username or password.'})
        raise he
    payload = {'sub': form_data.username, 'x-pas': form_data.password, 'exp': (exp := datetime.now(UTC) + JWT_DURATION)}
    token: str = jet_encode(payload, _ONE_TIME_SECRET_KEY, JWT_ALGORITHM)
    resp = RedirectResponse('/home', status_code=HttpStatus.HTTP_303_SEE_OTHER)
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
