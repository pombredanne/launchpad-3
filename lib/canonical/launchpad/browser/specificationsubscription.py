# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for SpecificationSubscription."""

__metaclass__ = type
__all__ = [
    'SpecificationSubscriptionAddView',
    'SpecificationSubscriptionEditView',
    ]


from canonical.launchpad.webapp import (
    canonical_url, GeneralFormView)

from canonical.launchpad.browser.editview import SQLObjectEditView


class SpecificationSubscriptionAddView(GeneralFormView):

    def process(self, person, essential):
        self._nextURL = canonical_url(self.context)
        return self.context.subscribe(person, self.user, essential)


class SpecificationSubscriptionEditView(SQLObjectEditView):

    def changed(self):
        self.request.response.redirect(
            canonical_url(self.context.specification))

