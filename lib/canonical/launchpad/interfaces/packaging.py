# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Packaging interfaces."""

__metaclass__ = type

__all__ = [
    'IPackaging',
    'IPackagingUtil',
    ]

from zope.schema import Choice, Datetime, Int
from zope.interface import Interface, Attribute

from canonical.launchpad import _
from canonical.launchpad.interfaces import IHasOwner


class IPackaging(IHasOwner):
    """
    A Packaging entry. It relates a SourcePackageName, DistroSeries
    and ProductSeries, with a packaging type. So, for example, we use this
    table to specify that the mozilla-firefox package in hoary is actually a
    primary packaging of firefox 1.0 series releases.
    """
    id = Int(title=_('Packaging ID'))

    productseries = Choice(
        title=_('Upstream Series'), required=True,
        vocabulary="ProductSeries", description=_(
        "The series for this source package. The same distribution "
        "release may package two different series of the same project as "
        "different source packages. For example: python2.4 and python2.5"))

    sourcepackagename = Choice(
        title=_("Source Package Name"), required=True,
        vocabulary='SourcePackageName')

    distroseries = Choice(
        title=_("Distribution Series"), required=True,
        vocabulary='DistroSeries')

    packaging = Choice(
        title=_('Packaging'), required=True, vocabulary='PackagingType')

    datecreated = Datetime(
        title=_('Date Created'), required=True, readonly=True)

    sourcepackage = Attribute(_("A source package that is constructed from "
        "the distroseries and sourcepackagename of this packaging record."))


class IPackagingUtil(Interface):
    """Utilities to handle Packaging."""

    def createPackaging(productseries, sourcepackagename,
                        distroseries, packaging, owner):
        """Create Packaging entry."""

    def packagingEntryExists(productseries, sourcepackagename,
                             distroseries):
        """Does this packaging entry already exists?"""
