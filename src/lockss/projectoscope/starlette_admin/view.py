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
from typing import TypeVar

from starlette.requests import Request
from starlette_admin import BaseField, RelationField, RequestAction
from starlette_admin.contrib.sqlmodel import InlineModelView, ModelView


ModelViewT = TypeVar('ModelViewT', bound=ModelView)


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


def gray(field: BaseField) -> BaseField:
    field.read_only = True
    field.disabled = True
    return field


def _make_view(name: str, parent: type[ModelView|InlineModelView]):
    #class _View(ModelView):
    class _View(parent):
        # Customize ModelView fields
        row_click_navigate = False
        show_goto_page = True

        # New fields
        _can_create: bool = True
        _can_delete: bool = True
        _can_edit: bool = True
        _can_export: bool = True
        _can_import: bool = True
        _can_view_detail: bool = True
        _non_editable_fields: Sequence[str | BaseField] = []

        def can_create(self, request: Request) -> bool:
            return self._can_create

        def can_delete(self, request: Request) -> bool:
            return self._can_delete

        def can_edit(self, request: Request) -> bool:
            return self._can_edit

        def can_export(self, request: Request) -> bool:
            return self._can_export

        def can_import(self, request: Request) -> bool:
            return self._can_import

        def can_view_detail(self, request: Request) -> bool:
            return self._can_view_detail

        def get_fields_list(self, request: Request, *, include_nested: bool = False, action: RequestAction | None = None) -> Sequence[BaseField]:
            ret: list[BaseField] = [*super().get_fields_list(request, include_nested=include_nested, action=action)]
            match action:
                case RequestAction.EDIT | RequestAction.INLINE_EDIT | None:  # FIXME unknown if None has bad side effects here
                    ret = [replace(field, read_only=True, disabled=True) if field.name in self._non_editable_fields else field for field in ret]
                    for field in ret:
                        if isinstance(field, RelationField) and field._view is None:
                            field._view = self
            return ret

        async def handle_exception(self, request: Request, exc: Exception) -> None:
            print(exc)
            await super().handle_exception(request, exc)

    _View.__name__ = name
    _View.__qualname__ = f'{__name__}.{name}'
    return _View


View = _make_view('View', ModelView)


InlineView = _make_view('InlineView', InlineModelView)
