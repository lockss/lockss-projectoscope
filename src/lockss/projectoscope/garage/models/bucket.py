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
from re import Pattern, compile as re_compile
from typing import Annotated, Final, TypeAlias, TYPE_CHECKING
from uuid import UUID, uuid4

from pydantic import StringConstraints
from sqlmodel import Field, Relationship, SQLModel

from .bucket_access_key_link import BucketAccessKeyLink

if TYPE_CHECKING:
    from .bucket_global_alias import BucketGlobalAlias


BUCKET_ID_LENGTH: Final[int] = 64


BUCKET_ID_PATTERN: Final[Pattern[str]] = re_compile(r'^[0-9a-f]{' + str(BUCKET_ID_LENGTH) + r'}$') # Case-sensitive


BucketId: TypeAlias = Annotated[str,
                                StringConstraints(min_length=BUCKET_ID_LENGTH,
                                                  max_length=BUCKET_ID_LENGTH,
                                                  pattern=BUCKET_ID_PATTERN)]


# See https://git.deuxfleurs.fr/garage-sdk/garage-admin-sdk-python/src/branch/main-v2/docs/GetBucketInfoResponse.md
class Bucket(SQLModel, table=True):
    __tablename__ = 'garage_buckets'

    id: UUID | None = Field(default_factory=uuid4, primary_key=True, index=True, title='UUID')
    bucket_identifier: BucketId = Field(title='Bucket ID') # known as 'id' in their definition
    # cors_rules: List[CorsRules] | None # see https://git.deuxfleurs.fr/garage-sdk/garage-admin-sdk-python/src/branch/main-v2/docs/CorsRule.md
    created: datetime | None = Field(None, title='Creation Time')
    # global_aliases: list[str] | None = Field(None, title='Global Aliases')
    # keys: List[GetBucketInfoKey] # see https://git.deuxfleurs.fr/garage-sdk/garage-admin-sdk-python/src/branch/main-v2/docs/GetBucketInfoKey.md
    # lifecycle_rules: List[LifeCycleRule] # see https://git.deuxfleurs.fr/garage-sdk/garage-admin-sdk-python/src/branch/main-v2/docs/LifecycleRule.md
    # objects: int
    # quotas: List[ApiBucketQuotas] # see https://git.deuxfleurs.fr/garage-sdk/garage-admin-sdk-python/src/branch/main-v2/docs/ApiBucketQuotas.md
    # unfinished_multipart_upload_bytes: int
    # unfinished_multipart_upload_parts: int
    # unfinished_multipart_uploads: int
    # unfinished_uploads: int
    # website_access: bool
    # website_config: GetBucketInfoWebsiteResponse # see https://git.deuxfleurs.fr/garage-sdk/garage-admin-sdk-python/src/branch/main-v2/docs/GetBucketInfoWebsiteResponse.md

    access_key_links: list[BucketAccessKeyLink] = Relationship(back_populates='bucket')

    global_aliases: list['BucketGlobalAlias'] = Relationship(back_populates='bucket')
