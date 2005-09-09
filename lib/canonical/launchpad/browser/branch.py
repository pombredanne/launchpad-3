# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Branch views."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.interfaces import IBranch, IBranchSet, ILaunchBag
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.browser.addview import SQLObjectAddView

from canonical.launchpad.webapp import canonical_url

__all__ = [
    'BranchView',
    'BranchEditView',
    'BranchAddView',
    ]


class BranchView:

    __used_for__ = IBranch

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.notices = []
        # figure out who the user is for this transaction
        self.user = getUtility(ILaunchBag).user
        # establish if a subscription form was posted
        newsub = request.form.get('subscribe', None)
        if newsub is not None and self.user and request.method == 'POST':
            if newsub == 'Subscribe':
                self.context.subscribe(self.user)
                self.notices.append("You have subscribed to this branch.")
            elif newsub == 'Unsubscribe':
                self.context.unsubscribe(self.user)
                self.notices.append("You have unsubscribed from this branch.")

    def url(self):
        components = self.context.url.split('/')
        return '/&#x200B;'.join(components)

    @property
    def subscription(self):
        """BranchSubscription for the current user and this branch, or None."""
        if self.user is None:
            return None
        for subscription in self.context.subscriptions:
            if subscription.person.id == self.user.id:
                return subscription
        return None


class BranchEditView(SQLObjectEditView):

    def changed(self):
        self.request.response.redirect(canonical_url(self.context))


class BranchAddView(SQLObjectAddView):
    """Add new branch."""

    _nextURL = None    

    def create(self, name, owner, author, product, url, title,
               lifecycle_status, summary, home_page):
        """Handle a request to create a new branch for this product."""        
        branch_set = getUtility(IBranchSet)
        branch = branch_set.new(
            name=name, owner=owner, author=author, product=product, url=url,
            title=title, lifecycle_status=lifecycle_status, summary=summary,
            home_page=home_page)
        self._nextURL = canonical_url(branch)

    def nextURL(self):
        assert self._nextURL
        return self._nextURL
