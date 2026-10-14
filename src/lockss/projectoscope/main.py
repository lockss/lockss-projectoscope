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

from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_ldap import LDAPAuth, LDAPSettings, get_current_user, require_groups
from fastapi_ldap.models import LDAPUser


_ldap_base_dn: str = 'dc=lockss,dc=org'


settings = LDAPSettings(
    ldap_url='ldaps://sul-lockss-thibvm1.stanford.edu:636',
    ldap_base_dn=_ldap_base_dn,
    bind_dn='uid=admin,cn=users,cn=accounts,dc=lockss,dc=org', # FIXME
    tls_ca_cert_file='ca.crt',
    user_search_base=f'cn=users,cn=accounts,{_ldap_base_dn}',
    group_search_base=f'cn=groups,cn=accounts,{_ldap_base_dn}',
)

ldap_auth = LDAPAuth(settings)


app = FastAPI(lifespan=ldap_auth.lifespan)
app.mount('/static/css', StaticFiles(directory='src/lockss/projectoscope/static/css'), name='css')
app.mount('/static/images', StaticFiles(directory='src/lockss/projectoscope/static/images'), name='images')
app.mount('/static/js', StaticFiles(directory='src/lockss/projectoscope/static/js'), name='js')
templates = Jinja2Templates(directory='src/lockss/projectoscope/templates')


@app.get('/', response_class=HTMLResponse)
def root(req: Request) -> Response:
    return templates.TemplateResponse(req, 'index.html')


@app.get('/home', response_class=HTMLResponse)
def home(req: Request) -> Response:
    return templates.TemplateResponse(req, 'base.html')


@app.get('/login', response_class=HTMLResponse)
def login(req: Request) -> Response:
    return templates.TemplateResponse(req, 'login.html')


@app.get('/ldap-test')
async def ldap_test(user: LDAPUser = Depends(get_current_user)):
    return repr(user)
