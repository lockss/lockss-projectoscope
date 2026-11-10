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
Projectoscope component for superusers of a Projectoscope cluster.
"""

from typing import TYPE_CHECKING

from starlette_admin import DropDown

from ..component import Component
from ..config import HqSettings, OverseerSettings
from .admin import HqAdmin
from .views.initiatives import InitiativeView
from .views.organizations import OrganizationView
from .views.users import UserView

if TYPE_CHECKING:
    from ..main import Projectoscope


class HqComponent(Component[HqSettings]):

    def __init__(self,
                 overseer_settings: OverseerSettings,
                 hq_settings: HqSettings):
        super().__init__(overseer_settings, hq_settings)

    def set_up_admin(self, app: Projectoscope) -> None:
        app.admin.add_view(DropDown(self.component_settings.title,
                                    [
                                        InitiativeView(),
                                        OrganizationView(),
                                        UserView()
                                    ],
                                    icon='fa-solid fa-screwdriver-wrench'))

    def set_up_api(self, app: Projectoscope) -> None:
        pass # No API
