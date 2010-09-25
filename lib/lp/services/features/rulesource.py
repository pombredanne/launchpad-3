# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Returns rules defining which features are active"""

__all__ = [
    'FeatureRuleSource',
    'NullFeatureRuleSource',
    'StormFeatureRuleSource',
    ]

__metaclass__ = type

import re

from storm.locals import Desc

from lp.services.features.model import (
    FeatureFlag,
    getFeatureStore,
    )


class FeatureRuleSource(object):
    """Access feature rule sources from the database or elsewhere."""

    def getAllRulesAsDict(self):
        """Return all rule definitions.

        :returns: dict from flag name to an ordered list of 
            (scope, priority, value) 
            tuples, where the first matching scope should be used.
        """
        d = {}
        for (flag, scope, priority, value) in self.getAllRulesAsTuples():
            d.setdefault(str(flag), []).append((str(scope), priority, value))
        return d

    def getAllRulesAsText(self):
        tr = []
        for (flag, scope, priority, value) in self.getAllRulesAsTuples():
            tr.append('\t'.join((flag, scope, str(priority), value)))
        tr.append('')
        return '\n'.join(tr)

    def setAllRulesFromText(self, text_form):
        self.setAllRules(self.parseRules(text_form))

    def parseRules(self, text_form):
        for line in text_form.splitlines():
            if line.strip() == '':
                continue
            flag, scope, priority_str, value = re.split('[ \t]+', line, 3)
            yield (flag, scope, int(priority_str), unicode(value))


class StormFeatureRuleSource(FeatureRuleSource):
    """Access feature rules stored in the database via Storm.
    """

    def getAllRulesAsTuples(self):
        store = getFeatureStore()
        rs = (store
                .find(FeatureFlag)
                .order_by(FeatureFlag.flag, Desc(FeatureFlag.priority)))
        for r in rs:
            yield str(r.flag), str(r.scope), r.priority, r.value

    def setAllRules(self, new_rules):
        """Replace all existing rules with a new set.

        :param new_rules: List of (name, scope, priority, value) tuples.
        """
        # XXX: would be slightly better to only update rules as necessary so we keep
        # timestamps, and to avoid the direct sql etc -- mbp 20100924
        store = getFeatureStore()
        store.execute('delete from featureflag')
        for (flag, scope, priority, value) in new_rules:
            store.add(FeatureFlag(
                scope=unicode(scope),
                flag=unicode(flag),
                value=value,
                priority=priority))


class NullFeatureRuleSource(FeatureRuleSource):
    """For use in testing: everything is turned off"""

    def getAllRulesAsTuples(self):
        return []
