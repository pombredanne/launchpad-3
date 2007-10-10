# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Infestation interfaces."""

__metaclass__ = type

__all__ = [
    'IBugProductInfestationSet',
    'IBugPackageInfestationSet',
    'IBugProductInfestation',
    'IBugPackageInfestation',
    ]

from zope.interface import Interface, Attribute

from zope.schema import Bool, Choice, Datetime, Int
from canonical.launchpad import _

class IBugProductInfestation(Interface):
    """Represents a report that a bug does or does not affect the source
    package to which this infestation points. The extent of the
    'infestation' is given by the infestationstatus field, which takes on
    values documented in dbschema.BugInfestationStatus."""

    id = Int(title=_("Bug Project Infestation ID"), required=True,
        readonly=True)
    bug = Int(title=_('Bug ID'))
    explicit = Bool(title=_('Explicitly Created by a Human'))
    productrelease = Choice(title=_('Product Release'),
                            vocabulary='ProductRelease')
    infestationstatus = Choice(title=_('Infestation Status'),
                         vocabulary='InfestationStatus')
    datecreated = Datetime(title=_('Date Created'))
    creator = Int(title=_('Creator'))
    dateverified = Datetime(title=_('Date Verified'))
    verifiedby = Int(title=_('Verified By'))
    lastmodified = Datetime(title=_('Last Modified'))
    lastmodifiedby = Int(title=_('Last Modified By'))

    # used for launchpad page layout
    title = Attribute('Title')

class IBugPackageInfestation(Interface):
    """Represents a report that a bug does or does not affect the source
    package to which this infestation points. The extent of the
    'infestation' is given by the infestationstatus field, which takes on
    values documented in dbschema.BugInfestationStatus."""

    id = Int(title=_("Bug Package Infestation ID"), required=True, readonly=True)
    bug = Int(title=_('Bug ID'))
    sourcepackagerelease = Choice(title=_('Package Release'),
                                  vocabulary='PackageRelease')
    explicit = Bool(title=_('Explicitly Created by a Human'))
    infestationstatus = Choice(title=_('Infestation Status'),
                         vocabulary='InfestationStatus')
    datecreated = Datetime(title=_('Date Created'))
    creator = Int(title=_('Creator'))
    dateverified = Datetime(title=_('Date Verified'))
    verifiedby = Int(title=_('Verified By'))
    lastmodified = Datetime(title=_('Last Modified'))
    lastmodifiedby = Int(title=_('Last Modified By'))

    # used for launchpad page layout
    title = Attribute('Title')

class IBugProductInfestationSet(Interface):
    """A set for IBugProductInfestations."""

    title = Attribute('Title')

    bug = Int(title=_("Bug id"), readonly=True)

    def __getitem__(key):
        """Get a BugProductInfestation."""

    def __iter__():
        """Iterate through BugProductInfestations for a given bug."""

class IBugPackageInfestationSet(Interface):
    """A set for IBugPackageInfestations."""

    title = Attribute('Title')

    bug = Int(title=_("Bug id"), readonly=True)

    def __getitem__(key):
        """Get a BugPackageInfestation."""

    def __iter__():
        """Iterate through BugPackageInfestations for a given bug."""

