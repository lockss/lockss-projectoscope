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

from starlette.requests import Request
from starlette_admin import HasMany, HasOne, StringField, UUIDField

from ...starlette_admin.view import View
from ..models.organizations import Organization
from ..models.users import user_


class OrganizationView(View):
    icon = 'fa-solid fa-people-roof'

    fields = [
        UUIDField('id', version=4, label=Organization.model_fields['id'].title),
        StringField('handle', label=Organization.model_fields['handle'].title),
        StringField('name', label=Organization.model_fields['name'].title),
        StringField('short_name', label=Organization.model_fields['short_name'].title),
        HasOne('initiative', key='initiative'),
        HasMany('users', key='user'),
    ]

    exclude_fields_from_create = ['users']
    exclude_fields_from_list = ['id', 'users']

    fields_default_sort = ['name']
    searchable_fields = ['id', 'handle', 'name', 'short_name']

    def __init__(self):
        super().__init__(Organization)

    def is_accessible(self, request: Request) -> bool:
        return (u := user_(request)).active and u.admin
