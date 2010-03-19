from trac.core import Interface

class IAutoCompleteProvider(Interface):
    """Extention point interface for components providing autocomplete AJAX endpoints"""

    def get_endpoint():
        """Return an iterable which provides dictionaries like:
        {'url': '/ajax/usersearch/area',
         'name': 'Search Domain',
         'permission': 'SEARCH_AREA'}

         permission can be None
         """
