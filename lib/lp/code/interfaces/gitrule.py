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
from lp.registry.interfaces.person import IPerson


class IGitRuleView(Interface):
    """`IGitRule` attributes that require launchpad.View."""

    id = Int(title=_("ID"), readonly=True, required=True)

    repository = Reference(
        title=_("Repository"), required=True, readonly=True,
        schema=IGitRepository,
        description=_("The repository that this rule is for."))

    ref_pattern = TextLine(
        title=_("Pattern"), required=True, readonly=False,
        description=_("The pattern of references matched by this rule."))

    creator = Reference(
        title=_("Creator"), required=True, readonly=True,
        schema=IPerson,
        description=_("The user who created this rule."))

    date_created = Datetime(
        title=_("Date created"), required=True, readonly=True,
        description=_("The time when this rule was created."))

    date_last_modified = Datetime(
        title=_("Date last modified"), required=True, readonly=True,
        description=_("The time when this rule was last modified."))

    grants = Attribute("The access grants for this rule.")


class IGitRuleEdit(Interface):
    """`IGitRule` attributes that require launchpad.Edit."""

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

    def destroySelf():
        """Delete this rule."""


class IGitRule(IGitRuleView, IGitRuleEdit):
    """An access rule for a Git repository."""
