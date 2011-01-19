# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Views for SpecificationSubscription."""

__metaclass__ = type
__all__ = [
    'SpecificationSubscriptionAddView',
    'SpecificationSubscriptionEditView',
    ]


from canonical.launchpad import _
from canonical.launchpad.webapp import (
    canonical_url,
    )
from lp.app.browser.launchpadform import (
    action,
    LaunchpadEditFormView,
    LaunchpadFormView,
    )
from lp.blueprints.interfaces.specificationsubscription import (
    ISpecificationSubscription,
    )


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

    @property
    def cancel_url(self):
        return canonical_url(self.context.specification)
