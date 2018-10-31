# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Git repository access rules."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'describe_git_permissions',
    'IGitNascentRule',
    'IGitNascentRuleGrant',
    'IGitRule',
    'IGitRuleGrant',
    ]

from lazr.restful.fields import Reference
from lazr.restful.interface import copy_field
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Bool,
    Choice,
    Datetime,
    FrozenSet,
    Int,
    List,
    TextLine,
    )

from lp import _
from lp.code.enums import (
    GitGranteeType,
    GitPermissionType,
    )
from lp.code.interfaces.gitrepository import IGitRepository
from lp.services.fields import (
    InlineObject,
    PersonChoice,
    PublicPersonChoice,
    )


class IGitRuleView(Interface):
    """`IGitRule` attributes that require launchpad.View."""

    id = Int(title=_("ID"), readonly=True, required=True)

    repository = Reference(
        title=_("Repository"), required=True, readonly=True,
        schema=IGitRepository,
        description=_("The repository that this rule is for."))

    position = Int(
        title=_("Position"), required=True, readonly=True,
        description=_(
            "The position of this rule in its repository's rule order."))

    creator = PublicPersonChoice(
        title=_("Creator"), required=True, readonly=True,
        vocabulary="ValidPerson",
        description=_("The user who created this rule."))

    date_created = Datetime(
        title=_("Date created"), required=True, readonly=True,
        description=_("The time when this rule was created."))

    date_last_modified = Datetime(
        title=_("Date last modified"), required=True, readonly=True,
        description=_("The time when this rule was last modified."))

    is_exact = Bool(
        title=_("Is this an exact-match rule?"), required=True, readonly=True,
        description=_(
            "True if this rule is for an exact reference name, or False if "
            "it is for a wildcard."))

    grants = Attribute("The access grants for this rule.")


class IGitRuleEditableAttributes(Interface):
    """`IGitRule` attributes that can be edited.

    These attributes need launchpad.View to see, and launchpad.Edit to change.
    """

    ref_pattern = TextLine(
        title=_("Pattern"), required=True, readonly=False,
        description=_("The pattern of references matched by this rule."))


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

    def setGrants(grants, user):
        """Set the access grants for this rule.

        :param grants: A sequence of `IGitNascentRuleGrant`.
        :param user: The `IPerson` who is granting permission.
        """

    def destroySelf(user):
        """Delete this rule.

        :param user: The `IPerson` doing the deletion.
        """


class IGitRule(IGitRuleView, IGitRuleEditableAttributes, IGitRuleEdit):
    """An access rule for a Git repository."""


class IGitRuleGrantView(Interface):
    """`IGitRuleGrant` attributes that require launchpad.View."""

    id = Int(title=_("ID"), readonly=True, required=True)

    repository = Reference(
        title=_("Repository"), required=True, readonly=True,
        schema=IGitRepository,
        description=_("The repository that this grant is for."))

    rule = Reference(
        title=_("Rule"), required=True, readonly=True,
        schema=IGitRule,
        description=_("The rule that this grant is for."))

    grantor = PublicPersonChoice(
        title=_("Grantor"), required=True, readonly=True,
        vocabulary="ValidPerson",
        description=_("The user who created this grant."))

    grantee_type = Choice(
        title=_("Grantee type"), required=True, readonly=True,
        vocabulary=GitGranteeType,
        description=_("The type of grantee for this grant."))

    grantee = PersonChoice(
        title=_("Grantee"), required=False, readonly=True,
        vocabulary="ValidPersonOrTeam",
        description=_("The person being granted access."))

    combined_grantee = Attribute(
        "The overall grantee of this grant: either a `GitGranteeType` (other "
        "than `PERSON`) or an `IPerson`.")

    date_created = Datetime(
        title=_("Date created"), required=True, readonly=True,
        description=_("The time when this grant was created."))

    date_last_modified = Datetime(
        title=_("Date last modified"), required=True, readonly=True,
        description=_("The time when this grant was last modified."))


class IGitRuleGrantEditableAttributes(Interface):
    """`IGitRuleGrant` attributes that can be edited.

    These attributes need launchpad.View to see, and launchpad.Edit to change.
    """

    can_create = Bool(
        title=_("Can create"), required=True, readonly=False,
        description=_("Whether creating references is allowed."))

    can_push = Bool(
        title=_("Can push"), required=True, readonly=False,
        description=_("Whether pushing references is allowed."))

    can_force_push = Bool(
        title=_("Can force-push"), required=True, readonly=False,
        description=_("Whether force-pushing references is allowed."))

    permissions = FrozenSet(
        title=_("Permissions"), required=True, readonly=False,
        value_type=Choice(vocabulary=GitPermissionType),
        description=_("The permissions granted by this grant."))


class IGitRuleGrantEdit(Interface):
    """`IGitRuleGrant` attributes that require launchpad.Edit."""

    def destroySelf(user=None):
        """Delete this access grant.

        :param user: The `IPerson` doing the deletion, or None if the
            deletion should not be logged.
        """


class IGitRuleGrant(IGitRuleGrantView, IGitRuleGrantEditableAttributes,
                    IGitRuleGrantEdit):
    """An access grant for a Git repository rule."""


class IGitNascentRuleGrant(Interface):
    """An access grant in the process of being created.

    This represents parameters for a grant that have been deserialised from
    a webservice request, but that have not yet been attached to a rule.
    """

    grantee_type = copy_field(IGitRuleGrant["grantee_type"])

    grantee = copy_field(IGitRuleGrant["grantee"])

    can_create = copy_field(
        IGitRuleGrant["can_create"], required=False, default=False)

    can_push = copy_field(
        IGitRuleGrant["can_push"], required=False, default=False)

    can_force_push = copy_field(
        IGitRuleGrant["can_force_push"], required=False, default=False)


class IGitNascentRule(Interface):
    """An access rule in the process of being created.

    This represents parameters for a rule that have been deserialised from a
    webservice request, but that have not yet been attached to a repository.
    """

    ref_pattern = copy_field(IGitRule["ref_pattern"])

    grants = List(value_type=InlineObject(schema=IGitNascentRuleGrant))


def describe_git_permissions(permissions, verbose=False):
    """Return human-readable descriptions of a set of Git access permissions.

    :param permissions: A collection of `GitPermissionType`.
    :return: A list of human-readable descriptions of the input permissions,
        in a conventional order.
    """
    names = []
    if GitPermissionType.CAN_CREATE in permissions:
        names.append("create")
    if GitPermissionType.CAN_PUSH in permissions:
        names.append("push")
    if GitPermissionType.CAN_FORCE_PUSH in permissions:
        names.append("force-push")
    return names
