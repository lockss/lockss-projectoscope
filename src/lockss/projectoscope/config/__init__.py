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
from lockss.pybasic.nodeutil import PortNumber
from pydantic import Field, HttpUrl, IPvAnyAddress, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class OverseerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env')

    database_url: SecretStr = Field(title='Database URL')
    secret_key: SecretStr = Field(title='Secret Key')
    url: HttpUrl | None = Field(None, title='Overseer URL')


class BaseComponentSettings(BaseSettings, ABC):
    title: str = Field(title='Title',
                       description='The title of this component')


ComponentType: TypeAlias = Literal[
    'hq',
    'garage',
    'profile',
]


class HqSettings(BaseComponentSettings):
    TYPE: ClassVar[Literal['hq']] = 'hq'
    DEFAULT_TITLE: ClassVar[str] = 'Projectoscope HQ'

    type: Literal['hq'] = TYPE
    title: str = DEFAULT_TITLE


class GarageComponentSettings(BaseComponentSettings):
    TYPE: ClassVar[Literal['garage']] = 'garage'
    DEFAULT_TITLE: ClassVar[str] = 'Garage Controller'

    type: Literal['garage'] = TYPE
    title: str = DEFAULT_TITLE
    admin: HttpUrl = Field(title='Garage Admin URL')


class ProfileSettings(BaseComponentSettings):
    TYPE: ClassVar[Literal['profile']] = 'profile'

    type: Literal['profile'] = TYPE
    title: str = 'Projectoscope Profile'


ComponentSettings: TypeAlias = Annotated[
    Union[
        HqSettings,
        GarageComponentSettings,
        ProfileSettings,
    ],
    Field(discriminator='type')
]


class ProjectoscopeSettings(BaseSettings):
    DEFAULT_PORT: ClassVar[PortNumber] = 8000

    host: IPvAnyAddress = Field(title='Host',
                                description='Host this Projectoscope instance binds to')
    port: PortNumber = Field(DEFAULT_PORT,
                             title='Port',
                             description='Port this Projectoscope instance binds to')
    overseer: OverseerSettings = Field(title='Overseer Settings',
                                       description='The overseer settings for this Projectoscope instance')
    components: list[ComponentSettings] = Field(title='Components',
                                                description='The list of components for this Projectoscope instance')

    @model_validator(mode='after')
    def _validate_components(self) -> Self:
        errors: list[str] = []
        if (nc := len(bucketize(self.components, 'type').get(hqtyp := HqSettings.TYPE, []))) > 1:
            errors.append(f'{nc} components are of type "{hqtyp}"')
        if errors:
            raise ValueError(f'{unit_len(errors, "error")}: {"; ".join(errors)}')
        return self

    def is_hq(self) -> bool:
        return any(c.type == HqSettings.TYPE for c in self.components)


def component_sort_key(settings: ComponentSettings) -> int:
    return ComponentType.__args__.index(settings.type) # raises ValueError
