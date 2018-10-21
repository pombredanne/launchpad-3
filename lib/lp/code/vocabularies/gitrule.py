# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Vocabularies related to Git access rules."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'GitPermissionsVocabulary',
    ]

from zope.schema.vocabulary import (
    SimpleTerm,
    SimpleVocabulary,
    )

from lp import _
from lp.code.enums import GitPermissionType
from lp.code.interfaces.gitref import IGitRef
from lp.code.interfaces.gitrule import (
    IGitRule,
    IGitRuleGrant,
    )


branch_permissions = [
    SimpleTerm(
        frozenset(),
        "cannot_push", _("Cannot push")),
    SimpleTerm(
        frozenset({
            GitPermissionType.CAN_PUSH,
            }),
        "can_push_existing", _("Can push if the branch already exists")),
    SimpleTerm(
        frozenset({
            GitPermissionType.CAN_CREATE,
            GitPermissionType.CAN_PUSH,
            }),
        "can_push", _("Can push")),
    SimpleTerm(
        frozenset({
            GitPermissionType.CAN_CREATE,
            GitPermissionType.CAN_PUSH,
            GitPermissionType.CAN_FORCE_PUSH,
            }),
        "can_force_push", _("Can force-push")),
    ]


tag_permissions = [
    SimpleTerm(
        frozenset(),
        "cannot_create", _("Cannot create")),
    SimpleTerm(
        frozenset({
            GitPermissionType.CAN_CREATE,
            }),
        "can_create", _("Can create")),
    SimpleTerm(
        frozenset({
            GitPermissionType.CAN_CREATE,
            GitPermissionType.CAN_PUSH,
            GitPermissionType.CAN_FORCE_PUSH,
            }),
        "can_move", _("Can move")),
    ]


class GitPermissionsVocabulary(SimpleVocabulary):
    """A vocabulary for typical combinations of Git access permissions.

    The terms of this vocabulary are combinations of permissions that make
    sense in the UI without being too overwhelming, depending on the rule's
    reference pattern (different combinations make sense for branches vs.
    tags).
    """

    def __init__(self, context):
        if IGitRef.providedBy(context):
            path = context.path
        elif IGitRule.providedBy(context):
            path = context.ref_pattern
        elif IGitRuleGrant.providedBy(context):
            path = context.rule.ref_pattern
        else:
            raise AssertionError("GitPermissionsVocabulary needs a context.")
        if path.startswith("refs/tags/"):
            terms = list(tag_permissions)
        else:
            # We could restrict this to just refs/heads/*, but it's helpful
            # to be able to offer *some* choices in the UI if somebody tries
            # to create grants for e.g. refs/*, and the choices we offer for
            # branches are probably more useful there than those we offer
            # for tags.
            terms = list(branch_permissions)
        if IGitRuleGrant.providedBy(context):
            grant_permissions = context.permissions
            if grant_permissions not in (term.value for term in terms):
                # Supplement the vocabulary with any atypical permissions
                # used by this grant.
                names = []
                if GitPermissionType.CAN_CREATE in grant_permissions:
                    names.append("create")
                if GitPermissionType.CAN_PUSH in grant_permissions:
                    names.append("push")
                if GitPermissionType.CAN_FORCE_PUSH in grant_permissions:
                    names.append("force-push")
                terms.append(SimpleTerm(
                    grant_permissions,
                    "custom", "Custom permissions: %s" % ", ".join(names)))
        super(GitPermissionsVocabulary, self).__init__(terms)
