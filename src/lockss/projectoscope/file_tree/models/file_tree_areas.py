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
from typing import TYPE_CHECKING, Any, Self
from uuid import UUID, uuid4

from pydantic import field_validator, model_validator, ModelWrapValidatorHandler
from sqlmodel import Field, Relationship, SQLModel
from starlette.requests import Request

from ...pydantic.errors import make_field_error

if TYPE_CHECKING:
    from .file_trees import FileTree


class FileTreeAreaEdit(SQLModel):
    active: bool = Field(title='Active', description='Whether this file tree area is active')


class FileTreeArea(FileTreeAreaEdit, table=True):
    __tablename__ = 'file_tree_areas'

    id: UUID | None = Field(default_factory=uuid4, primary_key=True, index=True, title='UUID')
    path: Path = Field(index=True, unique=True, title='Path', description='Absolute directory path')

    file_trees: list['FileTree'] = Relationship(back_populates='file_tree_area')

    def __admin_repr__(self, request: Request) -> str:
        return f'{self.path!s}'

    @field_validator('path', mode='after')
    @classmethod
    def _validate_path_is_absolute(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError('Path must be absolute')
        return value

    @model_validator(mode='wrap')
    @classmethod
    def _validate_path_if_active(cls, data: Any, handler: ModelWrapValidatorHandler[Self]) -> Self:
        mi: Self = handler(data)
        if mi.active:
            if not mi.path.exists():
                raise make_field_error(cls, mi, ('path', 'value_error', 'Active path must exist', None))
            if not mi.path.is_dir():
                raise make_field_error(cls, mi, ('path', 'value_error', 'Active path must be a directory', None))
        return mi
