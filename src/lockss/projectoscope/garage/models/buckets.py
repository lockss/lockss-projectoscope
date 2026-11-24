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
from random import randrange
from re import Pattern, compile as re_compile
from typing import Annotated, Final, TypeAlias
from uuid import UUID, uuid4

from pydantic import ConfigDict, StringConstraints
from starlette.requests import Request
from sqlmodel import Field, Relationship, SQLModel

from ...hq.models.users import User
from .bucket_access_key_links import BucketAccessKeyLink


BUCKET_ID_LENGTH: Final[int] = 64


BUCKET_ID_PATTERN: Final[Pattern[str]] = re_compile(r'^[0-9a-f]{' + str(BUCKET_ID_LENGTH) + r'}$') # Case-sensitive


BucketId: TypeAlias = Annotated[str,
                                StringConstraints(min_length=BUCKET_ID_LENGTH,
                                                  max_length=BUCKET_ID_LENGTH,
                                                  pattern=BUCKET_ID_PATTERN)]


# See https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html
BUCKET_NAME_MIN_LENGTH: Final[int] = 3


BUCKET_NAME_MAX_LENGTH: Final[int] = 63


# This uses https://stackoverflow.com/a/50484916 but tweaked for the current (As of this writing) version of https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html
# "Bucket names must be between 3 (min) and 63 (max) characters long" -> r'^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$'
# "Bucket names can consist only of lowercase letters, numbers, periods (.), and hyphens (-)" but best practices avoid periods -> r'[a-z0-9-]'
# "Bucket names must begin and end with a letter or number" -> r'^[a-z0-9]' and r'[a-z0-9]$'
# "Bucket names must not contain two adjacent periods" but best practices avoid periods
# "Bucket names must not be formatted as an IP address (for example, 192.168.5.4)" but best practices avoid periods
# "Bucket names must not start with the prefix xn--", "Bucket names must not start with the prefix sthree-", "Bucket names must not start with the prefix amzn-s3-demo-" -> r'^(?:xn--|sthree-|amzn-s3-demo-)'
# "Bucket names must not end with the suffix -s3alias", "Bucket names must not end with the suffix --ol-s3", "Bucket names must not end with the suffix .mrap", "Bucket names must not end with the suffix --x-s3", "Bucket names must not end with the suffix --table-s3" -> r'.+(?:-s3alias|--ol-s3|.mrap|--x-s3|--table-s3)$'
# "Bucket names can only end with the suffix -an when you are creating buckets in your account regional namespace" which we don't intend -> r'-an$'
# "Buckets used with Amazon S3 Transfer Acceleration can't have periods (.) in their names" and best practices "Avoid using periods (.) in bucket names" -> no periods allowed
BUCKET_NAME_REGEX: Final[str] = r'(?!(^(?:xn--|sthree-|amzn-s3-demo-)|.+(?:-s3alias|--ol-s3|.mrap|--x-s3|--table-s3|-an)$))^[a-z0-9][-a-z0-9]{1,' + str(BUCKET_NAME_MAX_LENGTH - 2) + r'}[a-z0-9]$'


GlobalAliasT: TypeAlias = Annotated[str,
                                    StringConstraints(min_length=BUCKET_NAME_MIN_LENGTH,
                                                      max_length=BUCKET_NAME_MAX_LENGTH,
                                                      pattern=BUCKET_NAME_REGEX)]


# See https://git.deuxfleurs.fr/garage-sdk/garage-admin-sdk-python/src/branch/main-v2/docs/GetBucketInfoResponse.md
class Bucket(SQLModel, table=True):
    model_config = ConfigDict(regex_engine='python-re')

    __tablename__ = 'garage_buckets'

    id: UUID | None = Field(default_factory=uuid4, primary_key=True, index=True, title='UUID')
    bucket_identifier: BucketId | None = Field(default=None, title='Bucket ID') # known as 'id' in their definition
    # cors_rules: List[CorsRules] | None # see https://git.deuxfleurs.fr/garage-sdk/garage-admin-sdk-python/src/branch/main-v2/docs/CorsRule.md
    created: datetime | None = Field(default=None, title='Creation Time', description='Understood in UTC')
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

    global_alias: GlobalAliasT | None = Field(default=None, title='Global Alias')

    access_key_links: list[BucketAccessKeyLink] = Relationship(back_populates='bucket')

    def __admin_repr__(self, request: Request) -> str:
        return f'{self.bucket_identifier} ({self.global_alias})'

    @staticmethod
    def generate_global_alias(user: User) -> GlobalAliasT:
        return f'ub-{user.handle}-{randrange(100000):05d}' # max length: 29
