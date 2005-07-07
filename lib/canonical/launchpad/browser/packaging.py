# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'PackagingAddView',
    ]

from zope.app.form.browser.add import AddView
from zope.component import getUtility

from canonical.launchpad.interfaces import IPackaging, IPackagingUtil

class PackagingAddView(AddView):

    __used_for__ = IPackaging

    def __init__(self, context, request):
        self.context = context
        self.request = request
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        # retrieve submitted values from the form
        productseries = data['productseries']
        sourcepackagename = data['sourcepackagename']
        distrorelease = data['distrorelease']
        packaging = data['packaging']

        # Invoke utility to create a packaging entry
        util = getUtility(IPackagingUtil)
        util.createPackaging(productseries, sourcepackagename,
                             distrorelease, packaging)

        # back to Product Page 
        self._nextURL = '.'

    def nextURL(self):
        return self._nextURL

