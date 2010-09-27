# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Feature control view"""


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

    feature_rules = Text(title=u"Feature rules")


class FeatureControlView(LaunchpadFormView):

    schema = IFeatureControlForm
    page_title = label = 'Feature control'

    @action(u"Change", name="change")
    def change_action(self, action, data):
        rules_text = self.request.get('feature_rules')
        logger = logging.getLogger('lp.services.features')
        logger.warning("Change feature rules to: %s" % (rules_text,))
        return self.request.features.rule_source.setAllRulesFromText(
            rules_text)

    def rules_text(self):
        """Return all rules in an editable text form"""
        return self.request.features.rule_source.getAllRulesAsText()
