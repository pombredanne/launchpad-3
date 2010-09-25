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

    pass


class StormFeatureRuleSource(FeatureRuleSource):
    """Access feature rules stored in the database via Storm.
    """

    def getAllRules(self):
        """Return all rule definitions.

        :returns: dict from flag name to an ordered list of (scope, value) 
            tuples, where the first matching scope should be used.
        """
        store = getFeatureStore()
        d = {}
        rs = (store
                .find(FeatureFlag)
                .order_by(Desc(FeatureFlag.priority))
                .values(FeatureFlag.flag, FeatureFlag.scope,
                    FeatureFlag.value))
        for flag, scope, value in rs:
            d.setdefault(str(flag), []).append((str(scope), value))
        return d

    def setRulesFromText(self, text_rules):
        """Set rules from user-editable text form."""
        raise NotImplementedError()


class NullFeatureRuleSource(FeatureRuleSource):
    """For use in testing: everything is turned off"""

    def getAllRules(self):
        return {}
