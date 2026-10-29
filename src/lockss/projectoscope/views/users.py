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

from collections.abc import Sequence
from typing import Any

from boltons.iterutils import partition
from boltons.strutils import unit_len
from sqlalchemy import Select
from starlette.status import HTTP_403_FORBIDDEN
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette_admin import ActionSelection, BaseField, ComputedField, CustomView, PasswordField, RequestAction, action, flash, route
from starlette_admin.filters import FilterGroup, FilterRegistry

from . import SQLModelModelView, COMPUTED_FIELD_ACTIONS, NON_COMPUTED_FIELD_ACTIONS
from ..models.users import User, UserBase


class UserView(SQLModelModelView):
    icon = 'fa fa-circle-user'
    fields = ['id', 'handle', 'first_name', 'last_name',
              ComputedField('full_name', getter=lambda req, obj: obj.full_name()),
              'email',
              'organization', 'active', 'admin', 'superuser']
    exclude_fields_from_list = ['id']
    fields_default_sort = ['last_name', 'first_name', 'handle']
    searchable_fields = ['handle', 'first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(User, *args, **kwargs)

    def can_create(self, request: Request) -> bool:
        return False

    def can_delete(self, request: Request) -> bool:
        return False

    def can_import(self, request: Request) -> bool:
        return False

    def can_access_field(self, request: Request, field: BaseField, action: RequestAction | None = None) -> bool:
        action = action or request.state.action
        match field.name:
            case 'first_name' | 'last_name': # Computed field counterparts
                return action.name in NON_COMPUTED_FIELD_ACTIONS
            case 'full_name': # Computed fields
                return action.name in COMPUTED_FIELD_ACTIONS
        return super().can_access_field(request, field, action=action)

    @action(name='deactivate',
            text='Deactivate',
            confirmation='Are you sure you want to deactivate the selected users?',
            submit_btn_text='Confirm',
            submit_btn_class='btn btn-success')
    async def deactivate_action(self, request: Request, selection: ActionSelection) -> None:
        selected: Sequence[User] = await selection.rows()
        n_selected: int = len(selected)
        active, inactive = partition(selected, lambda u: u.active)
        active_superuser, active_nonsuperuser = partition(active, lambda u: u.superuser)
        if len(active_nonsuperuser) == 0:
            flash(request, 'No selected users are eligible to be deactivated.', 'error')
            return
        for user in active_nonsuperuser:
            user.active = False
        flash(request, f'{unit_len(active_nonsuperuser, "selected user")} out of {n_selected} were deactivated.', 'success')
        if inactive:
            flash(request, f'{unit_len(inactive, "selected user")} out of {n_selected} were already deactivated.', 'warning')
        if active_superuser:
            flash(request, f'{unit_len(active_superuser, "selected user")} out of {n_selected} were superusers and are not eligible to be deactivated.', 'warning')
        return

    @action(name='reactivate',
            text='Reactivate',
            confirmation='Are you sure you want to reactivate the selected users?',
            submit_btn_text='Confirm',
            submit_btn_class='btn btn-success')
    async def reactivate_action(self, request: Request, selection: ActionSelection) -> None:
        selected: Sequence[User] = await selection.rows()
        n_selected: int = len(selected)
        active, inactive = partition(selected, lambda u: u.active)
        inactive_superuser, inactive_nonsuperuser = partition(inactive, lambda u: u.superuser)
        if len(inactive_nonsuperuser) == 0:
            flash(request, 'No selected users are eligible to be reactivated.', 'error')
            return
        for user in inactive_nonsuperuser:
            user.active = True
        flash(request, f'{unit_len(inactive_nonsuperuser, "selected user")} out of {n_selected} were reactivated.', 'success')
        if active:
            flash(request, f'{unit_len(active, "selected user")} out of {n_selected} were already active.', 'warning')
        if inactive_superuser:
            flash(request, f'{unit_len(inactive_superuser, "selected user")} out of {n_selected} were superusers and are not eligible to be reactivated.', 'warning')
        return

    def is_accessible(self, request: Request) -> bool:
        return (u := request.state.admin_user.user).active and u.admin

    def validate_call(self, request: Request, data: dict[str, Any]) -> None:
         UserBase.model_validate(data)


class ProfileView(SQLModelModelView):
    key = 'profile'
    menu_label = 'Profile'
    icon = 'fa fa-address-card'

    fields = ['id', 'handle', 'first_name', 'last_name',
              ComputedField('full_name', getter=lambda req, obj: obj.full_name()),
              'email',
              'organization', 'active', 'admin', 'superuser']
    exclude_fields_from_list = ['id']
    column_visibility = False
    searchable_fields = []
    sortable_fields = []
    show_goto_page = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(User, *args, **kwargs)

    def can_access_field(self, request: Request, field: BaseField, action: RequestAction | None = None) -> bool:
        action = action or request.state.action
        match field.name:
            case 'first_name' | 'last_name': # Computed field counterparts
                return action.name in NON_COMPUTED_FIELD_ACTIONS
            case 'full_name': # Computed fields
                return action.name in COMPUTED_FIELD_ACTIONS
        return super().can_access_field(request, field, action=action)

    def can_create(self, request: Request) -> bool:
        return False

    def can_delete(self, request: Request) -> bool:
        return False

    def can_export(self, request: Request) -> bool:
        return False

    def can_import(self, request: Request) -> bool:
        return False

    def get_filter_registry(self) -> FilterRegistry:
        return FilterRegistry() # empty registry, disabling the filter selector

    def is_accessible(self, request: Request) -> bool:
        return request.state.admin_user.user.active

    def get_count_query(self, request: Request) -> Select:
        return super().get_count_query(request).where(User.id == request.state.admin_user.user.id)

    def get_list_query(self, request: Request) -> Select:
        return super().get_list_query(request).where(User.id == request.state.admin_user.user.id)

    async def find_by_pk(self, request: Request, pk: Any) -> Any:
        # FIXME This doesn't feel right but it doesn't work without .hex
        return await super().find_by_pk(request, request.state.admin_user.user.id.hex)
