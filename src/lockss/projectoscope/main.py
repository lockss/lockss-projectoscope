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

from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path
import sys
from typing import cast

from dotenv import load_dotenv
from fastapi import FastAPI
from lockss.pybasic.errorutil import InternalError
from lockss.pybasic.fileutil import PathOrStr, path
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import SQLModel
from starlette.middleware.sessions import SessionMiddleware
from starlette_admin.auth import BaseAuthProvider
import uvicorn
import yaml

from .admin import ProjectoscopeAdmin
from .component import Component
from .config import HqSettings, ProfileSettings, ProjectoscopeSettings, component_sort_key, GarageComponentSettings
from .db import vet_database_url
from .garage import GarageComponent
from .hq import HqComponent
from .profile import ProfileComponent
from .sqlmodel.asyncio import AsyncSessionMaker, make_async_engine, make_async_session_maker
from .starlette_admin.auth import StarletteAdminAuthProvider


class Projectoscope:
    settings: ProjectoscopeSettings
    engine: AsyncEngine
    session_maker: AsyncSessionMaker
    auth_provider: BaseAuthProvider
    admin: ProjectoscopeAdmin
    api: FastAPI

    def __init__(self,
                 settings: ProjectoscopeSettings):
        self.settings = settings
        self.set_up_database()
        self.set_up_auth()
        self.set_up_admin()
        self.set_up_api()
        self.set_up_components()

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        async with AsyncExitStack() as stack:
            await stack.enter_async_context(self.lifespan_db(app))
            yield

    @asynccontextmanager
    async def lifespan_db(self, app: FastAPI):
        async with self.engine.begin() as conn:
            # await conn.run_sync(SQLModel.metadata.drop_all)
            await conn.run_sync(SQLModel.metadata.create_all)
        yield
        await self.engine.dispose()

    def set_up_admin(self) -> None:
        self.admin = ProjectoscopeAdmin(self)

    def set_up_api(self) -> None:
        self.api = FastAPI(lifespan=self.lifespan)
        self.api.add_middleware(SessionMiddleware, secret_key=self.settings.overseer.secret_key.get_secret_value())

    def set_up_auth(self) -> None:
        self.auth_provider = StarletteAdminAuthProvider(self.session_maker)

    def set_up_components(self) -> None:
        for settings in sorted(self.settings.components, key=component_sort_key):
            component: Component
            match typ := settings.type:
                case HqSettings.TYPE:
                    hq = HqComponent(self.settings.overseer, cast(HqSettings, settings))
                    hq.set_up_admin(self)
                    hq.set_up_api(self)
                case GarageComponentSettings.TYPE:
                    garage = GarageComponent(self.settings.overseer, cast(GarageComponentSettings, settings))
                    garage.set_up_admin(self)
                    garage.set_up_api(self)
                case _:
                    raise InternalError from ValueError(typ)
        if self.settings.is_hq():
            profile: ProfileComponent = ProfileComponent(self.settings.overseer, ProfileSettings())
            profile.set_up_admin(self)
            profile.set_up_api(self)
        else:
            self.admin.templates.context_processors.append(lambda req: {'overseer_url': self.settings.overseer.url})
        self.admin.mount_to(self.api)

    def set_up_database(self) -> None:
        database_url = vet_database_url(self.settings.overseer.database_url.get_secret_value())
        self.engine = make_async_engine(database_url, echo=True) # FIXME
        self.session_maker = make_async_session_maker(self.engine)


# @app.get('/')
# def root():
#     return {"message": "Welcome to Projectoscope"}


def load_settings(settings_file_path_or_str: PathOrStr) -> ProjectoscopeSettings:
    load_dotenv()
    settings_file_path: Path = path(settings_file_path_or_str)
    with settings_file_path.open() as settings_file:
        yaml_obj = yaml.safe_load(settings_file)
    return ProjectoscopeSettings.model_validate(yaml_obj)


def main() -> None:
    settings_arg: str = sys.argv[1:][0] if sys.argv[1:] else 'config/projectoscope.yaml'
    settings: ProjectoscopeSettings = load_settings(settings_arg)
    projectoscope = Projectoscope(settings)
    uvicorn.run(projectoscope.api,
                host=str(settings.host),
                port=settings.port,
                reload=False) # FIXME can't be True unless using import string
