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

import bcrypt
from typing import Self
from uuid import UUID, uuid4

from pydantic import EmailStr, ModelWrapValidatorHandler, model_validator
from sqlmodel import Field, SQLModel
from starlette_admin.auth import AdminUser

from . import make_field_error


class UserBase(SQLModel):
    username: str = Field(nullable=False, unique=True, index=True, max_length=20, title='Username')
    display_name: str = Field(nullable=False, max_length=60, title='Name')
    email: EmailStr = Field(nullable=False, unique=True, index=True, max_length=60, title='E-mail')
    active: bool = Field(default=True, title='Active')
    admin: bool = Field(default=False, title='Administrator')
    superuser: bool = Field(default=False, title='Superuser')

    @model_validator(mode='wrap')
    @classmethod
    def _check_admin(cls, data: Self, handler: ModelWrapValidatorHandler[Self]) -> Self:
        mi: Self = handler(data)
        if mi.superuser and not mi.admin:
            raise make_field_error(cls, mi, ('admin', 'value_error', 'A user who is a superuser must also be an admin', None))
        return mi


class User(UserBase, table=True):
    __tablename__ = 'users'
    id: UUID | None = Field(default_factory=uuid4, primary_key=True, index=True, title='UUID')
    hashed_password: str = Field(nullable=False, max_length=60, repr=False)

    def check_password(self, plaintext_password: str) -> bool:
        return bcrypt.checkpw(plaintext_password.encode(), self.hashed_password.encode())

    def set_password(self, plaintext_password: str) -> None:
        self.hashed_password = User.hash_password(plaintext_password)

    @staticmethod
    def hash_password(plaintext_password: str) -> str:
        return bcrypt.hashpw(plaintext_password.encode(), bcrypt.gensalt()).decode()


class StarletteAdminUser(AdminUser):

    user: User

    def __init__(self, user: User) -> None:
        super().__init__(username=user.username, photo_url=None)
        self.user = user
