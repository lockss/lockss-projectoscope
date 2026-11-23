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

from collections.abc import Sequence
from dataclasses import replace
from typing import Any, ClassVar, cast

from garage_admin_sdk import BucketApi, CreateBucketRequest, GetBucketInfoResponse
from sqlalchemy import Select, func
from sqlmodel import and_
from starlette.requests import Request
from starlette_admin import BaseField, DateTimeField, RelationField, RequestAction, StringField, UUIDField

from ...config import GarageComponentSettings
from ...hq.models.users import User, user_
from ..models.access_keys import AccessKey
from ..models.bucket_access_key_links import BucketAccessKeyLink
from ..models.buckets import Bucket
from ..views.bucket_access_key_links import BucketAccessKeyLinkInlineView
from . import GarageComponentView


class BucketView(GarageComponentView):
    DATETIME_FORMAT: ClassVar[str] = '%Y-%m-%d %H:%M:%S'

    icon = 'fa-solid fa-bucket'
    _can_delete = False
    _can_import = False

    fields = [
        UUIDField('id',
                  version=4,
                  label=Bucket.model_fields['id'].title),
        StringField('bucket_identifier',
                    copy_to_clipboard=True,
                    label=Bucket.model_fields['bucket_identifier'].title),
        StringField('global_alias',
                    label=Bucket.model_fields['global_alias'].title),
        DateTimeField('created',
                      output_format=DATETIME_FORMAT,
                      label=(crd := Bucket.model_fields['created']).title,
                      help_text=crd.description),
    ]

    inlines = [BucketAccessKeyLinkInlineView]

    exclude_fields_from_create = ['bucket_identifier', 'global_alias', 'created']

    exclude_fields_from_detail = []

    exclude_fields_from_edit = []

    _non_editable_fields = ['bucket_identifier', 'global_alias', 'created']

    exclude_fields_from_export = []

    exclude_fields_from_list = ['id', 'created']

    def __init__(self, garage_settings: GarageComponentSettings, *args, **kwargs) -> None:
        super().__init__(garage_settings, Bucket, *args, **kwargs)

    def is_accessible(self, request: Request) -> bool:
        return user_(request).active

    def get_list_query(self, request: Request) -> Select:
        if (user := user_(request)).admin:
            return super().get_list_query(request)
        else:
            return Select(Bucket, BucketAccessKeyLink, AccessKey).where(and_(Bucket.id == BucketAccessKeyLink.bucket_id, BucketAccessKeyLink.access_key_id == AccessKey.id, AccessKey.user_id == user.id))

    def get_count_query(self, request: Request) -> Select:
        if (user := user_(request)).admin:
            return super().get_count_query(request)
        else:
            return Select(func.count()).select_from(Bucket, BucketAccessKeyLink, AccessKey).where(and_(Bucket.id == BucketAccessKeyLink.bucket_id, BucketAccessKeyLink.access_key_id == AccessKey.id, AccessKey.user_id == user.id))

    async def before_create(self, request: Request, data: dict[str, Any], obj: Any) -> None:
        bucket: Bucket = cast(Bucket, obj)
        user: User = user_(request)
        bucket.global_alias = Bucket.generate_global_alias(user)
        with self.api_client_context as api_client:
            # FIXME requires try/except
            api_instance: BucketApi = BucketApi(api_client)
            cbr: CreateBucketRequest = CreateBucketRequest(globalAlias=bucket.global_alias)
            resp: GetBucketInfoResponse = api_instance.create_bucket(cbr)
        bucket.bucket_identifier = resp.id
        bucket.created = resp.created
