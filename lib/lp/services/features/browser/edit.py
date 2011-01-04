# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View and edit feature rules."""

__metaclass__ = type
__all__ = [
    'FeatureControlView',
    'IFeatureControlForm',
    ]


from difflib import unified_diff
import logging

from zope.interface import Interface
from zope.schema import Text
from zope.security.interfaces import Unauthorized

from canonical.launchpad.webapp.authorization import check_permission
from lp.app.browser.launchpadform import (
    action,
    LaunchpadFormView,
    )
from lp.app.browser.stringformatter import FormattersAPI


class IFeatureControlForm(Interface):
    """Interface specifically for editing a text form of feature rules"""

    def __init__(self, context):
        self.context = context

    feature_rules = Text(
        title=u"Feature rules",
        description=(
            u"Rules to control feature flags on Launchpad.  "
            u"On each line: (flag, scope, priority, value), "
            u"whitespace-separated.  Numerically higher "
            u"priorities match first."),
        required=False)


class FeatureControlView(LaunchpadFormView):
    """Text view of feature rules.

    Presents a text area, either read-only or read-write, showing currently
    active rules.
    """

    schema = IFeatureControlForm
    page_title = label = 'Feature control'
    field_names = ['feature_rules']
    diff = None

    @action(u"Change", name="change")
    def change_action(self, action, data):
        if not check_permission('launchpad.Admin', self.context):
            raise Unauthorized()
        original_rules = self.request.features.rule_source.getAllRulesAsText()
        new_rules = data.get('feature_rules') or ''
        logger = logging.getLogger('lp.services.features')
        logger.warning("Change feature rules to: %s" % (new_rules,))
        self.request.features.rule_source.setAllRulesFromText(new_rules)
        diff = '\n'.join(self.diff_rules(original_rules, new_rules))
        self.diff = FormattersAPI(diff).format_diff()

    @staticmethod
    def diff_rules(rules1, rules2):
        # Just generate a one-block diff.
        lines_of_context = 999999
        diff = unified_diff(
            rules1.splitlines(),
            rules2.splitlines(),
            n=lines_of_context)
        # The three line header is meaningless here.
        return list(diff)[3:]

    @property
    def initial_values(self):
        return {
            'feature_rules':
                self.request.features.rule_source.getAllRulesAsText(),
        }

    def validate(self, data):
        # Try parsing the rules so we give a clean error: at the moment the
        # message is not great, but it's better than an oops.
        try:
            # Unfortunately if the field is '', zope leaves it out of data.
            self.request.features.rule_source.parseRules(
                data.get('feature_rules') or '')
        except (IndexError, TypeError, ValueError), e:
            self.setFieldError('feature_rules', 'Invalid rule syntax: %s' % e)
