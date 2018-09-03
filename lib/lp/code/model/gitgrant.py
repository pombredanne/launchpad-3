# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Git repository access grants."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'GitGrant',
    ]

from lazr.enum import DBItem
import pytz
from storm.locals import (
    Bool,
    DateTime,
    Int,
    Reference,
    Store,
    )
from zope.interface import implementer

from lp.code.enums import GitGranteeType
from lp.code.interfaces.gitgrant import IGitGrant
from lp.services.database.constants import UTC_NOW
from lp.services.database.enumcol import EnumCol
from lp.services.database.stormbase import StormBase


def git_grant_modified(grant, event):
    """Update date_last_modified when a GitGrant is modified.

    This method is registered as a subscriber to `IObjectModifiedEvent`
    events on Git repository grants.
    """
    if event.edited_fields:
        grant.date_last_modified = UTC_NOW


@implementer(IGitGrant)
class GitGrant(StormBase):
    """See `IGitGrant`."""

    __storm_table__ = 'GitGrant'

    id = Int(primary=True)

    repository_id = Int(name='repository', allow_none=False)
    repository = Reference(repository_id, 'GitRepository.id')

    rule_id = Int(name='rule', allow_none=False)
    rule = Reference(rule_id, 'GitRule.id')

    grantee_type = EnumCol(
        dbName='grantee_type', enum=GitGranteeType, notNull=True)

    grantee_id = Int(name='grantee', allow_none=True)
    grantee = Reference(grantee_id, 'Person.id')

    can_create = Bool(name='can_create', allow_none=False)
    can_push = Bool(name='can_push', allow_none=False)
    can_force_push = Bool(name='can_force_push', allow_none=False)

    grantor_id = Int(name='grantor', allow_none=False)
    grantor = Reference(grantor_id, 'Person.id')

    date_created = DateTime(
        name='date_created', tzinfo=pytz.UTC, allow_none=False)
    date_last_modified = DateTime(
        name='date_last_modified', tzinfo=pytz.UTC, allow_none=False)

    def __init__(self, rule, grantee, can_create, can_push, can_force_push,
                 grantor, date_created):
        if isinstance(grantee, DBItem) and grantee.enum == GitGranteeType:
            if grantee == GitGranteeType.PERSON:
                raise ValueError(
                    "grantee may not be GitGranteeType.PERSON; pass a person "
                    "object instead")
            grantee_type = grantee
            grantee = None
        else:
            grantee_type = GitGranteeType.PERSON

        self.repository = rule.repository
        self.rule = rule
        self.grantee_type = grantee_type
        self.grantee = grantee
        self.can_create = can_create
        self.can_push = can_push or can_force_push
        self.can_force_push = can_force_push
        self.grantor = grantor
        self.date_created = date_created
        self.date_last_modified = date_created

    def __repr__(self):
        permissions = []
        if self.can_create:
            permissions.append("create")
        if self.can_push:
            permissions.append("push")
        if self.can_force_push:
            permissions.append("force-push")
        if self.grantee_type == GitGranteeType.PERSON:
            grantee_name = "~%s" % self.grantee.name
        else:
            grantee_name = self.grantee_type.title.lower()
        return "<GitGrant [%s] to %s> for %r" % (
            ", ".join(permissions), grantee_name, self.rule)

    def destroySelf(self):
        """See `IGitGrant`."""
        Store.of(self).remove(self)
