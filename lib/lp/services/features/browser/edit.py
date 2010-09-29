# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View and edit feature rules."""

__metaclass__ = type
__all__ = [
    'FeatureControlView',
    'IFeatureControlForm'
    ]


import logging 


from zope.interface import Interface
from zope.schema import (
    Text,
    )

from canonical.launchpad.webapp import (
    action,
    LaunchpadFormView,
    )


class IFeatureControlForm(Interface):
    """Interface specifically for editing a text form of feature rules"""

    def __init__(self, context):
        self.context = context

    feature_rules = Text(
        title=u"Feature rules",
        description=(
            u"Rules to control feature flags on Launchpad."
            u"On each line: (flag, scope, priority, value), "
            u"whitespace-separated.  Numerically higher "
            u"priorities match first."
        ))


class FeatureControlView(LaunchpadFormView):
    """Text view of feature rules.

    Presents a text area, either read-only or read-write, showing currently
    active rules.
    """

    schema = IFeatureControlForm
    page_title = label = 'Feature control'
    field_names = ['feature_rules']

    @action(u"Change", name="change")
    def change_action(self, action, data):
        rules_text = data['feature_rules']
        logger = logging.getLogger('lp.services.features')
        logger.warning("Change feature rules to: %s" % (rules_text,))
        return self.request.features.rule_source.setAllRulesFromText(
            rules_text)

    @property
    def feature_rules(self):
        """Default value for rules is what's currently defined."""
        return self.request.features.rule_source.getAllRulesAsText()

    def validate(self, data):
        # Try parsing the rules so we give a clean error: at the moment the
        # message is not great, but it's better than an oops.
        try:
            self.request.features.rule_source.parseRules(
                data['feature_rules'])
        except (IndexError, TypeError, ValueError), e:
            self.setFieldError('feature_rules', 'Invalid rule syntax: %s' % e)
