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

from typing import ClassVar, Sequence
from uuid import UUID

from sqlmodel import and_, or_, select
from starlette.requests import Request
from starlette_admin.auth import AdminUser, AuthProvider, LoginFailed

from .db import AsyncSessionMaker
from .models.users import StarletteAdminUser, User


# See https://jowilf.github.io/starlette-admin/user-guide/auth/#authprovider-built-in-sign-in-page
class StarletteAdminAuthProvider(AuthProvider):

    SESSION_IDENTIFIER: ClassVar[str] = 'starlette_admin_session_uuid'

    session_maker: AsyncSessionMaker

    def __init__(self,
                 session_maker: AsyncSessionMaker,
                 login_path: str = "/login",
                 logout_path: str = "/logout",
                 allow_routes: Sequence[str] | None = None) -> None:
        super().__init__(login_path=login_path, logout_path=logout_path, allow_routes=allow_routes)
        self.session_maker = session_maker


    async def login(self, username: str, password: str, remember_me: bool, request: Request) -> None:
        # NOTE: 'username' here is meant as User.username or User.email
        async with self.session_maker() as session:
            query = select(User).where(and_(or_(User.username == username, User.email == username), User.active == True, User.admin == True))
            user: User | None = (await session.scalars(query)).first()
            if not user or not user.check_password(password):
                raise LoginFailed('Invalid credentials')
            request.session[StarletteAdminAuthProvider.SESSION_IDENTIFIER] = str(user.id)
            return None

    async def authenticate(self, request: Request) -> AdminUser | None:
        uuid_str: str | None = request.session.get(StarletteAdminAuthProvider.SESSION_IDENTIFIER)
        if not uuid_str:
            return None
        try:
            uuid: UUID = UUID(uuid_str)
        except ValueError as ve:
            return None
        async with self.session_maker() as session:
            query = select(User).where(and_(User.id == uuid))
            user: User | None = (await session.scalars(query)).first()
            if not user:
                return None
            return StarletteAdminUser(user)

    async def logout(self, request: Request) -> None:
        request.session.clear()
        return None
