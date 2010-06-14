# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Interface for objects which have a bug contact."""

__metaclass__ = type

__all__ = [
    'IHasBugSupervisor',
    ]

from canonical.launchpad import _
from canonical.launchpad.fields import ParticipatingPersonChoice

from zope.interface import Interface

from lazr.restful.declarations import (
    REQUEST_USER, call_with, exported, export_write_operation,
    mutator_for, operation_parameters)
from lazr.restful.interface import copy_field


class IHasBugSupervisor(Interface):

    bug_supervisor = exported(ParticipatingPersonChoice(
        title=_("Bug Supervisor"),
        description=_(
            "The person or team responsible for bug management."),
        required=False, vocabulary='ValidPersonOrTeam', readonly=True))

    @mutator_for(bug_supervisor)
    @call_with(user=REQUEST_USER)
    @operation_parameters(
        bug_supervisor=copy_field(bug_supervisor))
    @export_write_operation()
    def setBugSupervisor(bug_supervisor, user):
        """Set the bug contact and create a bug subscription."""
