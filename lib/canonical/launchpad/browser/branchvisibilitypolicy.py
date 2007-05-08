# Copyright 2007 Canonical Ltd.  All rights reserved.

"""The view classes for handling branch visibility policies."""

__metaclass__ = type

__all__ = [
    'BranchVisibilityPolicyView',
    ]

from canonical.launchpad import _
from canonical.lp.dbschema import BranchVisibilityPolicy

from canonical.launchpad.interfaces import IHasBranchVisibilityPolicy, IBranchVisibilityPolicyItem
from canonical.launchpad.webapp import (
    canonical_url, LaunchpadEditFormView)
from canonical.widgets.itemswidgets import LaunchpadRadioWidget, LabeledMultiCheckBoxWidget
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from zope.schema import Choice
from zope.formlib import form
from zope.app.form import CustomWidgetFactory



class BranchVisibilityPolicyView(LaunchpadEditFormView):
    ""
    schema = IBranchVisibilityPolicyItem
    # 
    field_names = ['team','policy']

    initial_values = {'team': None,
                      'policy': BranchVisibilityPolicy.PRIVATE,
                      'policy_items': None}
    
    @property
    def policy(self):
        return self.context.branch_visibility_policy

    def _teamname(self, team):
        if team is None:
            return "Everyone"
        else:
            return team.displayname

    def _token(self, item):
        if item.team is None:
            return 'None'
        else:
            return item.team.name
    
    def _currentPolicyItemsField(self):

        terms = [SimpleTerm(item, self._token(item), self._teamname(item.team))
                 for item in self.policy.items]

        vocab = SimpleVocabulary(terms)

        return form.Fields(
            Choice(
                __name__='policy_items',
                title=_("Policy Items"),
                vocabulary=vocab),
            render_context=self.render_context,
            custom_widget=CustomWidgetFactory(LabeledMultiCheckBoxWidget))

    def setUpFields(self):
        LaunchpadEditFormView.setUpFields(self)
        # import pdb; pdb.set_trace()
        self.form_fields = (self._currentPolicyItemsField() +
                            self.form_fields.select('team', 'policy'))
    
    # We want to have a field that lists all the current policy items
    # with radio buttons, allowing the user to remove them.

    
