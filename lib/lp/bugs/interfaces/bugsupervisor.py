# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Interface for objects which have a bug contact."""

__metaclass__ = type

__all__ = [
    'IHasBugSupervisor',
    ]

from lazr.restful.declarations import (
    call_with,
    export_write_operation,
    exported,
    mutator_for,
    operation_for_version,
    operation_parameters,
    REQUEST_USER,
    )
from lazr.restful.interface import copy_field
from zope.interface import Interface

from canonical.launchpad import _
from lp.services.fields import PersonChoice


class IHasBugSupervisor(Interface):

    bug_supervisor = exported(PersonChoice(
        title=_("Bug Supervisor"),
        description=_(
            "The Launchpad id of the person or team (preferred) responsible "
            "for bug management. Mail about all bug activity will be sent to "
            "the supervisor by default. The bug supervisor can change the "
            "bug mail rules to limit the volume of email."),
        required=False, vocabulary='ValidPersonOrTeam', readonly=True))

    @mutator_for(bug_supervisor)
    @call_with(user=REQUEST_USER)
    @operation_parameters(
        bug_supervisor=copy_field(bug_supervisor))
    @export_write_operation()
    @operation_for_version('beta')
    def setBugSupervisor(bug_supervisor, user):
        """Set the bug contact and create a bug subscription."""
