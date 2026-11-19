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

from datetime import UTC, datetime
from random import randrange
from re import Pattern, compile as re_compile
from typing import Annotated, ClassVar, Final, TypeAlias
from uuid import UUID, uuid4

from pydantic import StringConstraints
from starlette.requests import Request
from sqlmodel import Field, Relationship, SQLModel

from ...hq.models.users import User
from .bucket_access_key_links import BucketAccessKeyLink


ACCESS_KEY_ID_LENGTH: Final[int] = 26


ACCESS_KEY_ID_PATTERN: Final[Pattern[str]] = re_compile(r'^GK[0-9a-f]{' + str(ACCESS_KEY_ID_LENGTH - 2) + r'}$') # Case-sensitive


AccessKeyIdT: TypeAlias = Annotated[str,
                                    StringConstraints(min_length=ACCESS_KEY_ID_LENGTH,
                                                      max_length=ACCESS_KEY_ID_LENGTH,
                                                      pattern=ACCESS_KEY_ID_PATTERN)]


ACCESS_KEY_NAME_LENGTH: Final[int] = 60


AccessKeyNameT: TypeAlias = Annotated[str, StringConstraints(min_length=1, max_length=ACCESS_KEY_NAME_LENGTH)]


# See https://git.deuxfleurs.fr/garage-sdk/garage-admin-sdk-python/src/branch/main-v2/docs/GetKeyInfoResponse.md
class AccessKey(SQLModel, table=True):
    __tablename__ = 'garage_access_keys'

    id: UUID | None = Field(default_factory=uuid4, primary_key=True, index=True, title='UUID')
    access_key_identifier: AccessKeyIdT | None = Field(default=None, title='Access Key ID')  # known as 'access_key_id' in their definition
    created: datetime | None = Field(default=None, title='Creation Time', description='Understood in UTC')
    expiration: datetime | None = Field(default_factory=lambda: (now := datetime.now(UTC)).replace(year=now.year + 1), title='Expiration Time', description='Understood in UTC')
    expired: bool = Field(False, title='Expired')
    name: AccessKeyNameT | None = Field(default=None, title='Name')

    user_id: UUID | None = Field(default=None, foreign_key='users.id', title='Associated User')
    user: User | None = Relationship()

    bucket_links: list[BucketAccessKeyLink] = Relationship(back_populates='access_key')

    def __admin_repr__(self, request: Request) -> str:
        return f'{self.access_key_identifier} ({self.name})'

    @staticmethod
    def generate_name(user: User) -> AccessKeyNameT:
        return f'uk-{user.handle}-{randrange(100000):05d}' # max length: 29
