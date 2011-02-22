# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface definitions for IHasRecipes."""

__metaclass__ = type
__all__ = [
    'IHasRecipes',
    ]


from zope.interface import (
    Interface,
    )

from lazr.restful.declarations import (
    export_read_operation,
    operation_returns_collection_of,
    )

class IHasRecipes(Interface):
    """An object that has recipes."""

    @operation_returns_collection_of(Interface)
    @export_read_operation()
    def getRecipes():
        """Returns all recipes associated with the object."""
