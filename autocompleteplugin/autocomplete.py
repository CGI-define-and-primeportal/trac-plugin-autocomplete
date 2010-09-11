# coding: utf-8
#
# Copyright (c) 2010, Logica
# 
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright 
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the <ORGANIZATION> nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# ----------------------------------------------------------------------------

from trac.core import Component, implements, TracError
from trac.config import BoolOption, ListOption
from trac.web import IRequestFilter
from trac.wiki import parse_args
from trac.web.chrome import ITemplateProvider, add_stylesheet, add_script, add_script_data
from pkg_resources import resource_filename
from trac.web.api import ITemplateStreamFilter, IRequestHandler
from genshi.builder import tag
from genshi.filters.transform import Transformer
from trac.env import IEnvironmentSetupParticipant
from trac.util.presentation import to_json
from api import IAutoCompleteProvider, IAutoCompleteUser
from trac.core import ExtensionPoint
from trac.perm import PermissionSystem
from trac.web.session import DetachedSession
import itertools

try:
    from simplifiedpermissionsadminplugin import SimplifiedPermissions
except ImportError, e:
    SimplifiedPermissions = None

class AutoCompleteForTickets(Component):
    """Enable auto completing / searchable user lists for ticket
    pages."""
    implements(IAutoCompleteUser)

    autocomplete_on_tickets = BoolOption('autocomplete', 'tickets', True,
                                         """Enable to provide
                                         autocomplete/search for user
                                         related fields on ticket
                                         pages""")

    # IAutoCompleteUser
    def get_templates(self):
        return {"ticket.html": [("#field-owner", 'select', {}),
                                ("#field-reporter", 'select', {}),
                                ("#action_reassign_reassign_owner", 'select', {}),
                                ('#field-cc', 'text', {}),
                                # turn off autocomplete and just use the "boxes"
                                ('#field-keywords', 'text', '{source: $.noop}')],
                "admin_components.html": [("input[name='owner']", 'select', {})]}

class AutoCompleteBasedOnPermissions(Component):
    """Enable auto completing / searchable user lists to search for
    users based on the session data (anyone who ever logged in.)"""
    implements(IAutoCompleteProvider, IRequestHandler)


    autocomplete_on_tickets = BoolOption('autocomplete', 'listed members', True,
                                         """Enable to provide search
                                         for users who are listed in
                                         permissions. Probably you
                                         don't want this if your
                                         project is open to all of a
                                         group.""")    

    ownurl = '/ajax/usersearch/permissions'

    # IAutoCompleteProvider
    def get_endpoint(self):
        return {'url': self.ownurl,
                'name': 'Members of %s' % self.env.project_name,
                'permission': 'TICKET_VIEW'}

    # IRequestHandler methods
    def match_request(self, req):
        return req.path_info.startswith(self.ownurl)

    def process_request(self, req):
        if req.path_info.startswith(self.ownurl):
            req.perm.require('TICKET_VIEW')
            users = self._users_query(req.args['q'], int(req.args.get('limit', 10)))
            body = to_json(list(users)).encode('utf8')
            req.send_response(200)
            req.send_header('Content-Type', "application/json")
            req.send_header('Content-Length', len(body))
            req.end_headers()
            req.write(body)

    def _users_query(self, q, limit=10):
        if SimplifiedPermissions and self.env.is_enabled(SimplifiedPermissions):
            sp = SimplifiedPermissions(self.env)
            for group, data in sp.group_memberships().items():
                for member in data['members']:
                    if q in member.sid:
                        yield {'sid': member.sid,
                               'name': member.get('name',"%s (never logged in)" % member.sid),
                               'email': member.get('email','')}
        else:
            perm = PermissionSystem(self.env)
            users = []
            for sid, permission in perm.get_all_permissions():
                # gotta get rid of groups...
                if sid in ("anonymous","authenticated","admin"):
                    continue
                users.append(sid)
            for sid in sorted(set(users)):
                if q in sid:
                    session = DetachedSession(self.env, sid)
                    yield {'sid': sid,
                           'name': session.get('name',''),
                           'email': session.get('email','Never logged in')}

class AutoCompleteBasedOnSessions(Component):
    """Enable auto completing / searchable user lists to search for
    users based on the session data (anyone who ever logged in.)"""
    implements(IAutoCompleteProvider, IRequestHandler)        

    ownurl = '/ajax/usersearch/sessions'

    # IAutoCompleteProvider
    def get_endpoint(self):
        return {'url': self.ownurl,
                'name': 'People who accessed %s' % self.env.project_name,
                'permission': 'TICKET_VIEW'}

    # IRequestHandler methods
    def match_request(self, req):
        return req.path_info.startswith(self.ownurl)

    def process_request(self, req):
        if req.path_info.startswith(self.ownurl):
            req.perm.require('TICKET_VIEW')
            users = self._session_query(req.args['q'], int(req.args.get('limit', 10)))
            body = to_json(list(users)).encode('utf8')
            req.send_response(200)
            req.send_header('Content-Type', "application/json")
            req.send_header('Content-Length', len(body))
            req.end_headers()
            req.write(body)

    def _session_query(self, q, limit=10):
        for user in itertools.islice(self.env.get_known_users(), 0, limit):
            if q.lower() in ''.join(user).lower():
                yield {'sid': user[0],
                       'name': user[1],
                       'email': user[2]}


class AutoCompleteSystem(Component):
    implements(ITemplateProvider, ITemplateStreamFilter)

    autocompleters    = ExtensionPoint(IAutoCompleteProvider)
    autocompleteusers = ExtensionPoint(IAutoCompleteUser)

    # ITemplateProvider
    def get_htdocs_dirs(self):
        return [('autocomplete', resource_filename(__name__, 'htdocs'))]
          
    def get_templates_dirs(self):
        return []

    # ITemplateStreamFilter
    def filter_stream(self, req, method, filename, stream, data):
        for autocompleteuser in self.autocompleteusers:
            d = autocompleteuser.get_templates()
            if filename in d:
                stream = self._enable_autocomplete_for_page(req, method, filename, stream, data, d[filename])
        return stream
    
    # internal
    def _enable_autocomplete_for_page(self, req, method, filename, stream, data, inputs):
        add_stylesheet(req, 'autocomplete/css/autocomplete.css')
        add_script(req, 'autocomplete/js/jquery.tracautocomplete.js')
        
        username_completers = []
        for autocompleter in self.autocompleters:
            endpoint = autocompleter.get_endpoint()
            if not endpoint:
                continue
            if endpoint['permission'] is None or req.perm.has_permission(endpoint['permission']):
                # Maybe we could support some 'local data' mode instead of just url?
                # after all, we're already putting the project_users list into the page!
                # that would mean folding AutoCompleteBasedOnSessions back into this component.
                username_completers.append({'url': req.href(endpoint['url']),
                                            'name': endpoint['name']})
        add_script_data(req, {'username_completers': username_completers})
                
        # we could put this into some other URL which the browser could cache?
        add_script_data(req, {'project_users': self._all_project_users()})
        js = ''
        for selector, method_, options in inputs:
            js += '$("%s").makeAutocompleteSearch("%s"' % (selector, method_ or 'select')
            if options:
                if not isinstance(options, basestring):
                    js += ', %s' % to_json(options)
                else:
                    js += ', %s' % options
            js += ')\n'
                
        stream = stream | Transformer('//head').append(tag.script("""
        jQuery(document).ready(
        function($) {
        %s
        });
        """ % js,type="text/javascript"))
        return stream
    
    def _all_project_users(self):
        people = {}
        session_users = False
        if SimplifiedPermissions and self.env.is_enabled(SimplifiedPermissions):
            sp = SimplifiedPermissions(self.env)
            for group, data in sp.group_memberships().items():
                group = group.title().replace("_"," ")
                if data['domains']:
                    group = "%s (Plus: %s)" % (group, ", ".join(data['domains']))
                    session_users = True
                people[group] = []
                for member in data['members']:
                    people[group].append({'sid': member.sid,
                                          'name': member.get('name',"%s (never logged in)" % member.sid),
                                          'email': member.get('email','')})
        else:
            session_users = True
        if session_users:
            people['Current Users'] = []
            for username, name, email in self.env.get_known_users():
                people['Current Users'].append({'sid': username,
                                                'name': name,
                                                'email': email})

        return people
        
