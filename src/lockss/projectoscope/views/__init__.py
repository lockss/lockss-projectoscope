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

from typing import Any

from pydantic import ValidationError
from starlette.requests import Request
from starlette_admin import RequestAction, flash
from starlette_admin.contrib.sqlmodel import ModelView
from starlette_admin.exceptions import FormValidationError


NON_COMPUTED_FIELD_ACTIONS: frozenset[RequestAction] = frozenset({
    RequestAction.CREATE,
    RequestAction.EDIT,
    RequestAction.EXPORT,
    RequestAction.IMPORT,
    RequestAction.LIST,
})


COMPUTED_FIELD_ACTIONS: frozenset[str] = frozenset({
    RequestAction.DETAIL,
})


class SQLModelModelView(ModelView):
    show_goto_page = True
    row_click_navigate = False

    async def validate(self, request: Request, data: dict[str, Any]) -> None:
        try:
            self.validate_call(request, data)
        except ValidationError as ve:
            flash(request, f'The form contains errors: {", ".join(error["loc"][0] for error in ve.errors())}', 'error')
            raise FormValidationError({error['loc'][0]: error['msg'] for error in ve.errors()})

    def validate_call(self, request: Request, data: dict[str, Any]) -> None:
        self.validate_original(request, data)

    def validate_original(self, request: Request, data: dict[str, Any]) -> None:
        super().validate(request, data)
