# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Git repository access rules."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'IGitRule',
    ]

from lazr.restful.fields import Reference
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Datetime,
    Int,
    TextLine,
    )

from lp import _
from lp.code.interfaces.gitrepository import IGitRepository
from lp.services.fields import PublicPersonChoice


class IGitRuleView(Interface):
    """`IGitRule` attributes that require launchpad.View."""

    id = Int(title=_("ID"), readonly=True, required=True)

    repository = Reference(
        title=_("Repository"), required=True, readonly=True,
        schema=IGitRepository,
        description=_("The repository that this rule is for."))

    creator = PublicPersonChoice(
        title=_("Creator"), required=True, readonly=True,
        vocabulary="ValidPerson",
        description=_("The user who created this rule."))

    date_created = Datetime(
        title=_("Date created"), required=True, readonly=True,
        description=_("The time when this rule was created."))

    position = Int(
        title=_("Position"), required=True, readonly=True,
        description=_(
            "The position of this rule in its repository's rule order."))

    grants = Attribute("The access grants for this rule.")


class IGitRuleEditableAttributes(Interface):
    """`IGitRule` attributes that can be edited.

    These attributes need launchpad.View to see, and launchpad.Edit to change.
    """

    ref_pattern = TextLine(
        title=_("Pattern"), required=True, readonly=False,
        description=_("The pattern of references matched by this rule."))

    date_last_modified = Datetime(
        title=_("Date last modified"), required=True, readonly=True,
        description=_("The time when this rule was last modified."))


class IGitRuleEdit(Interface):
    """`IGitRule` attributes that require launchpad.Edit."""

    def move(position, user):
        """Move this rule to a new position in its repository's rule order.

        :param position: The new position.  For example, 0 puts the rule at
            the start, while `len(repository.rules)` puts the rule at the
            end.
        :param user: The `IPerson` who is moving the rule.
        """

    def addGrant(grantee, grantor, can_create=False, can_push=False,
                 can_force_push=False):
        """Add an access grant to this rule.

        :param grantee: The `IPerson` who is being granted permission, or an
            item of `GitGranteeType` other than `GitGranteeType.PERSON` to
            grant permission to some other kind of entity.
        :param grantor: The `IPerson` who is granting permission.
        :param can_create: Whether the grantee can create references
            matching this rule.
        :param can_push: Whether the grantee can push references matching
            this rule.
        :param can_force_push: Whether the grantee can force-push references
            matching this rule.
        """

    def destroySelf(user):
        """Delete this rule.

        :param user: The `IPerson` doing the deletion.
        """


class IGitRule(IGitRuleView, IGitRuleEditableAttributes, IGitRuleEdit):
    """An access rule for a Git repository."""
