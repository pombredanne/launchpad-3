# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for SprintSpecification."""

__metaclass__ = type

from zope.app.form.browser.add import AddView
from zope.component import getUtility

from canonical.launchpad.helpers import check_permission

from canonical.launchpad.interfaces import ILaunchBag

from canonical.lp.dbschema import SprintSpecificationStatus

from canonical.launchpad.webapp import canonical_url, LaunchpadView


__all__ = [
    'SprintSpecificationAddView',
    'SprintSpecificationDecideView',
    ]

class SprintSpecificationAddView(AddView):

    def create(self, sprint):
        user = getUtility(ILaunchBag).user
        # NB the context here is a specification
        sprint_link = self.context.linkSprint(sprint, user)
        if check_permission('launchpad.Edit', sprint_link):
            sprint_link.acceptBy(user)
        return sprint_link

    def add(self, content):
        """Skipping 'adding' this content to a container, because
        this is a placeless system."""
        return content

    def nextURL(self):
        return canonical_url(self.context)


class SprintSpecificationDecideView(LaunchpadView):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        user = getUtility(ILaunchBag).user
        accept = request.form.get('accept')
        decline = request.form.get('decline')
        cancel = request.form.get('cancel')
        decided = False
        if accept is not None:
            self.context.acceptBy(user)
            decided = True
        elif decline is not None:
            self.context.declineBy(user)
            decided = True
        if decided or cancel is not None:
            self.request.response.redirect(
                canonical_url(self.context.specification))

