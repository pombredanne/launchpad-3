# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type
__all__ = ['ISourcePackageRecipeData']


from zope.interface import Attribute, Interface
from zope.schema import Int, Text

# Not sure this will end up being public at all, actually...

class ISourcePackageRecipeData(Interface):
    """ """

    id = Int(required=True, readonly=True)
    recipe = Text(required=True)

    referenced_branches = Attribute() # Probably shouldn't be Attribute...
