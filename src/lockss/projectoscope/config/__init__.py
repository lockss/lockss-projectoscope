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

from abc import ABC
from typing import Annotated, ClassVar, Literal, Self, TypeAlias, Union

from boltons.iterutils import bucketize
from boltons.strutils import unit_len
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class OverseerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env')

    database_url: SecretStr = Field(title='Database URL')
    secret_key: SecretStr = Field(title='Secret Key')


class BaseControllerSettings(BaseSettings, ABC):
    title: str = Field(title='Title',
                       description='The title of this controller')
    route_name: str = Field(title='Route Name',
                            description='The route name of this controller')
    base_url: str | None = Field(title='Base URL',
                                 description='The base URL of this controller, derived from the route name by default')

    @model_validator(mode='after')
    def _default_base_url(self) -> Self:
        self.base_url = self.base_url or f'/{self.route_name}'
        return self


ControllerType: TypeAlias = Literal[
    'hq',
    'garage',
]


class HqSettings(BaseControllerSettings):
    TYPE: ClassVar[str] = 'hq'

    type: Literal['hq'] = 'hq'
    title: str = 'Projectoscope HQ'
    route_name: Literal['hq'] = 'hq'
    base_url: Literal['/hq'] = '/hq'


class GarageControllerSettings(BaseControllerSettings):
    TYPE: ClassVar[str] = 'garage'

    type: Literal['garage'] = 'garage'
    title: str = 'Projectoscope Garage Controller'
    route_name: str = 'garage-controller'


ControllerSettings: TypeAlias = Annotated[
    Union[
        HqSettings,
        GarageControllerSettings,
    ],
    Field(discriminator='type')
]


class ProjectoscopeSettings(BaseSettings):
    overseer: OverseerSettings = Field(title='Overseer Settings',
                                       description='The overseer settings for this Projectoscope instance')
    controllers: list[ControllerSettings] = Field(title='Controllers',
                                                  description='The list of controllers for this Projectoscope instance')

    @model_validator(mode='after')
    def _validate_controllers(self) -> Self:
        errors: list[str] = []
        if (nc := len(bucketize(self.controllers, 'type').get(hqtyp := HqSettings.TYPE, []))) > 1:
            errors.append(f'{nc} controllers are of type "{hqtyp}"')
        for route_name, controllers in bucketize(self.controllers, 'route_name').items():
            if (nc := len(controllers)) > 1:
                errors.append(f'{nc} controllers share the route name "{route_name}"')
        for base_url, controllers in bucketize(self.controllers, 'base_url').items():
            if (nc := len(controllers)) > 1:
                errors.append(f'{nc} controllers share the base URL "{base_url}"')
        if errors:
            raise ValueError(f'{unit_len(errors, "error")}: {"; ".join(errors)}')
        return self

    def is_hq(self) -> bool:
        return any(c.type == HqSettings.TYPE for c in self.controllers)


def controller_sort_key(settings: ControllerSettings) -> int:
    return ControllerType.__args__.index(settings.type) # raises ValueError
