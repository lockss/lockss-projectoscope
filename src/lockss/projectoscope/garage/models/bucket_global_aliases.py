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

from typing import Annotated, Final, TypeAlias
from uuid import UUID, uuid4

from pydantic import ConfigDict, StringConstraints
from sqlmodel import Field, Relationship, SQLModel

from .buckets import Bucket


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
BUCKET_NAME_REGEX: Final[str] = r'(?!(^(?:xn--|sthree-|amzn-s3-demo-)|.+(?:-s3alias|--ol-s3|.mrap|--x-s3|--table-s3|-an)$))^[a-z0-9][a-z0-9-]{1,' + str(BUCKET_NAME_MAX_LENGTH - 2) + r'}[a-z0-9]$'


BucketName: TypeAlias = Annotated[str,
                                  StringConstraints(min_length=BUCKET_NAME_MIN_LENGTH,
                                                    max_length=BUCKET_NAME_MAX_LENGTH,
                                                    pattern=BUCKET_NAME_REGEX)]


class BucketGlobalAlias(SQLModel, table=True):
    model_config = ConfigDict(regex_engine='python-re')

    __tablename__ = 'garage_bucket_global_aliases'

    id: UUID | None = Field(default_factory=uuid4, primary_key=True, index=True, title='UUID')
    alias: BucketName = Field(title='Global Alias')

    bucket_id: UUID | None = Field(default=None, foreign_key='garage_buckets.id')
    bucket: Bucket | None = Relationship(back_populates='global_aliases')
