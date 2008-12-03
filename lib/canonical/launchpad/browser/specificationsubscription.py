# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for SpecificationSubscription."""

__metaclass__ = type
__all__ = [
    'SpecificationSubscriptionAddView',
    'SpecificationSubscriptionEditView',
    ]


from canonical.launchpad import _
from canonical.launchpad.interfaces.specificationsubscription import (
    ISpecificationSubscription)
from canonical.launchpad.webapp import (
    action, canonical_url, GeneralFormView, LaunchpadEditFormView)



class SpecificationSubscriptionAddView(GeneralFormView):

    def process(self, person, essential):
        self._nextURL = canonical_url(self.context)
        return self.context.subscribe(person, self.user, essential)


class SpecificationSubscriptionEditView(LaunchpadEditFormView):

    schema = ISpecificationSubscription
    field_names = ['essential']
    label = 'Edit subscription'

    @action(_('Change'), name='change')
    def change_action(self, action, data):
        self.updateContextFromData(data)
        self.next_url = canonical_url(self.context.specification)
