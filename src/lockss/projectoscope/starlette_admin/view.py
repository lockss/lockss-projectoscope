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
from typing import Generic, Self, TypeAlias, TypeVar, cast

from sqlmodel import SQLModel
from starlette.requests import Request
from starlette_admin import BaseField, BaseModelView, RelationField, RequestAction
from starlette_admin.contrib.sqla import InlineModelView as SQLAInlineModelView, ModelView as SQLAModelView
from starlette_admin.contrib.sqla.converters import BaseSQLAModelConverter
from starlette_admin.contrib.sqlmodel import InlineModelView, ModelView


#ModelViewT = TypeVar('ModelViewT', bound=BaseModelView) # the nearest common ancestor of ModelView and InlineModelView

ModelViewT = TypeVar('ModelViewT', bound=ModelView | InlineModelView)


ModelViewParentT = TypeVar('ModelViewParentT', bound=SQLAModelView | SQLAInlineModelView)


class ViewHelper(Generic[ModelViewT, ModelViewParentT]):
    owner: ModelViewT
    super_owner: ModelViewParentT

    def __init__(self, owner: ModelViewT, super_owner: ModelViewParentT):
        self.owner = owner
        self.super_owner = super_owner

    def can_create(self, request: Request) -> bool:
        return getattr(self.owner, '_can_create', True)

    def can_delete(self, request: Request) -> bool:
        return getattr(self.owner, '_can_delete', False)

    def can_edit(self, request: Request) -> bool:
        return getattr(self.owner, '_can_edit', True)

    def can_export(self, request: Request) -> bool:
        return getattr(self.owner, '_can_export', True)

    def can_import(self, request: Request) -> bool:
        return getattr(self.owner, '_can_import', False)

    def can_view_detail(self, request: Request) -> bool:
        return getattr(self.owner, '_can_view_detail', True)

    def get_fields_list(self, request: Request, *, include_nested: bool = False, action: RequestAction | None = None) -> Sequence[BaseField]:
        ret: list[BaseField] = [*self.super_owner.get_fields_list(request, include_nested=include_nested, action=action)]
        match action:
            case RequestAction.EDIT | RequestAction.INLINE_EDIT | None:  # FIXME unknown if None has bad side effects here
                ret = [replace(field, read_only=True, disabled=True) if field.name in getattr(self.owner, '_non_editable_fields', []) else field for field in ret]
                for field in ret:
                    if isinstance(field, RelationField) and field._view is None:
                        field._view = self.owner
        return ret

    async def handle_exception(self, request: Request, exc: Exception) -> None:
        print(exc)
        await self.super_owner.handle_exception(request, exc)


class View(ModelView):
    helper: ViewHelper[ModelView,SQLAModelView]

    def __init__(self,
                 model: type[SQLModel],
                 icon: str | None = None,
                 display_name: str | None = None,
                 menu_label: str | None = None,
                 key: str | None = None,
                 converter: BaseSQLAModelConverter | None = None) -> None:
        super().__init__(model, icon=icon, display_name=display_name, menu_label=menu_label, key=key, converter=converter)
        self.helper = ViewHelper[ModelView,SQLAModelView](self, super())

    def can_create(self, request: Request) -> bool:
        return self.helper.can_create(request)

    def can_delete(self, request: Request) -> bool:
        return self.helper.can_delete(request)

    def can_edit(self, request: Request) -> bool:
        return self.helper.can_edit(request)

    def can_export(self, request: Request) -> bool:
        return self.helper.can_export(request)

    def can_import(self, request: Request) -> bool:
        return self.helper.can_import(request)

    def can_view_detail(self, request: Request) -> bool:
        return self.helper.can_view_detail(request)

    def get_fields_list(self, request: Request, *, include_nested: bool = False, action: RequestAction | None = None) -> Sequence[BaseField]:
        return self.helper.get_fields_list(request, include_nested=include_nested, action=action)

    async def handle_exception(self, request: Request, exc: Exception) -> None:
        await self.helper.handle_exception(request, exc)


class InlineView(InlineModelView):
    helper: ViewHelper[InlineModelView,SQLAInlineModelView]

    def __init__(self, parent_view: BaseModelView | None = None) -> None:
        super().__init__(parent_view=parent_view)
        self.helper = ViewHelper[InlineModelView,SQLAInlineModelView](self, super())

    def can_create(self, request: Request) -> bool:
        return self.helper.can_create(request)

    def can_delete(self, request: Request) -> bool:
        return self.helper.can_delete(request)

    def can_edit(self, request: Request) -> bool:
        return self.helper.can_edit(request)

    def can_export(self, request: Request) -> bool:
        return self.helper.can_export(request)

    def can_import(self, request: Request) -> bool:
        return self.helper.can_import(request)

    def can_view_detail(self, request: Request) -> bool:
        return self.helper.can_view_detail(request)

    def get_fields_list(self, request: Request, *, include_nested: bool = False, action: RequestAction | None = None) -> Sequence[BaseField]:
        return self.helper.get_fields_list(request, include_nested=include_nested, action=action)

    async def handle_exception(self, request: Request, exc: Exception) -> None:
        await self.helper.handle_exception(request, exc)


def gray(field: BaseField) -> BaseField:
    field.read_only = True
    field.disabled = True
    return field


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
