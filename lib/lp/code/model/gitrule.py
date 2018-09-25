# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Git repository access rules."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'GitRule',
    'GitRuleGrant',
    ]

from lazr.enum import DBItem
import pytz
from storm.locals import (
    Bool,
    DateTime,
    Int,
    Reference,
    Store,
    Unicode,
    )
from zope.interface import implementer
from zope.security.proxy import removeSecurityProxy

from lp.code.enums import GitGranteeType
from lp.code.interfaces.gitrule import (
    IGitRule,
    IGitRuleGrant,
    )
from lp.registry.interfaces.person import (
    validate_person,
    validate_public_person,
    )
from lp.services.database.constants import (
    DEFAULT,
    UTC_NOW,
    )
from lp.services.database.enumcol import DBEnum
from lp.services.database.stormbase import StormBase


def git_rule_modified(rule, event):
    """Update date_last_modified when a GitRule is modified.

    This method is registered as a subscriber to `IObjectModifiedEvent`
    events on Git repository rules.
    """
    if event.edited_fields:
        rule.date_last_modified = UTC_NOW


@implementer(IGitRule)
class GitRule(StormBase):
    """See `IGitRule`."""

    __storm_table__ = 'GitRule'

    id = Int(primary=True)

    repository_id = Int(name='repository', allow_none=False)
    repository = Reference(repository_id, 'GitRepository.id')

    position = Int(name='position', allow_none=False)

    ref_pattern = Unicode(name='ref_pattern', allow_none=False)

    creator_id = Int(
        name='creator', allow_none=False, validator=validate_public_person)
    creator = Reference(creator_id, 'Person.id')

    date_created = DateTime(
        name='date_created', tzinfo=pytz.UTC, allow_none=False)
    date_last_modified = DateTime(
        name='date_last_modified', tzinfo=pytz.UTC, allow_none=False)

    def __init__(self, repository, position, ref_pattern, creator,
                 date_created):
        super(GitRule, self).__init__()
        self.repository = repository
        self.position = position
        self.ref_pattern = ref_pattern
        self.creator = creator
        self.date_created = date_created
        self.date_last_modified = date_created

    def __repr__(self):
        return "<GitRule '%s'> for %r" % (self.ref_pattern, self.repository)

    @property
    def is_exact(self):
        """See `IGitRule`."""
        # turnip's glob_to_re only treats * as special, so any rule whose
        # pattern does not contain * must be an exact-match rule.
        return "*" not in self.ref_pattern

    @property
    def grants(self):
        """See `IGitRule`."""
        return Store.of(self).find(
            GitRuleGrant, GitRuleGrant.rule_id == self.id)

    def addGrant(self, grantee, grantor, can_create=False, can_push=False,
                 can_force_push=False):
        """See `IGitRule`."""
        return GitRuleGrant(
            rule=self, grantee=grantee, can_create=can_create,
            can_push=can_push, can_force_push=can_force_push, grantor=grantor,
            date_created=DEFAULT)

    def destroySelf(self):
        """See `IGitRule`."""
        for grant in self.grants:
            grant.destroySelf()
        rules = list(self.repository.rules)
        Store.of(self).remove(self)
        rules.remove(self)
        removeSecurityProxy(self.repository)._syncRulePositions(rules)


def git_rule_grant_modified(grant, event):
    """Update date_last_modified when a GitRuleGrant is modified.

    This method is registered as a subscriber to `IObjectModifiedEvent`
    events on Git repository grants.
    """
    if event.edited_fields:
        grant.date_last_modified = UTC_NOW


@implementer(IGitRuleGrant)
class GitRuleGrant(StormBase):
    """See `IGitRuleGrant`."""

    __storm_table__ = 'GitRuleGrant'

    id = Int(primary=True)

    repository_id = Int(name='repository', allow_none=False)
    repository = Reference(repository_id, 'GitRepository.id')

    rule_id = Int(name='rule', allow_none=False)
    rule = Reference(rule_id, 'GitRule.id')

    grantee_type = DBEnum(
        name='grantee_type', enum=GitGranteeType, allow_none=False)

    grantee_id = Int(
        name='grantee', allow_none=True, validator=validate_person)
    grantee = Reference(grantee_id, 'Person.id')

    can_create = Bool(name='can_create', allow_none=False)
    can_push = Bool(name='can_push', allow_none=False)
    can_force_push = Bool(name='can_force_push', allow_none=False)

    grantor_id = Int(
        name='grantor', allow_none=False, validator=validate_public_person)
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
        self.can_push = can_push
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
        return "<GitRuleGrant [%s] to %s> for %r" % (
            ", ".join(permissions), grantee_name, self.rule)

    def destroySelf(self):
        """See `IGitRuleGrant`."""
        Store.of(self).remove(self)
