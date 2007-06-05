# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for SprintSpecification."""

__metaclass__ = type

__all__ = [
    'SprintSpecificationDecideView',
    ]

from canonical.launchpad.webapp import canonical_url, LaunchpadView


class SprintSpecificationDecideView(LaunchpadView):

    def initialize(self):
        accept = self.request.form.get('accept')
        decline = self.request.form.get('decline')
        cancel = self.request.form.get('cancel')
        decided = False
        if accept is not None:
            self.context.acceptBy(self.user)
            decided = True
        elif decline is not None:
            self.context.declineBy(self.user)
            decided = True
        if decided or cancel is not None:
            self.request.response.redirect(
                canonical_url(self.context.specification))

