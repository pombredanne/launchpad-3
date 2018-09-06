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
from zope.component import getUtility
from zope.interface import implementer
from zope.security.proxy import removeSecurityProxy

from lp.code.interfaces.gitactivity import IGitActivitySet
from lp.code.interfaces.gitrule import IGitRule
from lp.code.model.gitgrant import GitGrant
from lp.registry.interfaces.person import (
    IPerson,
    validate_public_person,
    )
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
        user = IPerson(event.user)
        getUtility(IGitActivitySet).logRuleChanged(
            event.object_before_modification, rule, user)
        removeSecurityProxy(rule).date_last_modified = UTC_NOW


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
    def grants(self):
        """See `IGitRule`."""
        return Store.of(self).find(GitGrant, GitGrant.rule_id == self.id)

    def addGrant(self, grantee, grantor, can_create=False, can_push=False,
                 can_force_push=False):
        """See `IGitRule`."""
        grant = GitGrant(
            rule=self, grantee=grantee, can_create=can_create,
            can_push=can_push, can_force_push=can_force_push, grantor=grantor,
            date_created=DEFAULT)
        getUtility(IGitActivitySet).logGrantAdded(grant, grantor)
        return grant

    def destroySelf(self, user):
        """See `IGitRule`."""
        getUtility(IGitActivitySet).logRuleRemoved(self, user)
        self.repository.rule_order.remove(self.id)
        Store.of(self).remove(self)
