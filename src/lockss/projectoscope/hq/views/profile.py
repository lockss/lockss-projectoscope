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
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE# POSSIBILITY OF SUCH DAMAGE.

from typing import Any, Sequence, cast

from sqlalchemy import Select
from sqlmodel import and_
from starlette.requests import Request
from starlette_admin import StringField, ComputedField, PasswordField, BooleanField, BaseField, RequestAction, flash
from starlette_admin.exceptions import FormValidationError
from starlette_admin.filters import FilterRegistry

from ..models.users import User, user_
from ..views import PJSModelView, gray, NON_COMPUTED_FIELD_ACTIONS, COMPUTED_FIELD_ACTIONS


class ProfileView(PJSModelView):
    key = 'profile'
    menu_label = 'Profile'
    icon = 'fa-solid fa-user'

    # Undo PJSModelView
    show_goto_page = False
    row_click_navigate = True

    fields = ['id', gray(StringField('handle')), 'first_name', 'last_name',
              ComputedField('full_name', getter=lambda req, obj: obj.full_name()),
              'email',
              PasswordField('plaintext_password', label='Change password'),
              PasswordField('plaintext_password_2', label='Change password (confirm)'),
              'organization', gray(BooleanField('active')), gray(BooleanField('admin')), gray(BooleanField('superuser'))]
    exclude_fields_from_list = ['id']
    column_visibility = False
    searchable_fields = []
    sortable_fields = []

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(User, *args, **kwargs)

    def can_access_field(self, request: Request, field: BaseField, action: RequestAction | None = None) -> bool:
        action = action or request.state.action
        match field.name:
            case 'first_name' | 'last_name': # Computed field counterparts
                return action.name in NON_COMPUTED_FIELD_ACTIONS
            case 'full_name': # Computed fields
                return action.name in COMPUTED_FIELD_ACTIONS
            case 'hashed_password':
                return action.name == RequestAction.EDIT
            case 'plaintext_password' | 'plaintext_password_2': # Only in EDIT
                return action.name == RequestAction.EDIT
        return super().can_access_field(request, field, action=action)

    def can_create(self, request: Request) -> bool:
        return False

    def can_delete(self, request: Request) -> bool:
        return False

    def can_edit(self, request: Request) -> bool:
        return (pk := request.query_params.get('pk')) is None or pk == str(user_(request).id) # FIXME pk:str/pk:UUID inconsistencies

    def can_export(self, request: Request) -> bool:
        return False

    def can_import(self, request: Request) -> bool:
        return False

    def can_view_detail(self, request: Request) -> bool:
        return (pk := request.query_params.get('pk')) is None or pk == str(user_(request).id) # FIXME pk:str/pk:UUID inconsistencies

    async def find_by_pk(self, request: Request, pk: Any) -> Any:
        return await super().find_by_pk(request, user_(request).id.hex) # FIXME pk:str/pk:UUID inconsistencies

    def get_count_query(self, request: Request) -> Select:
        return super().get_count_query(request).where(and_(User.id == user_(request).id))

    def get_fields_list(self, request: Request, *, include_nested: bool = False, action: RequestAction | None = None) -> Sequence[BaseField]:
        res = [f for f in super().get_fields_list(request, include_nested=include_nested, action=action)]
        if request.method == 'POST' and (action == RequestAction.EDIT or request.state.action == RequestAction.EDIT) and getattr(request.state, 'populate_obj_special_case', False):
            res = [f for f in res if f.name not in ('plaintext_password', 'plaintext_password_2')]
            res.append(PasswordField('hashed_password'))
        return res

    def get_filter_registry(self) -> FilterRegistry:
        return FilterRegistry() # empty registry, disabling the filter selector

    def get_list_query(self, request: Request) -> Select:
        return super().get_list_query(request).where(and_(User.id == user_(request).id))

    def is_accessible(self, request: Request) -> bool:
        return user_(request).active

    async def validate(self, request: Request, data: dict[str, Any]) -> None:
        # This is called from CREATE and EDIT. CREATE is disabled here right now.
        # This is where the password-checking logic must live, not in
        # before_edit as was previously believed, as the latter is called only
        # at the end as part of an event-emitting hook.
        user: User = user_(request)
        plaintext1: str = cast(str, data.get('plaintext_password'))
        plaintext2: str = cast(str, data.get('plaintext_password_2'))
        if plaintext1 and not plaintext2:
            flash(request, 'The form contains errors: plaintext_password, plaintext_password_2', 'error')
            raise FormValidationError({'plaintext_password_2': 'Please confirm password change'})
        if plaintext2 and not plaintext1:
            flash(request, 'The form contains errors: plaintext_password', 'error')
            raise FormValidationError({'plaintext_password': 'Please confirm password change'})
        if plaintext1 and plaintext2:
            if plaintext1 != plaintext2:
                flash(request, 'The form contains errors: plaintext_password_2', 'error')
                raise FormValidationError({'plaintext_password_2': 'Changed passwords do not match'})
            data['hashed_password'] = User.hash_password(plaintext1)
        else:
            data['hashed_password'] = user.hashed_password
        data.pop('plaintext_password', None)
        data.pop('plaintext_password_2', None)
        # Actual validation
        new_data = user_(request).model_copy(update=data).model_dump()
        await super().validate(request, new_data)

    async def _populate_obj(self, request: Request, obj: Any, data: dict[str, Any], is_edit: bool = False) -> Any:
        try:
            request.state.populate_obj_special_case = True
            await super()._populate_obj(request, obj, data, is_edit=is_edit)
        finally:
            request.state.populate_obj_special_case = False
