# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Interface for objects which have a bug contact."""

__metaclass__ = type

__all__ = [
    'IHasBugSupervisor',
    ]

from canonical.launchpad import _
from canonical.launchpad.fields import PersonChoice

from zope.interface import Interface

from lazr.restful.declarations import (
    REQUEST_USER, call_with, exported, export_write_operation,
    mutator_for, operation_parameters)
from lazr.restful.interface import copy_field


class IHasBugSupervisor(Interface):

    bug_supervisor = exported(PersonChoice(
        title=_("Bug Supervisor"),
        description=_(
            "The Launchpad id of the person or team (preferred) responsible "
            "for bug management.  The bug supervisor will be subscribed to "
            "all bugs and will receive email about all activity on all bugs "
            "for this project, so that should be a factor in your decision.  "
            "The bug supervisor will also have access to all private bugs."),



        required=False, vocabulary='ValidPersonOrTeam', readonly=True))

    @mutator_for(bug_supervisor)
    @call_with(user=REQUEST_USER)
    @operation_parameters(
        bug_supervisor=copy_field(bug_supervisor))
    @export_write_operation()
    def setBugSupervisor(bug_supervisor, user):
        """Set the bug contact and create a bug subscription."""
