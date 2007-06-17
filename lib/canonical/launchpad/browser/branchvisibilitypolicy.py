# Copyright 2007 Canonical Ltd.  All rights reserved.

"""The view classes for handling branch visibility policies."""

__metaclass__ = type

__all__ = [
    'AddBranchVisibilityPolicyItemView',
    'RemoveBranchVisibilityPolicyItemView',
    'BranchVisibilityPolicyView',
    ]

from zope.app.form import CustomWidgetFactory
from zope.formlib import form
from zope.schema import Choice, List
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from canonical.cachedproperty import cachedproperty

from canonical.launchpad import _
from canonical.launchpad.interfaces import IBranchVisibilityPolicyItem
from canonical.launchpad.webapp import (
    action, canonical_url, LaunchpadFormView, LaunchpadView)
from canonical.widgets.itemswidgets import LabeledMultiCheckBoxWidget
from canonical.lp.dbschema import BranchVisibilityPolicy


class BaseBranchVisibilityPolicyItemView(LaunchpadFormView):
    """Used as a base class for the add and remove view."""

    schema = IBranchVisibilityPolicyItem

    @property
    def adapters(self):
        return {IBranchVisibilityPolicyItem: self.context}

    @property
    def next_url(self):
        return canonical_url(self.context) + '/+branchvisibility'


class AddBranchVisibilityPolicyItemView(BaseBranchVisibilityPolicyItemView):
    """Simple form view to add branch visibility policy items."""

    pagetitle = "Set branch visibility policy for team"

    initial_values = {'policy': BranchVisibilityPolicy.PRIVATE}

    @action(_('Set policy for team'), name='set_policy')
    def set_policy_action(self, action, data):
        "Set the branch policy for the team."
        team = data['team']
        policy = data['policy']
        if team is not None and policy == BranchVisibilityPolicy.FORBIDDEN:
            self.setFieldError(
                'policy',
                "Forbidden can only be chosen as a policy for everyone.")
            self.next_url = None
        else:
            self.context.setTeamBranchVisibilityPolicy(team, policy)


class RemoveBranchVisibilityPolicyItemView(BaseBranchVisibilityPolicyItemView):
    """The view to remove zero or more branch visibility policy items."""

    pagetitle = "Remove branch visibility policy for teams"

    def _policyDescription(self, item):
        """The text visible to the user displayed by the widget."""
        if item.team is None:
            teamname = "Everyone"
        else:
            teamname = item.team.displayname

        return "%s: %s" % (teamname, item.policy.title)

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
                 for item in self.context.branch_visibility_policy_items]

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

    @action(_('Remove selected policy items'), name='remove')
    def remove_action(self, action, data):
        """Remove selected policy items."""
        for item in data['policy_items']:
            self.context.removeTeamFromBranchVisibilityPolicy(item.team)


class BranchVisibilityPolicyView(LaunchpadView):
    """Simple view for displaying branch visibility policies."""

    @cachedproperty
    def items(self):
        return self.context.branch_visibility_policy_items

    @property
    def can_remove_items(self):
        """You cannot remove items if using inherited policy or
        if there is only the default policy item.
        """
        return (len(self.items) > 0 and
                not self.context.isUsingInheritedBranchVisibilityPolicy())

    @property
    def team_policies(self):
        """The policy items that have a valid team."""
        return [item for item in self.items if item.team is not None]
