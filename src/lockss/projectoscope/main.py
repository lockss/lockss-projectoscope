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
from pathlib import Path
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

from .config import HqSettings, ProjectoscopeSettings, controller_sort_key
from .db import vet_database_url
from .sqlmodel.asyncio import AsyncSessionMaker, make_async_engine, make_async_session_maker
from .starlette_admin.auth import StarletteAdminAuthProvider


class Projectoscope:

    settings: ProjectoscopeSettings
    engine: AsyncEngine
    session_maker: AsyncSessionMaker
    app: FastAPI
    auth_provider: BaseAuthProvider

    def __init__(self,
                 settings_file_path_or_str: PathOrStr):
        self.load_settings(settings_file_path_or_str)
        self.set_up_database()
        self.set_up_auth()
        self.set_up_app()
        self.set_up_controllers()
        self.set_up_scaffold()

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

    def load_settings(self, settings_file_path_or_str: PathOrStr) -> None:
        load_dotenv()
        settings_file_path: Path = path(settings_file_path_or_str)
        with settings_file_path.open() as settings_file:
            self.settings = ProjectoscopeSettings.model_validate(yaml.safe_load(settings_file))

    def set_up_app(self) -> None:
        self.app = FastAPI(lifespan=self.lifespan)
        self.app.add_middleware(SessionMiddleware, secret_key=self.settings.overseer.secret_key.get_secret_value())

    def set_up_auth(self) -> None:
        self.auth_provider = StarletteAdminAuthProvider(self.session_maker)

    def set_up_controllers(self) -> None:
        for settings in sorted(self.settings.controllers, key=controller_sort_key):
            match typ := settings.type:
                case HqSettings.TYPE:
                    from .hq import set_up_hq
                    set_up_hq(self.settings.overseer, cast(HqSettings, settings), self.app, self.engine, self.auth_provider)
                case _:
                    raise InternalError from ValueError(typ)

    def set_up_database(self) -> None:
        database_url = vet_database_url(self.settings.overseer.database_url.get_secret_value())
        self.engine = make_async_engine(database_url, echo=True) # FIXME
        self.session_maker = make_async_session_maker(self.engine)

    def set_up_scaffold(self) -> None:
        self.


projectoscope: Projectoscope = Projectoscope('config/projectoscope.yaml')


app: FastAPI = projectoscope.app # To be auto-detectable by FastAPI


@app.get('/')
def root():
    return {"message": "Welcome to Projectoscope"}


def main() -> None:
    print(f'{ "=" * (n := 32) } DEVELOPMENT MODE { "=" * n }') # FIXME
    uvicorn.run(f'{__name__}:app', host="127.0.0.1", port=8000, reload=True) # FIXME
