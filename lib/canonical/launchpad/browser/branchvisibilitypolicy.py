# Copyright 2007 Canonical Ltd.  All rights reserved.

"""The view classes for handling branch visibility policies."""

__metaclass__ = type

__all__ = [
    'AddBranchVisibilityPolicyItemView',
    'RemoveBranchVisibilityPolicyItemView',
    'BranchVisibilityPolicyView',
    ]

from canonical.launchpad import _
from canonical.lp.dbschema import BranchVisibilityPolicy

from canonical.launchpad.interfaces import IHasBranchVisibilityPolicy, IBranchVisibilityPolicyItem
from canonical.launchpad.webapp import (
    action, canonical_url, LaunchpadFormView, LaunchpadView)
from canonical.widgets.itemswidgets import LaunchpadRadioWidget, LabeledMultiCheckBoxWidget
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from zope.schema import Choice, List
from zope.formlib import form
from zope.app.form import CustomWidgetFactory


class AddBranchVisibilityPolicyItemView(LaunchpadFormView):

    schema = IBranchVisibilityPolicyItem

    pagetitle = "Add branch visibility policy item"

    initial_values = {'policy': BranchVisibilityPolicy.PRIVATE}

    @property
    def adapters(self):
        return {IBranchVisibilityPolicyItem: self.context}
    
    @property
    def policy(self):
        return self.context.branch_visibility_policy

    @action(_('Set policy for team'), name='set_policy')
    def set_policy_action(self, action, data):
        "Set the branch policy for the team."
        self.policy.setTeamPolicy(data['team'], data['policy'])

    @property
    def next_url(self):
        """See canonical.launchpad.webapp.generalform.GeneralFormView."""
        return canonical_url(self.context) + '/+branchvisibility'


class RemoveBranchVisibilityPolicyItemView(LaunchpadFormView):

    schema = IBranchVisibilityPolicyItem

    pagetitle = "Remove branch visibility policy items"

    @property
    def adapters(self):
        return {IBranchVisibilityPolicyItem: self.context}
    
    @property
    def policy(self):
        return self.context.branch_visibility_policy

    def _policyDescription(self, item):
        
        if item.team is None:
            teamname = "Everyone"
        else:
            teamname = item.team.displayname

        return "%s: %s" % (teamname, item.policy.title)

    def _policyToken(self, item):
        if item.team is None:
            return 'None'
        else:
            return item.team.name

    def _currentPolicyItemsField(self):

        terms = [SimpleTerm(item, self._policyToken(item),
                            self._policyDescription(item))
                 for item in self.policy.items
                 if not item._implicit]

        return form.Fields(
            List(
                __name__='policy_items',
                title=_("Policy Items"),
                value_type=Choice(vocabulary=SimpleVocabulary(terms)),
                required=True),
            render_context=self.render_context,
            custom_widget=CustomWidgetFactory(LabeledMultiCheckBoxWidget))

    def setUpFields(self):
        self.form_fields = self._currentPolicyItemsField()

    @action(_('Remove selected policy items'), name='remove')
    def remove_action(self, action, data):
        "Remove selected policy items"
        for item in data['policy_items']:
            self.policy.removeTeam(item.team)

    @property
    def next_url(self):
        return canonical_url(self.context) + '/+branchvisibility'


class BranchVisibilityPolicyView(LaunchpadView):
    ""

    @property
    def policy(self):
        return self.context.branch_visibility_policy

    @property
    def can_remove_items(self):
        """You cannot remove items if using inherited policy or
        if there is only the default policy item.
        """
        policy_items = self.policy.items
        only_default_policy = (
            len(policy_items) == 1 and policy_items[0]._implicit)
        return not (only_default_policy or self.policy.isUsingInheritedPolicy())
    
