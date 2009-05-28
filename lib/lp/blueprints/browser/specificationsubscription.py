# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for SpecificationSubscription."""

__metaclass__ = type
__all__ = [
    'SpecificationSubscriptionAddView',
    'SpecificationSubscriptionEditView',
    ]


from canonical.launchpad import _
from lp.blueprints.interfaces.specificationsubscription import (
    ISpecificationSubscription)
from canonical.launchpad.webapp import (
    action, canonical_url, LaunchpadEditFormView, LaunchpadFormView)


class SpecificationSubscriptionAddView(LaunchpadFormView):

    schema = ISpecificationSubscription
    field_names = ['person', 'essential']
    label = 'Subscribe someone else'
    for_input = True

    @action(_('Continue'), name='continue')
    def continue_action(self, action, data):
        self.context.subscribe(data['person'], self.user, data['essential'])
        self.next_url = canonical_url(self.context)

    @property
    def cancel_url(self):
        return canonical_url(self.context)


class SpecificationSubscriptionEditView(LaunchpadEditFormView):

    schema = ISpecificationSubscription
    field_names = ['essential']
    label = 'Edit subscription'

    @action(_('Change'), name='change')
    def change_action(self, action, data):
        self.updateContextFromData(data)
        self.next_url = canonical_url(self.context.specification)
