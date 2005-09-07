# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Branch views."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.interfaces import IBranch, IBranchSet
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

    def url(self):
        components = self.context.url.split('/')
        return '/&#x200B;'.join(components)


class BranchEditView(SQLObjectEditView):

    def changed(self):
        self.request.response.redirect(canonical_url(self.context))


class BranchAddView(SQLObjectAddView):
    """Add new branch."""

    _nextURL = None    

    def create(self, name, owner, product, url, title, lifecycle_status,
               summary, home_page):
        """Handle a request to create a new branch for this product."""        
        branch_set = getUtility(IBranchSet)
        branch = branch_set.new(name, owner, product, url, title,
                                lifecycle_status, summary, home_page)
        self._nextURL = canonical_url(branch)

    def nextURL(self):
        assert self._nextURL
        return self._nextURL


