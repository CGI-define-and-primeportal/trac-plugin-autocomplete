from trac.core import Interface

class IAutoCompleteProvider(Interface):
    """Extention point interface for components providing autocomplete AJAX endpoints"""

    def get_endpoint():
        """Return an iterable which provides dictionaries like:
        {'url': '/ajax/usersearch/area',
         'name': 'Search Domain',
         'permission': 'SEARCH_AREA'}

         permission can be None. The url will be adjusted to be
         correct for this Trac instance.
         """
        
class IAutoCompleteUser(Interface):
    """Extention point interface for components showing pages which
    need autocompleting fields.

    The genshi template should include HTML elements which match
    jQuery selectors given in the list. They will be converted into
    select elements with search facilities, based on which
    IAutoCompleteProviders are available and the current user
    permissions.
    """

    def get_templates():
        """Return a dictionary like:
        {'ticket.html': [('#field-owner','select', {'option_name','option value'}),...]}
        """
