# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'BinaryPackageNameSetView',
    'BinaryPackageNameAddView',
    ]

from zope.component import getUtility
from zope.app.form.browser.add import AddView

from canonical.launchpad.interfaces import (
    IBinaryPackageName, IBinaryPackageNameSet)
from canonical.launchpad.webapp.batching import BatchNavigator


class BinaryPackageNameSetView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def binaryPackagenamesBatchNavigator(self):
        name = self.request.get("name", "")
        if name:
            binary_packagenames = self.context.findByName(name)
        else:
            binary_packagenames = self.context.getAll()
        return BatchNavigator(binary_packagenames, self.request)


class BinaryPackageNameAddView(AddView):

    __used_for__ = IBinaryPackageName


    def __init__(self, context, request):
        self.context = context
        self.request = request
        self._nextURL = '.'
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        self.name = data['name']
        name_set = getUtility(IBinaryPackageNameSet)
        name_set.getOrCreateByName(self.name)
        self._nextURL = '.?name=%s' % self.name

    def nextURL(self):
        return self._nextURL
