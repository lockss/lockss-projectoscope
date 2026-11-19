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
from datetime import UTC
from typing import Any, ClassVar, cast

from garage_admin_sdk import AccessKeyApi, GetKeyInfoResponse, UpdateKeyRequestBody
from sqlalchemy import Select
from sqlmodel import and_
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.status import HTTP_400_BAD_REQUEST
from starlette_admin import BaseField, BooleanField, ComputedField, DateTimeField, HasOne, RelationField, RequestAction, StringField, UUIDField, flash

from ...config import GarageComponentSettings
from ...hq.models.users import User, user_
from ..models.access_keys import AccessKey
from . import GarageComponentView


class AccessKeyView(GarageComponentView):
    DATETIME_FORMAT: ClassVar[str] = '%Y-%m-%d %H:%M:%S'

    icon = 'fa-solid fa-key'
    _can_import = False

    fields = [
        UUIDField('id',
                  version=4,
                  label=AccessKey.model_fields['id'].title),
        StringField('access_key_identifier',
                    copy_to_clipboard=True,
                    label=AccessKey.model_fields['access_key_identifier'].title),
        StringField('name',
                    label=AccessKey.model_fields['name'].title),
        HasOne('user',
               key='user',
               label=(usr := AccessKey.model_fields['user_id']).title,
               help_text=usr.description),
        DateTimeField('created',
                      output_format=DATETIME_FORMAT,
                      label=(crd := AccessKey.model_fields['created']).title,
                      help_text=crd.description),
        DateTimeField('expiration',
                      default=((exn := AccessKey.model_fields['expiration']).default_factory or (lambda: ''))(),
                      output_format=DATETIME_FORMAT,
                      label=exn.title,
                      help_text=exn.description),
        BooleanField('expired',
                     label=AccessKey.model_fields['expired'].title,
                     list_template = 'fields/list/text.html',
                     detail_template = 'fields/detail/text.html'),
    ]

    exclude_fields_from_create = ['access_key_identifier', 'name', 'created', 'expired']

    exclude_fields_from_detail = []

    exclude_fields_from_edit = ['user'] # Couldn't make the select2 box disabled

    _non_editable_fields = ['access_key_identifier', 'name', 'created', 'expired']

    exclude_fields_from_export = []

    exclude_fields_from_list = ['id', 'created']

    def __init__(self, garage_settings: GarageComponentSettings, *args, **kwargs) -> None:
        super().__init__(garage_settings, AccessKey, *args, **kwargs)

    def is_accessible(self, request: Request) -> bool:
        return user_(request).active

    def get_list_query(self, request: Request) -> Select:
        select: Select = super().get_list_query(request)
        if not (user := user_(request)).admin:
            select = select.where(and_(AccessKey.user_id == user.id))
        return select

    def get_count_query(self, request: Request) -> Select:
        select: Select = super().get_count_query(request)
        if not (user := user_(request)).admin:
            select = select.where(and_(AccessKey.user_id == user.id))
        return select

    def can_access_field(self, request: Request, field: BaseField, action: RequestAction | None = None) -> bool:
        return super().can_access_field(request, field, action=action)

    def get_fields_list(self, request: Request, *, include_nested: bool = False, action: RequestAction | None = None) -> Sequence[BaseField]:
        ret: list[BaseField] = [*super().get_fields_list(request, include_nested=include_nested, action=action)]
        match action:
            case RequestAction.EDIT | RequestAction.INLINE_EDIT | None: # FIXME unknown if None has bad side effects here
                ret = [replace(field, read_only=True, disabled=True) if field.name in self._non_editable_fields else field for field in ret]
                for field in ret:
                    if isinstance(field, RelationField) and field._view is None:
                        field._view = self
        return ret

    async def before_create(self, request: Request, data: dict[str, Any], obj: Any) -> None:
        access_key: AccessKey = cast(AccessKey, obj)
        user : User = user_(request)
        access_key.name = AccessKey.generate_name(user)
        if access_key.expiration:
            access_key.expiration = access_key.expiration.astimezone(UTC) # FIXME timezones
        with self.api_client_context as api_client:
            # FIXME requires try/except
            api_instance: AccessKeyApi = AccessKeyApi(api_client)
            body: UpdateKeyRequestBody = UpdateKeyRequestBody(name=access_key.name,
                                                              expiration=access_key.expiration,
                                                              neverExpires=access_key.expiration is None)
            resp: GetKeyInfoResponse = api_instance.create_key(body)
        access_key.access_key_identifier = resp.access_key_id
        access_key.created = resp.created
        access_key.expired = resp.expired
        access_key.user_id = user.id
        request.state[f'{access_key.access_key_identifier}_sak'] = resp.secret_access_key

    async def after_create(self, request: Request, obj: Any) -> None:
        access_key: AccessKey = cast(AccessKey, obj)
        # Adding flash messages in the more correct after_create_committed did not have the intended effect
        flash(request, f'The access key {access_key.__admin_repr__(request)} was created and its secret access key is: {request.state[f"{access_key.access_key_identifier}_sak"]}', 'info')
        flash(request, "Warning. The secret access key will not be displayed again.", 'warning')

    async def before_delete(self, request: Request, obj: Any) -> None:
        access_key: AccessKey = cast(AccessKey, obj)
        if access_key.expiration:
            access_key.expiration = access_key.expiration.astimezone(UTC) # FIXME timezones
        with self.api_client_context as api_client:
            # FIXME requires try/except
            api_instance: AccessKeyApi = AccessKeyApi(api_client)
            api_instance.delete_key(cast(str, access_key.access_key_identifier))

    async def before_edit(self, request: Request, data: dict[str, Any], obj: Any) -> None:
        for k in data:
            if k in self._non_editable_fields:
                orig, val = getattr(obj, k, None), data.pop(k, None)
                if orig != val:
                    raise HTTPException(HTTP_400_BAD_REQUEST) # but does this actually occur?
        data.pop('expiration', None)
        access_key: AccessKey = cast(AccessKey, obj)
        if access_key.expiration:
            access_key.expiration = access_key.expiration.astimezone(UTC) # FIXME timezones
        with self.api_client_context as api_client:
            # FIXME requires try/except
            api_instance: AccessKeyApi = AccessKeyApi(api_client)
            body: UpdateKeyRequestBody = UpdateKeyRequestBody(expiration=access_key.expiration,
                                                              neverExpires=access_key.expiration is None)
            resp: GetKeyInfoResponse = api_instance.update_key(cast(str, access_key.access_key_identifier), body)
        access_key.expiration = resp.expiration
        access_key.expired = resp.expired
