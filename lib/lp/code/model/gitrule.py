# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Git repository access rules."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'GitRule',
    ]

import pytz
from storm.locals import (
    DateTime,
    Int,
    Reference,
    Store,
    Unicode,
    )
from zope.interface import implementer

from lp.code.interfaces.gitrule import IGitRule
from lp.code.model.gitrulegrant import GitRuleGrant
from lp.registry.interfaces.person import validate_public_person
from lp.services.database.constants import (
    DEFAULT,
    UTC_NOW,
    )
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

    ref_pattern = Unicode(name='ref_pattern', allow_none=False)

    creator_id = Int(
        name='creator', allow_none=False, validator=validate_public_person)
    creator = Reference(creator_id, 'Person.id')

    date_created = DateTime(
        name='date_created', tzinfo=pytz.UTC, allow_none=False)
    date_last_modified = DateTime(
        name='date_last_modified', tzinfo=pytz.UTC, allow_none=False)

    def __init__(self, repository, ref_pattern, creator, date_created):
        super(GitRule, self).__init__()
        self.repository = repository
        self.ref_pattern = ref_pattern
        self.creator = creator
        self.date_created = date_created
        self.date_last_modified = date_created

    def __repr__(self):
        return "<GitRule '%s'> for %r" % (self.ref_pattern, self.repository)

    @property
    def position(self):
        """See `IGitRule`."""
        rule_order = self.repository.rule_order
        if not rule_order:
            raise AssertionError("%r has no access rules" % self.repository)
        try:
            return rule_order.index(self.id)
        except ValueError:
            raise AssertionError(
                "%r is not in rule_order for %r" % (self, self.repository))

    def move(self, position):
        """See `IGitRule`."""
        if position < 0:
            raise ValueError("Negative positions are not supported")
        current_position = self.position
        if position != current_position:
            del self.repository.rule_order[current_position]
            self.repository.rule_order.insert(position, self.id)

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
        self.repository.rule_order.remove(self.id)
        Store.of(self).remove(self)
