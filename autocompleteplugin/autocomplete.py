from trac.core import Component, implements, TracError
from trac.config import Option, IntOption, ListOption
from trac.web import IRequestFilter
from trac.wiki import parse_args
from trac.web.chrome import ITemplateProvider, add_stylesheet, add_script
from pkg_resources import resource_filename
from trac.web.api import ITemplateStreamFilter, IRequestHandler
from genshi.builder import tag
from genshi.filters.transform import Transformer
from trac.env import IEnvironmentSetupParticipant

class AutoCompleteSystem(Component):
    implements(IRequestHandler, ITemplateProvider, ITemplateStreamFilter)
    
    # ITemplateProvider
    
    def get_htdocs_dirs(self):
        return [('autocomplete', resource_filename(__name__, 'htdocs'))]
          
    def get_templates_dirs(self):
        return [(resource_filename(__name__, 'templates'))]

    # IRequestHandler methods
    def match_request(self, req):
        return req.path_info.startswith('/ajax/usersearch')

    def process_request(self, req):
        if req.path_info.startswith('/ajax/usersearch'):
            db = self.env.get_db_cnx()
            if not req.args.has_key("q"):
                raise ValueError("search string q not provided")
            search_term = "%%%s%%" % req.args['q']

            cursor = db.cursor()
            authenticated = 1
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
                """, (search_term,search_term,search_term,req.args['limit']))
            # TODO: ensure | is escaped in the data
            return "usersearch.txt", {'users': cursor}, "text/plain"

    # ITemplateStreamFilter
    
    def filter_stream(self, req, method, filename, stream, data):
        if filename == "ticket.html":
            add_stylesheet(req, 'autocomplete/css/jquery.autocomplete.css')
            add_script(req, 'autocomplete/js/jquery.autocomplete.pack.js')
            add_script(req, 'autocomplete/js/autocomplete.js')
            return stream

        return stream
    
