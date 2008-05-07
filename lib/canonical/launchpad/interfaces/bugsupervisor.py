# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interface for objects which have a bug contact."""

__metaclass__ = type

__all__ = [
    'IHasBugSupervisor',
    ]

from zope.schema import Choice

from canonical.launchpad import _
from canonical.launchpad.interfaces.structuralsubscription import (
    IStructuralSubscriptionTarget)


class IHasBugSupervisor(IStructuralSubscriptionTarget):

    bug_supervisor = Choice(
        title=_("Bug Supervisor"),
        description=_(
            "The person or team responsible for bug management."),
        required=False, vocabulary='ValidPersonOrTeam')

    def setBugSupervisor(self, bug_supervisor, user):
        """Set the bug contact and create a bug subscription."""
