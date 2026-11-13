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

from datetime import datetime
from typing import Annotated, ClassVar, Final, TypeAlias
from uuid import UUID, uuid4

from pydantic import SecretStr, StringConstraints
from sqlmodel import Field, SQLModel

from ...sqlmodel.secret_string import SecretStringConstraints


ACCESS_KEY_ID_LENGTH: Final[int] = 26


ACCESS_KEY_ID_PATTERN: Final[str] = r'^GK[0-9a-f]{' + str(ACCESS_KEY_ID_LENGTH - 2) + r'}$'  # Case-sensitive


AccessKeyId: TypeAlias = Annotated[SecretStr,
                                   SecretStringConstraints(min_length=ACCESS_KEY_ID_LENGTH,
                                                           max_length=ACCESS_KEY_ID_LENGTH,
                                                           pattern=ACCESS_KEY_ID_PATTERN)]


SECRET_ACCESS_KEY_LENGTH: Final[int] = 64


SECRET_ACCESS_KEY_PATTERN: Final[str] = r'^[0-9a-f]{' + str(SECRET_ACCESS_KEY_LENGTH) + r'}$'  # Case-sensitive


SecretAccessKey: TypeAlias = Annotated[SecretStr,
                                       SecretStringConstraints(min_length=SECRET_ACCESS_KEY_LENGTH,
                                                               max_length=SECRET_ACCESS_KEY_LENGTH,
                                                               pattern=SECRET_ACCESS_KEY_PATTERN)]


NAME_LENGTH: Final[int] = 60


Name: TypeAlias = Annotated[str, StringConstraints(min_length=1, max_length=NAME_LENGTH)]


# See https://git.deuxfleurs.fr/garage-sdk/garage-admin-sdk-python/src/branch/main-v2/docs/GetKeyInfoResponse.md
class AccessKey(SQLModel, table=True):
    NAME_LENGTH: ClassVar[int] = 60

    __tablename__ = 'garage_access_keys'

    id: UUID | None = Field(default_factory=uuid4, primary_key=True, index=True, title='UUID')
    access_key_id: AccessKeyId = Field(title='Access Key ID')
    # buckets: list[KeyInfoBucketResponse] # see https://git.deuxfleurs.fr/garage-sdk/garage-admin-sdk-python/src/branch/main-v2/docs/KeyInfoBucketResponse.md
    created: datetime | None = Field(None, title='Creation Time')
    expiration: datetime | None = Field(None, title='Expiration Time')
    expired: bool = Field(False, title='Expired')
    name: Name = Field(title='Name')
    permissions_create_bucket: bool = Field(False, title='Create Bucket Permission')
    secret_access_key: SecretAccessKey | None = Field(None, title='Secret Access Key')
