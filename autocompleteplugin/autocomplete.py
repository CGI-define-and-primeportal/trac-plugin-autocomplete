from trac.core import Component, implements, TracError
from trac.config import Option, IntOption, ListOption
from trac.web import IRequestFilter
from trac.wiki import parse_args
from trac.web.chrome import ITemplateProvider, add_stylesheet, add_script, add_script_data
from pkg_resources import resource_filename
from trac.web.api import ITemplateStreamFilter, IRequestHandler
from genshi.builder import tag
from genshi.filters.transform import Transformer
from trac.env import IEnvironmentSetupParticipant
from trac.util.presentation import to_json
from api import IAutoCompleteProvider
from trac.core import ExtensionPoint

class AutoCompleteSystem(Component):
    implements(IRequestHandler, ITemplateProvider, ITemplateStreamFilter, IAutoCompleteProvider)

    autocompleters = ExtensionPoint(IAutoCompleteProvider) 

    # IAutoCompleteProvider
    def get_endpoint(self):
        return {'url': '/ajax/usersearch/project',
                'name': 'This Project',
                'permission': 'TICKET_VIEW'}

    # ITemplateProvider
    def get_htdocs_dirs(self):
        return [('autocomplete', resource_filename(__name__, 'htdocs'))]
          
    def get_templates_dirs(self):
        return []

    # IRequestHandler methods
    def match_request(self, req):
        return req.path_info.startswith('/ajax/usersearch/project')

    def process_request(self, req):
        if req.path_info.startswith('/ajax/usersearch/project'):
            req.perm.require('TICKET_VIEW')
            users = self._session_query(req.args['q'], req.args['limit'])
            body = to_json(users).encode('utf8')
            req.send_response(200)
            req.send_header('Content-Type', "application/json")
            req.send_header('Content-Length', len(body))
            req.end_headers()
            req.write(body)

    # ITemplateStreamFilter
    def filter_stream(self, req, method, filename, stream, data):
        if filename in ("ticket.html",):
            add_stylesheet(req, 'autocomplete/css/jquery.autocomplete.css')
            add_stylesheet(req, 'autocomplete/css/autocomplete.css')
            add_script(req, 'autocomplete/js/jquery.autocomplete.pack.js')
            add_script(req, 'autocomplete/js/autocomplete.js')

            username_completers = []
            for autocompleter in self.autocompleters:
                endpoint = autocompleter.get_endpoint()
                if endpoint['permission'] is None or req.perm.has_permission(endpoint['permission']):
                    # Maybe we could support some 'local data' mode instead of just url?
                    # after all, we're already putting the project_users list into the page!
                    username_completers.append({'url': req.href(endpoint['url']),
                                                'name': endpoint['name']})
            add_script_data(req, {'username_completers': username_completers})
            # we could put this into some other URL which the browser could cache?
            add_script_data(req, {'project_users': self._all_project_users()})
            return stream

        return stream
    
    # internal
    def _all_project_users(self):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("""
            SELECT DISTINCT s.sid, n.value, e.value 
            FROM session AS s 
              LEFT JOIN session_attribute AS n
                ON (n.sid=s.sid AND n.authenticated=1 AND n.name='name')
              LEFT JOIN session_attribute AS e
                ON (e.sid=s.sid AND e.authenticated=1 AND e.name='email')
            WHERE s.authenticated=1 
            ORDER BY s.sid
            """)
        users = []
        for user in cursor:
            users.append({'sid': user[0],
                          'name': user[1],
                          'email': user[2]})
        return users
        
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
        users = []
        for user in cursor:
            users.append({'sid': user[0],
                          'name': user[1],
                          'email': user[2]})
        return users
