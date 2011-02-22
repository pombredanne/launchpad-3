# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface for the Jobs system to change memberships or merge persons."""

__metaclass__ = type
__all__ = [
    'IMembershipNotificationJob',
    'IMembershipNotificationJobSource',
    'IPersonMergeJob',
    'IPersonMergeJobSource',
    'IPersonTransferJob',
    'IPersonTransferJobSource',
    ]

from zope.interface import Attribute
from zope.schema import (
    Int,
    Object,
    )

from canonical.launchpad import _
from lp.services.fields import PublicPersonChoice
from lp.services.job.interfaces.job import (
    IJob,
    IJobSource,
    IRunnableJob,
    )


class IPersonTransferJob(IRunnableJob):
    """A Job related to team membership or a person merge."""

    id = Int(
        title=_('DB ID'), required=True, readonly=True,
        description=_("The tracking number for this job."))

    job = Object(
        title=_('The common Job attributes'),
        schema=IJob,
        required=True)

    minor_person = PublicPersonChoice(
        title=_('The person being added to the major person/team'),
        vocabulary='ValidPersonOrTeam',
        required=True)

    major_person = PublicPersonChoice(
        title=_('The person or team receiving the minor person'),
        vocabulary='ValidPersonOrTeam',
        required=True)

    metadata = Attribute('A dict of data about the job.')


class IPersonTransferJobSource(IJobSource):
    """An interface for acquiring IPersonTransferJobs."""

    def create(minor_person, major_person, metadata):
        """Create a new IPersonTransferJob."""


class IMembershipNotificationJob(IPersonTransferJob):
    """A Job to notify new members of a team of that change."""

    member = PublicPersonChoice(
        title=_('Alias for minor_person attribute'),
        vocabulary='ValidPersonOrTeam',
        required=True)

    team = PublicPersonChoice(
        title=_('Alias for major_person attribute'),
        vocabulary='ValidPersonOrTeam',
        required=True)


class IMembershipNotificationJobSource(IJobSource):
    """An interface for acquiring IMembershipNotificationJobs."""

    def create(member, team, reviewer, old_status, new_status,
               last_change_comment=None):
        """Create a new IMembershipNotificationJob."""


class IPersonMergeJob(IPersonTransferJob):
    """A Job that merges one person or team into another."""

    from_person = PublicPersonChoice(
        title=_('Alias for minor_person attribute'),
        vocabulary='ValidPersonOrTeam',
        required=True)

    to_person = PublicPersonChoice(
        title=_('Alias for major_person attribute'),
        vocabulary='ValidPersonOrTeam',
        required=True)


class IPersonMergeJobSource(IJobSource):
    """An interface for acquiring IMembershipNotificationJobs."""

    def create(from_person, to_person):
        """Create a new IMembershipNotificationJob."""

    def find(from_person=None, to_person=None):
        """Finds pending or running merge jobs.

        :param from_person: Match jobs on `from_person`, or `None` to ignore
            `from_person`.
        :param to_person: Match jobs on `to_person`, or `None` to ignore
            `from_person`.
        :return: A `ResultSet` yielding `IPersonMergeJob`.

        If both `from_person` and `to_person` is supplied, only jobs where
        both match are returned.
        """
