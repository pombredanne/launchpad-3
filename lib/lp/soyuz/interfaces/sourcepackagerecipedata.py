# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type
__all__ = ['ISourcePackageRecipeData']


from zope.interface import Attribute, Interface
from zope.schema import Datetime, Int, Object, Text

from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.sourcepackagename import ISourcePackageName


class ISourcePackageRecipeData(Interface):
    """ """

    id = Int(required=True, readonly=True)
    date_created = Datetime(required=True, readonly=True)
    distroseries = Object(schema=IDistroSeries)
    sourcepackagename = Object(schema=ISourcePackageName)
    recipe = Text(required=True)

    referenced_branches = Attribute() # Probably shouldn't be Attribute...
