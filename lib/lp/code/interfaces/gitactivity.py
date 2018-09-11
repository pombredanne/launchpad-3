# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Git repository activity logs."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'IGitActivity',
    'IGitActivitySet',
    ]

from lazr.restful.fields import Reference
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Choice,
    Datetime,
    Dict,
    Int,
    Text,
    TextLine,
    )

from lp import _
from lp.code.enums import GitActivityType
from lp.code.interfaces.gitrepository import IGitRepository
from lp.services.fields import (
    PersonChoice,
    PublicPersonChoice,
    )


class IGitActivity(Interface):
    """An activity log entry for a Git repository."""

    id = Int(title=_("ID"), readonly=True, required=True)

    repository = Reference(
        title=_("Repository"), required=True, readonly=True,
        schema=IGitRepository,
        description=_("The repository that this log entry is for."))

    date_changed = Datetime(
        title=_("Date changed"), required=True, readonly=True,
        description=_("The time when this change happened."))

    changer = PublicPersonChoice(
        title=_("Changer"), required=True, readonly=True,
        vocabulary="ValidPerson",
        description=_("The user who made this change."))

    changee = PersonChoice(
        title=_("Changee"), required=False, readonly=True,
        vocabulary="ValidPersonOrTeam",
        description=_("The person or team that this change was applied to."))

    changee_description = Attribute(
        "A human-readable description of the changee.")

    what_changed = Choice(
        title=_("What changed"), required=True, readonly=True,
        vocabulary=GitActivityType,
        description=_("The property of the repository that changed."))

    old_value = Dict(
        title=_("Old value"), required=False, readonly=True,
        description=_("The value before the change."),
        key_type=TextLine(), value_type=Text())

    new_value = Dict(
        title=_("New value"), required=False, readonly=True,
        description=_("The value after the change."),
        key_type=TextLine(), value_type=Text())


class IGitActivitySet(Interface):
    """Utilities for managing Git repository activity log entries."""

    def logRuleAdded(rule, user):
        """Log that an access rule was added.

        :param rule: The `IGitRule` that was added.
        :param user: The `IPerson` who added it.
        :return: The new `IGitActivity`.
        """

    def logRuleChanged(old_rule, new_rule, user):
        """Log that an access rule was changed.

        :param old_rule: The `IGitRule` before the change.
        :param new_rule: The `IGitRule` after the change.
        :param user: The `IPerson` who made the change.
        :return: The new `IGitActivity`.
        """

    def logRuleRemoved(rule, user):
        """Log that an access rule was removed.

        :param rule: The `IGitRule` that was removed.
        :param user: The `IPerson` who removed it.
        :return: The new `IGitActivity`.
        """

    def logRuleMoved(rule, old_position, new_position, user):
        """Log that an access rule was moved to a different position.

        :param rule: The `IGitRule` that was moved.
        :param old_position: The old position in its repository's order.
        :param new_position: The new position in its repository's order.
        :param user: The `IPerson` who moved it.
        :return: The new `IGitActivity`.
        """

    def logGrantAdded(grant, user):
        """Log that an access grant was added.

        :param grant: The `IGitGrant` that was added.
        :param user: The `IPerson` who added it.
        :return: The new `IGitActivity`.
        """

    def logGrantChanged(old_grant, new_grant, user):
        """Log that an access grant was changed.

        :param old_grant: The `IGitGrant` before the change.
        :param new_grant: The `IGitGrant` after the change.
        :param user: The `IPerson` who made the change.
        :return: The new `IGitActivity`.
        """

    def logGrantRemoved(grant, user):
        """Log that an access grant was removed.

        :param grant: The `IGitGrant` that was removed.
        :param user: The `IPerson` who removed it.
        :return: The new `IGitActivity`.
        """
