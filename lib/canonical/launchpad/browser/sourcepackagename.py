# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'SourcePackageNameSetView',
    'SourcePackageNameAddView',
    ]

from zope.component import getUtility
from zope.app.form.browser.add import AddView

from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
from canonical.launchpad.interfaces import (
    ISourcePackageName, ISourcePackageNameSet)

BATCH_SIZE = 40

class SourcePackageNameSetView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def sourcePackagenamesBatchNavigator(self):
        name = self.request.get("name", "")

        if not name:
            source_packagenames = list(self.context)
        else:
            source_packagenames = list(self.context.findByName(name))

        start = int(self.request.get('batch_start', 0))
        end = int(self.request.get('batch_end', BATCH_SIZE))
        batch_size = BATCH_SIZE

        batch = Batch(list=source_packagenames, start=start, size=batch_size)
        return BatchNavigator(batch=batch, request=self.request)


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
