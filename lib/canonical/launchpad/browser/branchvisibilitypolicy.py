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
    action, canonical_url, LaunchpadFormView)
from canonical.widgets.itemswidgets import LaunchpadRadioWidget, LabeledMultiCheckBoxWidget
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from zope.schema import Choice, List
from zope.formlib import form
from zope.app.form import CustomWidgetFactory


class BranchVisibilityPolicyView(LaunchpadFormView):
    ""
    schema = IBranchVisibilityPolicyItem
    # 
    field_names = ['team','policy']

    initial_values = {'team': None,
                      'policy': BranchVisibilityPolicy.PRIVATE,
                      'policy_items': None}

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

    #def _validate(self, action, data):
    #    import pdb; pdb.set_trace()
    #    LaunchpadEditFormView._validate(self, action, data)

    def _currentPolicyItemsField(self):

        terms = [SimpleTerm(item, self._policyToken(item),
                            self._policyDescription(item))
                 for item in self.policy.items]

        #vocab = SimpleVocabulary(terms)
        #import pdb; pdb.set_trace()
        return form.Fields(
            List(
                __name__='policy_items',
                title=_("Policy Items"),
                value_type=Choice(vocabulary=SimpleVocabulary(terms)),
                required=False),
            render_context=self.render_context,
            custom_widget=CustomWidgetFactory(LabeledMultiCheckBoxWidget))

    def setUpFields(self):
        LaunchpadFormView.setUpFields(self)
        # import pdb; pdb.set_trace()
        self.form_fields = (self._currentPolicyItemsField() +
                            self.form_fields.select('team', 'policy'))


    @action(_('Remove'), name='remove')
    def remove_action(self, action, data):
        "Remove selected policy items"

    @action(_('Add'), name='add')
    def add_action(self, action, data):
        "Add new item"

    
    # We want to have a field that lists all the current policy items
    # with radio buttons, allowing the user to remove them.

    
