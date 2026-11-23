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

from garage_admin_sdk import BucketApi, CreateBucketRequest, GetBucketInfoResponse
from starlette.requests import Request
from starlette_admin import BooleanField, RelationField

from ...starlette_admin.view import InlineView
from ..models.bucket_access_key_links import BucketAccessKeyLink


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
        link: BucketAccessKeyLink = cast(BucketAccessKeyLink, obj)
        pass

    async def before_edit(self, request: Request, data: dict[str, Any], obj: Any) -> None:
        pass

    async def before_delete(self, request: Request, obj: Any) -> None:
        pass
