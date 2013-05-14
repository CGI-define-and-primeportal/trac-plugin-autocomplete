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
from trac.ticket.api import ITicketChangeListener
from pkg_resources import resource_filename
from trac.web.api import ITemplateStreamFilter, IRequestHandler
from genshi.builder import tag
from genshi.filters.transform import Transformer
from genshi.core import Markup
from trac.env import IEnvironmentSetupParticipant
from trac.util.presentation import to_json
from api import IAutoCompleteProvider, IAutoCompleteUser, ISelect2AutoCompleteUser, IADLDSAutoCompleteProvider
from trac.core import ExtensionPoint
from trac.perm import PermissionSystem
from trac.web.session import DetachedSession
from trac.cache import cached
import itertools
import re
from trac.admin.api import IAdminPanelProvider
from trac.util.translation import _

from simplifiedpermissionsadminplugin.api import IGroupMembershipChangeListener   
from autocompleteplugin.model import AutoCompleteGroup

class AutoCompleteForMailinglist(Component):
    """Enable auto completing / searchable user lists for mailinglists pages."""
    implements(IAutoCompleteUser)

    autocomplete_on_mailinglist = BoolOption('autocomplete', 'mailinglists', True,
                                             """Enable to provide
                                             autocomplete/search for user
                                             related fields on mailinglist
                                             pages""")

    # IAutoCompleteUser
    def get_templates(self):
        if not self.autocomplete_on_mailinglist:
            return {}
        return {"mailinglist_admin.html": [("input[name=username]", 'select')]}

class AutoCompleteForAuthz(Component):
    """Enable auto completing / searchable user lists for authz admin pages"""
    implements(IAutoCompleteUser)

    autocomplete_on_authz = BoolOption('autocomplete', 'authz', True,
                                       """Enable to provide
                                       autocomplete/search for user
                                       related fields on authz admin
                                       pages""")

    # IAutoCompleteUser
    def get_templates(self):
        if not self.autocomplete_on_authz:
            return {}
        return {"admin_authz.html": [("#addpathmember select[name='subject']", 'select')]}

class AutoCompleteForTimeline(Component):
    """Enable auto completing / searchable user lists for authors on timeline page"""
    implements(IAutoCompleteUser)

    autocomplete_on_authz = BoolOption('autocomplete', 'authors', True,
                                       """Enable to provide
                                       autocomplete/searchable user lists for authors on timeline page""")

    # IAutoCompleteUser
    def get_templates(self):
        if not self.autocomplete_on_authz:
            return {}
        return {"timeline.html": [("input[name='authors']", 'text')]}

class AutoCompleteForTickets(Component):
    """Enable auto completing / searchable user lists for ticket
    pages."""
    implements(IAutoCompleteUser, ITicketChangeListener)

    autocomplete_on_tickets = BoolOption('autocomplete', 'tickets', True,
                                         """Enable to provide
                                         autocomplete/search for user
                                         related fields on ticket
                                         pages""")

    # IAutoCompleteUser
    def get_templates(self):
        if not self.autocomplete_on_tickets:
            return {}
        action_ctls = [("#field-owner", 'select'),
                       ("#field-reporter", 'select'),
                       # Created by vanilla Trac using default workflow
                       ("#action_reassign_reassign_owner", 'select'),
                       ("#action_btn_fixed_select", 'select'),
                       ]
        return {"ticket.html": action_ctls +
                               [("#field-qualityassurancecontact", 'select'),
                                ('#field-cc[type=text]', 'text'),
                                ('#field-keywords', 'text', '{source: %s}' % to_json(
                        self._current_keywords).encode('utf8'))],
                # These are for fields that are pre-loaded using a stored query for instance
                "query.html": action_ctls +
                              [('#filters input[name$=_owner]', 'select'),
                               ('#filters input[name$=_reporter]', 'select'),
                               ('#filters input[name$=_qualityassurancecontact]', 'select')],
                "admin_components.html": [("input[name='owner']", 'select')],
                "hours_timeline.html": action_ctls +
                              [('#filters input[name$=_owner]', 'select'),
                               ('#filters input[name$=_reporter]', 'select'),
                               ('#filters input[name$=_qualityassurancecontact]', 'select')],}

    # ITicketChangeListener
    def ticket_created(self, ticket):
        if ticket['keywords']:
            del self._current_keywords

    def ticket_changed(self, ticket, comment, author, old_values):
        if "keywords" in old_values:
            del self._current_keywords

    def ticket_deleted(self, ticket):
        if ticket['keywords']:
            del self._current_keywords

    @cached
    def _current_keywords(self, db):
        # TODO: should we filter this based on permissions of the ticket
        # each keyword was found in?!
        self.log.debug("Running query for current keywords")
        cursor = db.cursor()
        all_keywords = set()
        cursor.execute("SELECT keywords FROM ticket WHERE status != 'closed'")
        for keywords, in cursor:
            if keywords:
                # this expression comes from _query_link_words() in trac.ticket.web_ui
                for keyword in re.split(r'(\s*(?:\s|[,;])\s*)', keywords):
                    all_keywords.add(keyword)
        return list(all_keywords)

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
        from simplifiedpermissionsadminplugin.simplifiedpermissions import SimplifiedPermissions
        if SimplifiedPermissions and self.env.is_enabled(SimplifiedPermissions):
            sp = SimplifiedPermissions(self.env)
            # Keep track of users that have already been found to prevent
            # yielding duplicates of users belonging to several groups
            yielded_sids = set()
            for group, data in sp.group_memberships().items():
                for member in data['members']:
                    if q in member.sid and member.sid not in yielded_sids:
                        # if the 'never logged in' text changes, then update
                        # plugins/open/autocompleteplugin/autocompleteplugin/htdocs/js/jquery.tracautocomplete.js
                        yield {'sid': member.sid,
                               'name': member.get('name', member.sid),
                               'email': member.get('email','')}
                        yielded_sids.add(member.sid)
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
        lower_q = q.lower()
        for user in itertools.islice(self.env.get_known_users(), 0, limit):
            if True in (lower_q in userdetail.lower() for userdetail in user if userdetail):
                yield {'sid': user[0],
                       'name': user[1],
                       'email': user[2]}

class AutoCompleteSystem(Component):
    implements(ITemplateProvider, ITemplateStreamFilter, IGroupMembershipChangeListener)

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
    
    # Internal
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
        #show users from all groups, shown or not, on the members page
        add_script_data(req, {'project_users': self._project_users()})

        js = ''
        for input_ in inputs:
            if len(input_) == 3:
                selector, method_, options = input_
            else:
                selector, method_ = input_
                options = "{}"
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

    def _project_users(self, all=False):
        """ Get project users """
        people = {}
        session_users = False
        from simplifiedpermissionsadminplugin.simplifiedpermissions import SimplifiedPermissions
        if SimplifiedPermissions and self.env.is_enabled(SimplifiedPermissions):
            shown_groups = AutoCompleteGroup(self.env).get_autocomplete_values('shown_groups')
            sp = SimplifiedPermissions(self.env)
            for group, data in sp.group_memberships().items():
                if all or group in shown_groups:
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

    # IGroupMembershipChangeListener methods
    def user_added(self, username, groupname):
        pass

    def user_removed(self, username, groupname):
        pass
    
    def group_added(self, groupname):
        pass

    def group_removed(self, groupname):
        AutoCompleteGroup(self.env).remove_autocomplete_name('shown_groups', 
                                                             groupname)

class Select2AutoCompleteSystem(Component):
    implements(ITemplateProvider, ITemplateStreamFilter)

    autocompleter = ExtensionPoint(IADLDSAutoCompleteProvider)
    autocompleteusers = ExtensionPoint(ISelect2AutoCompleteUser)

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

    # Internal
    def _enable_autocomplete_for_page(self, req, method, filename, stream, data, inputs):
        add_stylesheet(req, 'autocomplete/css/select2_autocomplete.css')
        user_lookup_url = req.href('/ajax/userlookup/adlds')

        #There should never be multiple implementations of IADLDSAutoCompleteProvider
        endpoint = self.autocompleter[0].get_endpoint()
        if endpoint.get('permission') is None or req.perm.has_permission(endpoint.get('permission')):
            #Js to initialize select2
            #Note that "createSearchChoice" has a bit of a hack to it, it is
            #done this way in order to be able to add users that are not part
            #of the search result.. But they must still be able to be added if
            #validated.
            #Future versions of Select2 might make this simpler in which case
            #we should definitly rewrite that part.
            js = ''
            for input_ in inputs:
                selector, method_ = input_
                js += '$("%s").select2({' % (method_ + selector)
                js += '''width: "500px",
                        dropdownCssClass: "ui-dialog",'''
                js += 'placeholder: "%s %s",' % (_('Search users within this project and'), 
                                                 endpoint.get('name'))
                js += 'minimumInputLength: 2, ajax: {'
                js += 'url: "%s",' % req.href(endpoint.get('url'))
                js += '''
        dataType: 'json',
        data: function (term, page) {
            return {
                q: term
            };
          },
          results: function (data, page) {
                return { results: data };
          }
        },
        createSearchChoice: function(term, data) {
            if (data.length == 0) {
                return { id: -1, text:term }
            }
        },
        formatResult: userFormatResult,
        formatSelection: userFormatSelection,
        escapeMarkup: function (m) { 
            return m; 
        }
    });
    '''
        #Add formatting functions
        stream = stream | Transformer('//head').append(tag.script(Markup('''
function userFormatResult(user) {
    var markup = '';
    if (user.id == -1) {
        //Hack to be able to add users that are not searchable.
        markup += '<span id="select2_matches">';
        $.ajax({
            url: "%s",
            data: "q=" + user.text,
            success: function(data) {
                if (data.id !== undefined) {
                    user.id = data.id;
                    $('#select2_matches').text('Add external user' + data.id + ', ' + data.displayName + '?');
                }
                else {
                    $('#select2_matches').closest('li').removeClass('select2-result-selectable select2-highlighted');
                }
            }
        });
        markup += 'No matches found for ' + user.text + '</span>';
    }
    else {
        if (user.text !== undefined) {
            return '<div class="header"><h5>' + user.text + '</h5></div>';
        }
        markup = '<div class="result">';
        if (user.id !== undefined) {
            markup += '<span class="username"><p>' + user.id + '</p></span>';
        }
        if(user.displayName !== undefined || user.mail !== undefined) {
            markup += '<span class="info">';
            if (user.displayName !== undefined) {
                markup += '<p>' + user.displayName + '</p>';
            }
            if (user.mail !== undefined) {
                markup += '<p>&lt;' + user.mail + '&gt;</p>';
            }
            markup += '</span>';
        }
        markup += '</div>';
    }
    return markup;
}
function userFormatSelection(user) {
    return user.id;
}
''' % user_lookup_url), type="text/javascript"))
    
        stream = stream | Transformer('//head').append(tag.script('''
jQuery(document).ready(
    function($) {
        %s
});
''' % js,type="text/javascript"))

        return stream
