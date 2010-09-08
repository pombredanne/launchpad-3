# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for using the Jobs system for Memberships."""

__metaclass__ = type
__all__ = [
    'IMembershipJob',
    'IMembershipJobSource',
    ]

from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Int,
    Object,
    )

from canonical.launchpad import _
from lp.services.fields import PublicPersonChoice
from lp.services.job.interfaces.job import (
    IJob,
    IJobSource,
    )


class IMembershipJob(Interface):
    """A Job related to a team membership."""

    id = Int(
        title=_('DB ID'), required=True, readonly=True,
        description=_("The tracking number for this job."))

    job = Object(
        title=_('The common Job attributes'),
        schema=IJob,
        required=True)

    super_team = PublicPersonChoice(
        title=_('The team that is getting a new member'),
        vocabulary='ValidTeam',
        required=True)

    new_member = PublicPersonChoice(
        title=_('The person or team that is being added as a member'),
        vocabulary='ValidPersonOrTeam',
        required=True)

    metadata = Attribute('A dict of data about the job.')


class IMembershipJobSource(IJobSource):
    """An interface for acquiring IMembershipJobs."""

    def create(super_team, new_member):
        """Create a new IMembershipJob."""
