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

from click_extra import Context, echo, group, pass_context, option_group, show_params_option, timer_option, tree_option
from lockss.pybasic.cliutil import compose_decorators

from . import __copyright__, __license__, __version__


#: The debug option group: --show-params, --time/--no-time
_debug_option_group = option_group(
    'Debug options',
    show_params_option,
    timer_option
)


@group(params=None)
@tree_option
@pass_context
def projcli(ctx: Context, **kwargs) -> None:
    pass


#: The composite top-level command decorator
_top_level_command = compose_decorators(_debug_option_group, pass_context)


@projcli.command(help='Show the copyright and exit.')
@_top_level_command
def copyright(ctx: Context, **kwargs) -> None:
    echo(__copyright__)


@projcli.command(help='Show the software license and exit.')
@_top_level_command
def license(ctx: Context, **kwargs) -> None:
    echo(__license__)


@projcli.command('version', help='Show the version number and exit.')
@_top_level_command
def version(ctx: Context, **kwargs) -> None:
    echo(__version__)


def main() -> None:
    """Main entry point of the module."""
    projcli()
