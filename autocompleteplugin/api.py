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

class IADLDSAutoCompleteProvider(Interface):
    """Extension point interface for a ADLDS component providing autocomplete AJAX 
    endpoints to Extended AutocompleteUser. This interface should only be 
    implemented once for a ADLDS provider.
    """

    def get_endpoint():
        """Return dictionary like:
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
        {'ticket.html': [('#field-owner','select'),
                         ('#field-owner','text', 'source: $.noop'}),
                         ...
                         ]}
        """

class ISelect2AutoCompleteUser(Interface):
    """Extension point interface for components showing pages which
    need extended autocompleting fields.
    """

    def get_templates():
        """Return a dictionary like:
        {'ticket.html': [('#field-owner','select'),
                         ('#field-owner','text', 'source: $.noop'}),
                         ...
                         ]}
        """
