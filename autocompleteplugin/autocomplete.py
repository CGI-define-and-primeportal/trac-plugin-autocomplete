from trac.core import Component, implements, TracError
from trac.config import BoolOption
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
        return {"ticket.html": ["field-owner",
                                "field-reporter",
                                "action_reassign_reassign_owner"]}
    
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
            users = self._users_query(req.args['q'], req.args['limit'])
            body = to_json(list(users)).encode('utf8')
            req.send_response(200)
            req.send_header('Content-Type', "application/json")
            req.send_header('Content-Length', len(body))
            req.end_headers()
            req.write(body)

    def _users_query(self, q, limit=10):
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
                'name': 'Current Users of %s' % self.env.project_name,
                'permission': 'TICKET_VIEW'}

    # IRequestHandler methods
    def match_request(self, req):
        return req.path_info.startswith(self.ownurl)

    def process_request(self, req):
        if req.path_info.startswith(self.ownurl):
            req.perm.require('TICKET_VIEW')
            users = self._session_query(req.args['q'], req.args['limit'])
            body = to_json(list(users)).encode('utf8')
            req.send_response(200)
            req.send_header('Content-Type', "application/json")
            req.send_header('Content-Length', len(body))
            req.end_headers()
            req.write(body)

    def _session_query(self, q, limit=10):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        search_term = "%%%s%%" % q
        cursor.execute("""
            SELECT DISTINCT s.sid, n.value, e.value 
            FROM session AS s 
              LEFT JOIN session_attribute AS n
                ON (n.sid=s.sid AND n.authenticated=1 AND n.name='name')
              LEFT JOIN session_attribute AS e
                ON (e.sid=s.sid AND e.authenticated=1 AND e.name='email')
            WHERE s.authenticated=1 
            AND ( s.sid LIKE %s OR n.value LIKE %s OR e.value LIKE %s)
            ORDER BY s.sid
            LIMIT %s
            """, (search_term,search_term,search_term,limit))
        for user in cursor:
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
               return  self._enable_autocomplete_for_page(req, method, filename, stream, data, d[filename])
        return stream
    
    # internal
    def _enable_autocomplete_for_page(self, req, method, filename, stream, data, inputs):
        add_stylesheet(req, 'autocomplete/css/jquery.autocomplete.css')
        add_stylesheet(req, 'autocomplete/css/autocomplete.css')
        add_script(req, 'autocomplete/js/jquery.autocomplete.pack.js')
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
        add_script_data(req, {'project_users': list(self._all_project_users())})
        
        js = "\n".join(['$("#%s").makeTracUserSearch();' % _ for _ in inputs])
        stream = stream | Transformer('//head').append(tag.script("""
        jQuery(document).ready(
        function($) {
        %s
        });
        """ % js,type="text/javascript"))
        
        return stream
    
    def _all_project_users(self):
        for username, name, email in self.env.get_known_users():
            yield {'sid': username,
                   'name': name,
                   'email': email}
        
