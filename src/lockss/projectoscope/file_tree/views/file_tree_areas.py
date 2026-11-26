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

from pathlib import Path
from typing import Any, cast

from lockss.pybasic.fileutil import path
from sqlalchemy.exc import IntegrityError as SQLAIntegrityError
from starlette.requests import Request
from starlette_admin import BooleanField, HasMany, StringField, UUIDField, flash
from starlette_admin.exceptions import FormValidationError

from ...config import FileTreeManagerSettings
from ...hq.models.users import user_
from ...starlette_admin.view import IntegrityError
from ..models.file_tree_areas import FileTreeArea, FileTreeAreaEdit
from . import FileTreeManagerView


class FileTreeAreaView(FileTreeManagerView):
    _edit_validation_model = FileTreeAreaEdit
    icon = 'fa-solid fa-folder-tree'

    fields = [
        UUIDField('id', version=4, label=FileTreeArea.model_fields['id'].title),
        StringField('path', label=FileTreeArea.model_fields['path'].title),
        BooleanField('active', label=FileTreeArea.model_fields['active'].title),
        HasMany('file_trees', key='file-tree')
    ]

    exclude_fields_from_create = ['file_trees']
    exclude_fields_from_detail = ['file_trees']
    _non_editable_fields = ['path']
    exclude_fields_from_list = ['id', 'file_trees']

    fields_default_sort = ['path']
    searchable_fields = ['id', 'path']

    def __init__(self, file_tree_manager_settings: FileTreeManagerSettings) -> None:
        super().__init__(file_tree_manager_settings, FileTreeArea)

    async def before_create(self, request: Request, data: dict[str, Any], obj: Any) -> None:
        # Both data['path'] and obj.path seem to be str, not Path
        ftap: Path = path(data['path'])
        if not any(ftap.is_relative_to(prefix) for prefix in self.file_tree_manager_settings.file_tree_area_prefixes):
            raise FormValidationError({'path': 'Invalid file tree area path'})

    async def create(self, request: Request, data: dict[str, Any]) -> Any:
        try:
            return await super().create(request, data)
        except IntegrityError as ie:
            match [*ie.fields]:
                case ['path']:
                    raise FormValidationError({'path': 'Path already in use'})
                case _:
                    raise # Unexpected
        except SQLAIntegrityError as sqlaie:
            flash(request, f'An unexpected integrity error has occurred. {sqlaie}', 'error')
            raise FormValidationError({'id': 'An unexpected integrity error has occurred'})

    def is_accessible(self, request: Request) -> bool:
        return (u := user_(request)).active and u.admin
