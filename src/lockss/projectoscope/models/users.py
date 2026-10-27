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
from typing import Final, Self
from uuid import UUID, uuid4

from pydantic import EmailStr, ModelWrapValidatorHandler, model_validator
from sqlmodel import Field, Relationship
from starlette.requests import Request
from starlette_admin.auth import AdminUser

from . import Handle, StrictSQLModel, make_field_error
from .organizations import Organization


BCRYPT_HASH_LENGTH: Final[int] = 60


BCRYPT_MAX_BYTES: Final[int] = 72


class UserBase(StrictSQLModel):
    handle: Handle = Field(nullable=False, unique=True, index=True, title='User Handle')
    first_name: str = Field(nullable=False, min_length=1, max_length=60, title='First Name')
    last_name: str = Field(nullable=False, min_length=1, max_length=60, title='Last Name')
    email: EmailStr = Field(nullable=False, unique=True, index=True, max_length=60, title='E-mail')
    active: bool = Field(default=True, title='Active')
    admin: bool = Field(default=False, title='Administrator')
    superuser: bool = Field(default=False, title='Superuser')

    # Not a computed_field, just a convenience method
    def full_name(self) -> str:
        return f'{self.first_name} {self.last_name}'

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
    hashed_password: str = Field(nullable=False, min_length=BCRYPT_HASH_LENGTH, max_length=BCRYPT_HASH_LENGTH, repr=False)

    organization_id: UUID | None = Field(default=None, foreign_key='organizations.id')
    organization: Organization | None = Relationship(back_populates='users')

    def check_password(self, plaintext_password: str) -> bool:
        return bcrypt.checkpw(plaintext_password.encode()[:BCRYPT_MAX_BYTES], self.hashed_password.encode()[:BCRYPT_MAX_BYTES])

    def set_password(self, plaintext_password: str) -> None:
        self.hashed_password = User.hash_password(plaintext_password)

    def __admin_repr__(self, request: Request) -> str:
        return f'{self.full_name()} ({self.handle})'

    @staticmethod
    def hash_password(plaintext_password: str) -> str:
        return bcrypt.hashpw(plaintext_password.encode()[:BCRYPT_MAX_BYTES], bcrypt.gensalt()).decode()


class StarletteAdminUser(AdminUser):

    user: User

    def __init__(self, user: User) -> None:
        super().__init__(username=user.handle, photo_url=None)
        self.user = user
