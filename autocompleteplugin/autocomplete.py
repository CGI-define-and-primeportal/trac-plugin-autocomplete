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

import ldap
import ldap.filter
ldap.set_option(ldap.OPT_REFERRALS, 0)

class AutoCompleteSystem(Component):
    implements(IRequestHandler, ITemplateProvider, ITemplateStreamFilter)

    ldap_base      = Option('autocomplete', 'ldap_base', '',"LDAP base")
    ldap_server    = Option('autocomplete', 'ldap_server', '',"LDAP server hostname")
    ldap_who       = Option('autocomplete', 'ldap_who', '',"LDAP bind username")
    ldap_cred      = Option('autocomplete', 'ldap_cred', '',"LDAP bind password")
    ldap_domain    = Option('autocomplete', 'ldap_domain', '',"AD Domain served by this LDAP server")
    
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
            if not req.args.has_key("q"):
                raise ValueError("search string q not provided")

            if req.args['domain'] == "project":
                users = self._session_query(req.args['q'], req.args['limit'])
            elif req.args['domain'] == "groupinfra":
                users = self._ldap_query(req.args['q'], req.args['limit'])
            else:
                users = []
            # TODO: ensure | is escaped in the data
            return "usersearch.txt", {'users': users}, "text/plain"

    # ITemplateStreamFilter
    
    def filter_stream(self, req, method, filename, stream, data):
        if filename == "ticket.html":
            add_stylesheet(req, 'autocomplete/css/jquery.autocomplete.css')
            add_script(req, 'autocomplete/js/jquery.autocomplete.pack.js')
            add_script(req, 'autocomplete/js/autocomplete.js')
            return stream

        return stream
    
    # internal
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
        return cursor

    def _ldap_query(self, q, limit=10):
        if not self.ldap_server and self.ldap_who:
            return []
        l = ldap.open(self.ldap_server)
        l.simple_bind_s(self.ldap_who, self.ldap_cred)
        # support finding people like groupinfra\username
        if q.startswith("%s\\" % self.ldap_domain):
            q = q[len(self.ldap_domain) + 1:]
        safeq = ldap.filter.escape_filter_chars(q)
        query = "(&(objectClass=user)(|(mail=%s*)(displayName=%s*)(sAMAccountName=%s*)))" % (safeq, safeq, safeq)
        # we need a string, not unicode, for the attribute name
        users = []
        for item in l.search_s(self.ldap_base, ldap.SCOPE_SUBTREE, query, ["mail".encode("UTF8"),
                                                                           "displayName".encode("UTF8"),
                                                                           "sAMAccountName".encode("UTF8")]):
            if item[0]: # don't process ldap references
                details = item[1]
                try:
                    users.append(("%s\\%s" % (self.ldap_domain, details['sAMAccountName'][0]),
                                  details['displayName'][0].decode('utf8'),
                                  details['mail'][0]))
                except KeyError, e:
                    self.log.debug("Skipping LDAP result %s due to KeyError: %s", item, e)
        return users
