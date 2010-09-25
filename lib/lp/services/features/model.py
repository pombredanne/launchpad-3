# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = [
    'addFeatureFlagRules',
    'FeatureFlag',
    'getFeatureStore',
    ]

__metaclass__ = type

from storm.locals import (
    DateTime,
    Desc,
    Int,
    Storm,
    Unicode,
    )
from zope.component import getUtility

from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )


def getFeatureStore():
    """Get Storm store to access feature definitions."""
    # TODO: This is copied so many times in Launchpad; maybe it should be more
    # general?
    return getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)


class FeatureFlag(Storm):
    """Database setting of a particular flag in a scope"""

    __storm_table__ = 'FeatureFlag'
    __storm_primary__ = "scope", "flag"

    scope = Unicode(allow_none=False)
    flag = Unicode(allow_none=False)
    priority = Int(allow_none=False)
    value = Unicode(allow_none=False)
    date_modified = DateTime()

    def __init__(self, scope, priority, flag, value):
        super(FeatureFlag, self).__init__()
        self.scope = scope
        self.priority = priority
        self.flag = flag
        self.value = value


def addFeatureFlagRules(rule_list):
    """Add rules in to the database; intended for use in testing.

    :param rule_list: [(scope, flag, value, priority)...]
    """
    store = getFeatureStore()
    for (scope, flag, value, priority) in rule_list:
        store.add(FeatureFlag(
            scope=unicode(scope),
            flag=unicode(flag),
            value=value,
            priority=priority))
