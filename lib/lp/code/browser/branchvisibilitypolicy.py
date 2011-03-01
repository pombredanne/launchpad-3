# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The view classes for handling branch visibility policies."""

__metaclass__ = type

__all__ = [
    'AddBranchVisibilityTeamPolicyView',
    'RemoveBranchVisibilityTeamPolicyView',
    'BranchVisibilityPolicyMixin',
    'BranchVisibilityPolicyView',
    ]

from zope.app.form import CustomWidgetFactory
from zope.formlib import form
from zope.schema import (
    Choice,
    List,
    )
from zope.schema.vocabulary import (
    SimpleTerm,
    SimpleVocabulary,
    )

from canonical.launchpad import _
from canonical.launchpad.webapp import (
    canonical_url,
    LaunchpadView,
    )
from lp.app.browser.launchpadform import (
    action,
    custom_widget,
    LaunchpadFormView,
    )
from lp.app.widgets.itemswidgets import (
    LabeledMultiCheckBoxWidget,
    LaunchpadRadioWidgetWithDescription,
    )
from lp.code.enums import (
    BranchVisibilityRule,
    TeamBranchVisibilityRule,
    )
from lp.code.interfaces.branchvisibilitypolicy import (
    IBranchVisibilityTeamPolicy,
    )
from lp.services.propertycache import cachedproperty


class BaseBranchVisibilityTeamPolicyView(LaunchpadFormView):
    """Used as a base class for the add and remove view."""

    schema = IBranchVisibilityTeamPolicy

    @property
    def adapters(self):
        return {IBranchVisibilityTeamPolicy: self.context}

    @property
    def next_url(self):
        return canonical_url(self.context, view_name='+branchvisibility')

    cancel_url = next_url


class AddBranchVisibilityTeamPolicyView(BaseBranchVisibilityTeamPolicyView):
    """Simple form view to add branch visibility policy items."""

    page_title = label = "Set branch visibility policy for team"

    initial_values = {'rule': TeamBranchVisibilityRule.PRIVATE}
    custom_widget('rule', LaunchpadRadioWidgetWithDescription)

    def showSetDefaultPublic(self, action=None):
        """Show if using inherited policy, or currently forbidden."""
        base_rule = self.context.getBaseBranchVisibilityRule()
        return (self.context.isUsingInheritedBranchVisibilityPolicy() or
                base_rule == BranchVisibilityRule.FORBIDDEN)

    def showSetDefaultForbidden(self, action=None):
        """Show if using inherited policy, or currently forbidden."""
        base_rule = self.context.getBaseBranchVisibilityRule()
        return (self.context.isUsingInheritedBranchVisibilityPolicy() or
                base_rule != BranchVisibilityRule.FORBIDDEN)

    @action(_('Set Default Public'), name='set_default_public',
            condition=showSetDefaultPublic,
            validator=LaunchpadFormView.validate_none)
    def set_default_public_action(self, action, data):
        """Make the default policy public."""
        self.context.setBranchVisibilityTeamPolicy(
            None, BranchVisibilityRule.PUBLIC)

    @action(_('Set Default Forbidden'), name='set_default_forbidden',
            condition=showSetDefaultForbidden,
            validator=LaunchpadFormView.validate_none)
    def set_default_forbidden_action(self, action, data):
        """Make the default policy forbidden."""
        self.context.setBranchVisibilityTeamPolicy(
            None, BranchVisibilityRule.FORBIDDEN)

    @action(_('Set Team Policy'), name='set_team_policy')
    def set_team_policy_action(self, action, data):
        "Set the branch visibility rule for the team."
        team = data['team']
        rule = BranchVisibilityRule.items[data['rule'].name]
        self.context.setBranchVisibilityTeamPolicy(team, rule)


class RemoveBranchVisibilityTeamPolicyView(BaseBranchVisibilityTeamPolicyView):
    """The view to remove zero or more branch visibility policy items."""

    page_title = label = "Remove branch visibility policy for teams"

    def _policyDescription(self, item):
        """The text visible to the user displayed by the widget."""
        if item.team is None:
            teamname = "Everyone"
        else:
            teamname = item.team.displayname

        return "%s: %s" % (teamname, item.rule.title)

    def _policyToken(self, item):
        """The text used as the value of the widget."""
        if item.team is None:
            return '+everyone'
        else:
            return item.team.name

    def _currentPolicyItemsField(self):
        """Create the policy items field.

        The vocabulary is created from the policy items.  This is then shown
        using the multi checkbox widget.
        """
        terms = [SimpleTerm(item, self._policyToken(item),
                            self._policyDescription(item))
                 for item in self.context.getBranchVisibilityTeamPolicies()]

        return form.Fields(
            List(
                __name__='policy_items',
                title=_("Policy Items"),
                value_type=Choice(vocabulary=SimpleVocabulary(terms)),
                required=True),
            render_context=self.render_context,
            custom_widget=CustomWidgetFactory(LabeledMultiCheckBoxWidget))

    def setUpFields(self):
        """Override the setup to define own fields."""
        self.form_fields = self._currentPolicyItemsField()

    @action(_('Remove Selected Policy Items'), name='remove')
    def remove_action(self, action, data):
        """Remove selected policy items."""
        for item in data['policy_items']:
            self.context.removeTeamFromBranchVisibilityPolicy(item.team)


class BranchVisibilityPolicyMixin:
    """Mixin class providing visibility rules."""
    @property
    def base_visibility_rule(self):
        return self.context.getBaseBranchVisibilityRule()

    @property
    def team_policies(self):
        """The policy items that have a valid team."""
        return [item for item in self.items if item.team is not None]

    @cachedproperty
    def items(self):
        return self.context.getBranchVisibilityTeamPolicies()


class BranchVisibilityPolicyView(LaunchpadView,
                                 BranchVisibilityPolicyMixin):
    """Simple view for displaying branch visibility policies."""

    @property
    def page_title(self):
        name = self.context.displayname
        return 'Set branch visibility policy for %s' % name

    @property
    def can_remove_items(self):
        """You cannot remove items if using inherited policy or
        if there is only the default policy item.
        """
        return (len(self.items) > 0 and
                not self.context.isUsingInheritedBranchVisibilityPolicy())
