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
A type that combines Pydantic's SecretStr with StringConstraints that can be
picked up by Alembic (which benefits from Alembic)
"""

from typing import Annotated

from pydantic import SecretStr, StringConstraints
from sqlalchemy.types import String, TypeDecorator
from sqlmodel import Field


class SecretStrType(TypeDecorator):
    impl = String
    cache_ok = True

    def __init__(self, length: int | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.length = length
        self.impl = String(length=length)

    def process_bind_param(self, value: SecretStr | str | None, dialect):
        if isinstance(value, SecretStr):
            return value.get_secret_value()
        return value

    def process_result_value(self, value: str | None, dialect):
        if value is not None:
            return SecretStr(value)
        return None


def SecretStringConstraints(*,
                            min_length: int | None = None,
                            max_length: int | None = None,
                            pattern: str | None = None):
    return Annotated[StringConstraints(min_length=min_length,
                                       max_length=max_length,
                                       pattern=pattern),
                     Field(sa_type=SecretStrType(length=max_length))]
