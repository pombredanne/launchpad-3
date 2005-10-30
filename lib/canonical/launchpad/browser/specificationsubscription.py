# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for SpecificationSubscription."""

__metaclass__ = type
__all__ = ['SpecificationSubscriptionAddView']

from canonical.launchpad.browser.form import FormView
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.interfaces import ISpecificationSubscription


class SpecificationSubscriptionAddView(FormView):

    schema = ISpecificationSubscription
    fieldNames = ['person']
    _arguments = ['person']

    def process(self, person):
        self._nextURL = canonical_url(self.context)
        return self.context.subscribe(person)

