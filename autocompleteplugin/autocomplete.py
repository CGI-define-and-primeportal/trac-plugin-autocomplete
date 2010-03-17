from trac.core import Component, implements, TracError
from trac.config import Option, IntOption, ListOption
from trac.web import IRequestFilter
from trac.wiki import parse_args
from trac.web.chrome import ITemplateProvider, add_stylesheet
from pkg_resources import resource_filename
from trac.web.api import ITemplateStreamFilter
from genshi.builder import tag
from genshi.filters.transform import Transformer
from trac.env import IEnvironmentSetupParticipant

class AutoCompleteSystem(Component):
    implements(IRequestFilter, ITemplateProvider, ITemplateStreamFilter)
    
    
    ## IRequestFilter
    def pre_process_request(self, req, handler):
        return handler
        
    def post_process_request(self, req, template, data, content_type):
        return template, data, content_type
    
    ## ITemplateProvider
    
    def get_htdocs_dirs(self):
        return [('autocomplete', resource_filename(__name__, 'htdocs'))]
          
    def get_templates_dirs(self):
        return [(resource_filename(__name__, 'templates'))]

    ## ITemplateStreamFilter
    
    def filter_stream(self, req, method, filename, stream, data):
        add_stylesheet(req, 'autocomplete/css/autocomplete.css')
        return stream

        
