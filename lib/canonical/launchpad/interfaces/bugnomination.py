# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces related to bug nomination."""

__metaclass__ = type

__all__ = [
    'BugNominationStatusError',
    'NominationError',
    'IBugNomination',
    'IBugNominationForm',
    'IBugNominationSet',
    'BugNominationStatus',
    'NominationSeriesObsoleteError']

from zope.schema import Int, Datetime, Choice, Set
from zope.interface import Interface, Attribute

from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    IHasBug, IHasDateCreated, IHasOwner, can_be_nominated_for_serieses)

from canonical.lazr import DBEnumeratedType, DBItem

class NominationError(Exception):
    """The bug cannot be nominated for this release."""


class NominationSeriesObsoleteError(Exception):
    """A bug cannot be nominated for an obsolete series."""


class BugNominationStatusError(Exception):
    """A error occurred while trying to set a bug nomination status."""


class BugNominationStatus(DBEnumeratedType):
    """Bug Nomination Status.

    The status of the decision to fix a bug in a specific release.
    """

    PROPOSED = DBItem(10, """
        Nominated

        This nomination hasn't yet been reviewed, or is still under
        review.
        """)

    APPROVED = DBItem(20, """
        Approved

        The release management team has approved fixing the bug for this
        release.
        """)

    DECLINED = DBItem(30, """
        Declined

        The release management team has declined fixing the bug for this
        release.
        """)


class IBugNomination(IHasBug, IHasOwner, IHasDateCreated):
    """A nomination for a bug to be fixed in a specific series.

    A nomination can apply to an IDistroSeries or an IProductSeries.
    """
    # We want to customize the titles and descriptions of some of the
    # attributes of our parent interfaces, so we redefine those specific
    # attributes below.
    id = Int(title=_("Bug Nomination #"))
    bug = Int(title=_("Bug #"))
    date_created = Datetime(
        title=_("Date Submitted"),
        description=_("The date on which this nomination was submitted."),
        required=True, readonly=True)
    date_decided = Datetime(
        title=_("Date Decided"),
        description=_(
            "The date on which this nomination was approved or declined."),
        required=False, readonly=True)
    distroseries = Choice(
        title=_("Series"), required=False,
        vocabulary="DistroSeries")
    productseries = Choice(
        title=_("Series"), required=False,
        vocabulary="ProductSeries")
    owner = Choice(
        title=_('Submitter'), required=True, readonly=True,
        vocabulary='ValidPersonOrTeam')
    decider = Choice(
        title=_('Decided By'), required=False, readonly=True,
        vocabulary='ValidPersonOrTeam')
    target = Attribute(
        "The IProductSeries or IDistroSeries of this nomination.")
    status = Choice(
        title=_("Status"), vocabulary=BugNominationStatus,
        default=BugNominationStatus.PROPOSED)

    def approve(approver):
        """Approve this bug for fixing in a series.

        :approver: The IPerson that approves this nomination and that
                   will own the created bugtasks.

        The status is set to APPROVED and the appropriate IBugTask(s)
        are created for the nomination target.

        A nomination in any state can be approved. If the nomination is
        /already/ approved, this method is a noop.
        """

    def decline(decliner):
        """Decline this bug for fixing in a series.

        :decliner: The IPerson that declines this nomination.

        The status is set to DECLINED.

        If called on a nomination that is in APPROVED state, a
        BugNominationStatusError is raised. If the nomination was
        already DECLINED, this method is a noop.
        """

    # Helper methods for making status checking more readable.
    def isProposed():
        """Is this nomination in Proposed state?"""

    def isDeclined():
        """Is this nomination in Declined state?"""

    def isApproved():
        """Is this nomination in Approved state?"""

    def canApprove(person):
        """Is this person allowed to approve the nomination?"""


class IBugNominationSet(Interface):
    """The set of IBugNominations."""

    def get(id):
        """Get a nomination by its ID.

        Returns an IBugNomination. Raises a NotFoundError is the
        nomination was not found.
        """


class IBugNominationForm(Interface):
    """The browser form for nominating bugs for series."""

    nominatable_serieses = Set(
        title=_("Series that can be nominated"), required=True,
        value_type=Choice(vocabulary="BugNominatableSerieses"),
        constraint=can_be_nominated_for_serieses)


