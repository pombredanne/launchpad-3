# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Returns rules defining which features are active"""

__all__ = [
    'FeatureRuleSource',
    'NullFeatureRuleSource',
    'StormFeatureRuleSource',
    ]

__metaclass__ = type

from storm.locals import Desc

from lp.services.features.model import (
    FeatureFlag,
    getFeatureStore,
    )


class FeatureRuleSource(object):
    """Access feature rule sources from the database or elsewhere."""

    def getAllRulesAsText(self):
        tr = []
        for flag, rules in sorted(self.getAllRules().items()):
            for (scope, priority, value) in rules:
                tr.append('\t'.join((flag, scope, str(priority), value)))
        tr.append('')
        return '\n'.join(tr)


class StormFeatureRuleSource(FeatureRuleSource):
    """Access feature rules stored in the database via Storm.
    """

    def getAllRules(self):
        """Return all rule definitions.

        :returns: dict from flag name to an ordered list of 
            (scope, priority, value) 
            tuples, where the first matching scope should be used.
        """
        store = getFeatureStore()
        d = {}
        rs = (store
                .find(FeatureFlag)
                .order_by(Desc(FeatureFlag.priority)))
        for r in rs:
            d.setdefault(str(r.flag), []).append((str(r.scope), r.priority, r.value))
        return d


class NullFeatureRuleSource(FeatureRuleSource):
    """For use in testing: everything is turned off"""

    def getAllRules(self):
        return {}
