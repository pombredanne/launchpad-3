# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Infestation interfaces."""

__metaclass__ = type

__all__ = [
    'BugInfestationStatus',
    'IBugProductInfestationSet',
    'IBugPackageInfestationSet',
    'IBugProductInfestation',
    'IBugPackageInfestation',
    ]

from zope.interface import Interface, Attribute

from zope.schema import Bool, Choice, Datetime, Int
from canonical.launchpad import _

from canonical.lazr import DBEnumeratedType, DBItem


class BugInfestationStatus(DBEnumeratedType):
    """Bug Infestation Status.

    Malone is the bug tracking application that is part of Launchpad. It
    tracks the status of bugs in different distributions as well as
    upstream. This schema documents the kinds of infestation of a bug
    in a code release.
    """

    AFFECTED = DBItem(60, """
        Affected

        This bug is believed to affect that code release. The
        `verifiedby` field will indicate whether that has been verified
        by a package maintainer.
        """)

    DORMANT = DBItem(50, """
        Dormant

        The bug exists in the code of this code release, but it is dormant
        because that codepath is unused in this release.
        """)

    VICTIMIZED = DBItem(40, """
        Victimized

        This code release does not actually contain the buggy code, but
        it is affected by the bug nonetheless because of the way it
        interacts with the products or packages that are actually buggy.
        Often users will report a bug against the package which displays
        the symptoms when the bug itself lies elsewhere.
        """)

    FIXED = DBItem(30, """
        Fixed

        It is believed that the bug is actually fixed in this release of code.
        Setting the "fixed" flag allows us to generate lists of bugs fixed
        in a release.
        """)

    UNAFFECTED = DBItem(20, """
        Unaffected

        It is believed that this bug does not infest this release of code.
        """)

    UNKNOWN = DBItem(10, """
        Unknown

        We don't know if this bug infests that code release.
        """)


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

