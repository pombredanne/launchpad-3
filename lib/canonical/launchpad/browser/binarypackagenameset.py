# zope imports
from zope.component import getUtility
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

# launchpad import
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator

BATCH_SIZE = 40

class BinaryPackageNameSetView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def binaryPackagenamesBatchNavigator(self):
        name = self.request.get("name", "")

        if not name:
            binary_packagenames = list(self.context)
        else:
            binary_packagenames = list(self.context.findByName(name))

        start = int(self.request.get('batch_start', 0))
        end = int(self.request.get('batch_end', BATCH_SIZE))
        batch_size = BATCH_SIZE

        batch = Batch(list=binary_packagenames, start=start, size=batch_size)
        return BatchNavigator(batch=batch, request=self.request)
