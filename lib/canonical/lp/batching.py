import re

from zope.interface import implements
from canonical.lp.z3batching import Batch
from canonical.lp.interfaces import IBatchNavigator

class BatchNavigator(object):

    implements(IBatchNavigator)

    def __init__(self, batch, request=None):
        self.batch = batch
        self.request = request

    def cleanQueryString(self, query_string):

        nav_params = re.compile("[?&]?batch_start=\d+&batch_end=\d+")
        return nav_params.sub("", query_string)

    def generateBatchURL(self, batch):
        qs = self.request.environment.get('QUERY_STRING', '')
        qs = self.cleanQueryString(qs)
        if qs:
            qs += "&"

        url = ""
        if not batch:
            return url

        url = "%s?%sbatch_start=%d&batch_end=%d" % \
            (str(self.request.URL), qs, batch.startNumber() - 1,
             batch.endNumber())
        return url

    def getBatches(self):
        batch = Batch(self.batch.list, size = self.batch.size)
        batches = [batch]
        while 1:
            batch = batch.nextBatch()
            if not batch:
                break
            batches.append(batch)
        return batches

    def prevBatchURL(self):
        return self.generateBatchURL(self.batch.prevBatch())

    def nextBatchURL(self):
        return self.generateBatchURL(self.batch.nextBatch())

    def batchPageURLs(self):
        batches = self.getBatches()
        urls = []
        for page_number in range(len(batches)):
            this_batch = batches[page_number]
            url = self.generateBatchURL(this_batch)
            urls.append({ page_number + 1 : url })
        return urls

    def currentBatch(self):
        return self.batch

