# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for SpecificationSubscription."""

__metaclass__ = type
__all__ = ['SpecificationSubscriptionAddView']


from canonical.launchpad.webapp import (
    canonical_url, GeneralFormView)
from canonical.launchpad.interfaces import ISpecificationSubscription


class SpecificationSubscriptionAddView(GeneralFormView):

    def process(self, person):
        self._nextURL = canonical_url(self.context)
        return self.context.subscribe(person)

