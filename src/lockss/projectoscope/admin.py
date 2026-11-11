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

"""
A Starlette-Admin Admin subclass for Projectoscope with some pluggable behaviors
to suit individual components.
"""

from importlib import resources
from typing import Any, Awaitable, Callable, TypeAlias, TYPE_CHECKING

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.status import HTTP_403_FORBIDDEN
from starlette_admin import BaseModelView
from starlette_admin.contrib.sqlmodel import Admin

from .hq.models.users import user_
from lockss.projectoscope.profile.views.profile import ProfileView

if TYPE_CHECKING:
    from .main import Projectoscope


FindObjectOr404Behavior: TypeAlias = Callable[['ProjectoscopeAdmin', Request, BaseModelView, str | None, str | None, str], Awaitable[Any]]


class ProjectoscopeAdmin(Admin):
    _find_object_or_404_behaviors: list[FindObjectOr404Behavior] = []

    def __init__(self, app: Projectoscope):
        super().__init__(app.engine,
                         auth_provider=app.auth_provider,
                         secret_key=app.settings.overseer.secret_key.get_secret_value(),
                         title='Projectoscope',
                         base_url='/web',
                         route_name='web',
                         templates_dir=str(resources.files(__package__).joinpath('templates')),
                         static_dir=str(resources.files(__package__).joinpath('static')))

    def add_find_object_or_404_behavior(self, find_object_or_404_behavior: FindObjectOr404Behavior) -> None:
        self._find_object_or_404_behaviors.append(find_object_or_404_behavior)

    async def _find_object_or_404(self, request: Request, view: BaseModelView, key: str | None, pk: str | None, action: str) -> Any:
        for find_object_or_404_behavior in self._find_object_or_404_behaviors:
            await find_object_or_404_behavior(self, request, view, key, pk, action)
        if isinstance(view, ProfileView) and key == 'profile' and (action == 'detail' or action == 'edit'):
            upk = str(user_(request).id)  # FIXME pk:str/pk:UUID inconsistencies
            if pk and pk != upk:
                raise HTTPException(HTTP_403_FORBIDDEN)
            pk = upk
        return await super()._find_object_or_404(request, view, key, pk, action)
