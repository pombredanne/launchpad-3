# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Packaging interfaces."""

__metaclass__ = type

__all__ = [
    'IPackaging',
    'IPackagingUtil',
    ]

from zope.schema import Choice, Datetime, Int
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class IPackaging(Interface):
    """
    A Packaging entry. It relates a SourcePackageName, DistroRelease
    and ProductSeries, with a packaging type. So, for example, we use this
    table to specify that the mozilla-firefox package in hoary is actually a
    primary packaging of firefox 1.0 series releases.
    """
    id = Int(title=_('Packaging ID'))

    productseries = Choice(title=_('Product Series'), required=True,
        vocabulary="ProductSeries", description=_("The branch or "
        "'product series' that this is a packaging of. We expressly "
        "need to know the branch because you might have packages "
        "of two different branches of a product in the same release "
        "of a distribution, if for example you have packages of both "
        "GiMP 2.0 and GiMP 2.1 in the distro, it is important to make "
        "sure this link is to the correct branch."))

    sourcepackagename = Choice(title=_("Source Package Name"),
                           required=True, vocabulary='SourcePackageName')

    distrorelease = Choice(title=_("Distribution Release"),
                           required=True, vocabulary='DistroRelease')

    packaging = Choice(title=_('Packaging'), required=True,
                       vocabulary='PackagingType')
    datecreated = Datetime(
        title=_('Date Created'), required=True, readonly=True)
    owner = Int()
    # XXX sabdfl can we get away with this? or do we need ownerID?
    #ownerID = Int(title=_('Creator'), required=True, readonly=True)
    #owner = Attribute("The IPerson who created this entry.")

    sourcepackage = Attribute("A source package that is constructed from "
        "the distrorelease and sourcepackagename of this packaging record.")

class IPackagingUtil(Interface):
    """Utilities to handle Packaging."""

    def createPackaging(productseries, sourcepackagename,
                        distrorelease, packaging):
        """Create Packaging entry."""
