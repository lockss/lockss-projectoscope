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

from typing import Self, TYPE_CHECKING
from uuid import UUID

from pydantic import ModelWrapValidatorHandler, model_validator
from sqlmodel import Field, Relationship, SQLModel

from ...pydantic.errors import make_field_error

if TYPE_CHECKING:
    from .access_keys import AccessKey
    from .buckets import Bucket


class BucketAccessKeyLink(SQLModel, table=True):
    __tablename__ = 'garage_bucket_access_key_links'

    bucket_id: UUID | None = Field(default=None, foreign_key='garage_buckets.id', primary_key=True, title='Bucket ID')
    access_key_id: UUID | None = Field(default=None, foreign_key='garage_access_keys.id', primary_key=True, title='Access Key ID')
    # owner: bool = Field(default=False, title='Owner')
    read: bool = Field(default=False, title='Read')
    write: bool = Field(default=False, title='Write')

    bucket: 'Bucket' = Relationship(back_populates='access_key_links')
    access_key: 'AccessKey' = Relationship(back_populates='bucket_links')

    @model_validator(mode='wrap')
    @classmethod
    def _check_admin(cls, data: Self, handler: ModelWrapValidatorHandler[Self]) -> Self:
        mi: Self = handler(data)
        if not (mi.read or mi.write):
            raise make_field_error(cls, mi, ('read', 'value_error', "At least one of 'read' or 'write' should be true", None), ('write', 'value_error', "At least one of 'read' or 'write' should be true", None))
        return mi
