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
from typing import Any

from boltons.iterutils import partition
from boltons.strutils import unit_len
from starlette.requests import Request
from starlette_admin import ActionSelection, action, flash
from starlette_admin.exceptions import ActionFailed

from . import SQLModelModelView
from ..models.users import User, UserBase


class UserView(SQLModelModelView):
    fields = ['id', 'username', 'display_name', 'email', 'active', 'admin', 'superuser']
    exclude_fields_from_list = ['id']
    fields_default_sort = ['username']
    searchable_fields = ['id', 'username', 'display_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(User, *args, **kwargs)

    def is_accessible(self, request: Request) -> bool:
        return request.state.admin_user.user.admin

    def can_create(self, request: Request) -> bool:
        return False

    def can_delete(self, request: Request) -> bool:
        return False

    def can_import(self, request: Request) -> bool:
        return False

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

    def validate_call(self, request: Request, data: dict[str, Any]) -> None:
         UserBase.model_validate(data)
