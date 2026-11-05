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

from typing import Literal, Self, TypeAlias, Union

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class OverseerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env')

    is_hq: bool = Field(False, title='Is HQ')
    database_url: str = Field(title='Database URL')
    secret_key: str = Field(title='Secret Key')


class ControllerSettings(BaseSettings):
    title: str = Field(title='Title')
    route_name: str = Field(title='Route Name')
    base_url: str | None = Field(title='Base URL')

    @model_validator(mode='after')
    def _default_base_url(self) -> Self:
        self.base_url = self.base_url or f'/{self.route_name}'
        return self


class HqSettings(ControllerSettings):
    title: str = 'Projectoscope HQ'
    route_name: Literal['hq'] = 'hq'
    base_url: Literal['/hq'] = '/hq'


class GarageControllerSettings(ControllerSettings):
    title: str = 'Projectoscope Garage Controller'
    route_name: str = 'garage-controller'


ControllerSettingsType: TypeAlias = Union[
    HqSettings,
    GarageControllerSettings,
]


class ProjectoscopeSettings(BaseSettings):
    overseer: OverseerSettings = Field(title='Overseer Settings')
    controllers: list[ControllerSettings] = Field(title='Controllers')
