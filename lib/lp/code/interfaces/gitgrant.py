# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Git repository access grants."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'IGitGrant',
    ]

from lazr.restful.fields import Reference
from zope.interface import Interface
from zope.schema import (
    Bool,
    Choice,
    Datetime,
    Int,
    )

from lp import _
from lp.code.enums import GitGranteeType
from lp.code.interfaces.gitrepository import IGitRepository
from lp.code.interfaces.gitrule import IGitRule
from lp.services.fields import (
    PersonChoice,
    PublicPersonChoice,
    )


class IGitGrantView(Interface):
    """`IGitGrant` attributes that require launchpad.View."""

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

    date_created = Datetime(
        title=_("Date created"), required=True, readonly=True,
        description=_("The time when this grant was created."))


class IGitGrantEditableAttributes(Interface):
    """`IGitGrant` attributes that can be edited.

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

    date_last_modified = Datetime(
        title=_("Date last modified"), required=True, readonly=True,
        description=_("The time when this grant was last modified."))


class IGitGrantEdit(Interface):
    """`IGitGrant` attributes that require launchpad.Edit."""

    def destroySelf():
        """Delete this access grant."""


class IGitGrant(IGitGrantView, IGitGrantEditableAttributes, IGitGrantEdit):
    """An access grant for a Git repository rule."""
