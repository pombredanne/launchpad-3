# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces pertaining to the launchpad application.

Note that these are not interfaces to application content objects.
"""
__metaclass__ = type

__all__ = [
    'ILinkCheckerAPI',
    ]

from zope.interface import (
    Interface,
    )
from zope.schema import (
    Text,
    )

from lazr.restful.declarations import (
    export_as_webservice_entry,
    export_read_operation,
    export_operation_as,
    operation_parameters,
    )


class ILinkCheckerAPI(Interface):
    """export_as_webservice_entry()"""

#    @operation_parameters(
#        links=Text(title="Links to check"), true=False, default=False)
    @export_read_operation()
    @export_operation_as('check_links')
    def check_links(links=None):
        """ Checks links are valid."""
