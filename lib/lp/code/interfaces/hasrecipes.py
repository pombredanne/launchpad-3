# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface definitions for IHasRecipes."""

__metaclass__ = type
__all__ = [
    'IHasRecipes',
    ]


from zope.interface import (
    Attribute,
    Interface,
    )


class IHasRecipes(Interface):
    """An object that has recipes."""

    def getRecipes():
        """Returns all recipes associated with the object."""
