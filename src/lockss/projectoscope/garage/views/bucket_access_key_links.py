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

from typing import Any, cast

from garage_admin_sdk import ApiBucketKeyPerm, BucketKeyPermChangeRequest, GetBucketInfoResponse, PermissionApi
from starlette.requests import Request
from starlette_admin import BooleanField, RelationField

from ...starlette_admin.view import InlineView
from ..models.bucket_access_key_links import BucketAccessKeyLink
from ..models.buckets import Bucket


class BucketAccessKeyLinkInlineView(InlineView):
    model = BucketAccessKeyLink
    fk_attr = 'bucket_id'
    fields = [
        RelationField('access_key',
                      key='access-key',
                      label=BucketAccessKeyLink.model_fields['access_key_id'].title),
        BooleanField('read',
                     label=BucketAccessKeyLink.model_fields['read'].title),
        BooleanField('write',
                     label=BucketAccessKeyLink.model_fields['write'].title)
    ]

    async def before_create(self, request: Request, data: dict[str, Any], obj: Any) -> None:
        # Notes:
        # - data['access_key'] and link.access_key are initialized, but link.access_key_id is None
        # - data['bucket_id] and link.bucket_id are initialized, but data['bucket'] does not exist and link.bucket is None
        link: BucketAccessKeyLink = cast(BucketAccessKeyLink, obj)
        bucket: Bucket = await self.parent_view.find_by_pk(request, link.bucket_id.hex) # FIXME UUID inconsistencies
        with self.parent_view.api_client_context as api_client:
            # FIXME requires try/except
            permission_api: PermissionApi = PermissionApi(api_client)
            bkpcr: BucketKeyPermChangeRequest = BucketKeyPermChangeRequest(accessKeyId=cast(str, link.access_key.access_key_identifier),
                                                                           bucketId=cast(str, bucket.bucket_identifier),
                                                                           permissions=ApiBucketKeyPerm(owner=False,
                                                                                                        read=link.read,
                                                                                                        write=link.write))
            gbir: GetBucketInfoResponse = permission_api.allow_bucket_key(bkpcr)
            # FIXME Should check that request was honored?

    async def before_edit(self, request: Request, data: dict[str, Any], obj: Any) -> None:
        link: BucketAccessKeyLink = cast(BucketAccessKeyLink, obj)
        bucket: Bucket = await self.parent_view.find_by_pk(request, link.bucket_id.hex) # FIXME UUID inconsistencies
        read: bool = data.get('read', False)
        write: bool = data.get('write', False)
        print(f'{"#" * 500} {read=} {write=}')
        with self.parent_view.api_client_context as api_client:
            # FIXME requires try/except
            permission_api: PermissionApi = PermissionApi(api_client)
            bkpcr_allow: BucketKeyPermChangeRequest = BucketKeyPermChangeRequest(accessKeyId=cast(str, link.access_key.access_key_identifier),
                                                                                 bucketId=cast(str, bucket.bucket_identifier),
                                                                                 permissions=ApiBucketKeyPerm(owner=False,
                                                                                                              read=link.read,
                                                                                                              write=link.write))
            gbir_allow: GetBucketInfoResponse = permission_api.allow_bucket_key(bkpcr_allow)
            bkpcr_deny: BucketKeyPermChangeRequest = BucketKeyPermChangeRequest(accessKeyId=cast(str, link.access_key.access_key_identifier),
                                                                                bucketId=cast(str, bucket.bucket_identifier),
                                                                                permissions=ApiBucketKeyPerm(owner=True,            # meaning, deny owner
                                                                                                             read=not link.read,    # meaning, deny read
                                                                                                             write=not link.write)) # meaning, deny write
            gbir_deny: GetBucketInfoResponse = permission_api.deny_bucket_key(bkpcr_deny)
            # FIXME Should check that request was honored?

    async def before_delete(self, request: Request, obj: Any) -> None:
        link: BucketAccessKeyLink = cast(BucketAccessKeyLink, obj)
        with self.parent_view.api_client_context as api_client:
            # FIXME requires try/except
            permission_api: PermissionApi = PermissionApi(api_client)
            bkpcr: BucketKeyPermChangeRequest = BucketKeyPermChangeRequest(accessKeyId=cast(str, link.access_key.access_key_identifier),
                                                                           bucketId=cast(str, link.bucket.bucket_identifier),
                                                                           permissions=ApiBucketKeyPerm(owner=True,  # meaning, deny owner
                                                                                                        read=True,   # meaning, deny read
                                                                                                        write=True)) # meaning, deny write
            gbir: GetBucketInfoResponse = permission_api.deny_bucket_key(bkpcr)
            # FIXME Should check that request was honored?
