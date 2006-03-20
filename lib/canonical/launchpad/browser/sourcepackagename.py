# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'SourcePackageNameSetView',
    'SourcePackageNameAddView',
    ]

from zope.component import getUtility
from zope.app.form.browser.add import AddView

from canonical.launchpad.interfaces import (
    ISourcePackageName, ISourcePackageNameSet)
from canonical.launchpad.webapp.batching import BatchNavigator

class SourcePackageNameSetView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def sourcePackagenamesBatchNavigator(self):
        name = self.request.get("name", "")
        if name:
            sourcepackagenames = self.context.findByName(name)
        else:
            sourcepackagenames = self.context.getAll()
        return BatchNavigator(sourcepackagenames, self.request)


class SourcePackageNameAddView(AddView):

    __used_for__ = ISourcePackageName

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self._nextURL = '.'
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        self.name = data['name']
        name_set = getUtility(ISourcePackageNameSet)
        name_set.getOrCreateByName(self.name)
        self._nextURL = '.?name=%s' % self.name

    def nextURL(self):
        return self._nextURL

