# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Interfaces related to bug nomination."""

__metaclass__ = type

__all__ = ['IBugNomination']

from zope.schema import Int, Datetime, Choice
from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    IHasBug, IHasDateCreated, IHasOwner)

class IBugNomination(IHasBug, IHasOwner, IHasDateCreated):
    """A nomination for a bug to be fixed in a specific release.

    A nomination can apply to an IDistroRelease or an IProductSeries.
    """
    # We want to customize the titles and descriptions of some of the
    # attributes of our parent interfaces, so we redefine those specific
    # attributes below.
    id = Int(title=_("Bug Nomination #"))
    datecreated = Datetime(
        title=_("Date Submitted"),
        description=_("The date on which this nomination was submitted."))
    distrorelease = Choice(
        title=_("Distribution Release"), required=False,
        vocabulary="DistroRelease")
    productseries = Choice(
        title=_("Product Series"), required=False,
        vocabulary="ProductSeries")
    owner = Choice(
        title=_('Submitter'), required=True, readonly=True,
        vocabulary='ValidPersonOrTeam')
