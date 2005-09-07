# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Branch views."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.interfaces import IBranch
from canonical.launchpad.browser.editview import SQLObjectEditView

from canonical.launchpad.webapp import canonical_url

__all__ = [
    'BranchView',
    'BranchEditView',
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
