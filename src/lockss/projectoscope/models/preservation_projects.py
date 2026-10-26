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

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship
from starlette.requests import Request

from . import Handle, StrictSQLModel

if TYPE_CHECKING:
    from .organizations import Organization


class PreservationProjectBase(StrictSQLModel):
    handle: Handle = Field(nullable=False, unique=True, index=True, title='Preservation Project Handle')
    name: str = Field(nullable=False, min_length=1, max_length=60, title='Name')
    short_name: str = Field(unique=True, max_length=20, title='Short Name')

class PreservationProject(PreservationProjectBase, table=True):
    __tablename__ = 'preservation_projects'
    id: UUID | None = Field(default_factory=uuid4, primary_key=True, index=True, title='UUID')

    organizations: list['Organization'] = Relationship(back_populates='preservation_project')

    def __admin_repr__(self, request: Request) -> str:
        return f'{self.name} ({self.handle})'
