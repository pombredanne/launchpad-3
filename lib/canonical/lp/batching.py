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
        nav_params = re.compile(r"&?batch_start=\d&batch_end=\d")
        return nav_params.sub("", query_string)

    def prevBatchURL(self):
        prev_url = ""
        qs = self.cleanQueryString(self.request.environment.get('QUERY_STRING', ''))
        if qs:
            qs += "&"
        prev_batch = self.batch.prevBatch()
        if prev_batch:
            prev_url = str(self.request.URL)
            prev_url += "?%sbatch_start=%d&batch_end=%d" % (
                qs, prev_batch.startNumber() - 1, prev_batch.endNumber())

        return prev_url

    def nextBatchURL(self):
        next_url = ""
        next_batch = self.batch.nextBatch()
        qs = self.cleanQueryString(self.request.environment.get('QUERY_STRING', ''))
        if qs:
            qs += "&"
        if next_batch:
            next_url = str(self.request.URL)
            next_url += "?%sbatch_start=%d&batch_end=%d" % (
                qs, next_batch.startNumber() - 1, next_batch.endNumber())

        return next_url

    def batchPageURLs(self):
        batch = Batch(self.batch.list, size = self.batch.size)
        batches = [batch]
        got_all_batches = False
        while not got_all_batches:
            batch = batch.nextBatch()
            if batch:
                batches.append(batch)
            else:
                got_all_batches = True

        urls = []
        base_url_template = str(self.request.URL) + "?%sbatch_start=%d&batch_end=%d"
        qs = self.cleanQueryString(self.request.environment.get('QUERY_STRING', ''))
        if qs:
            qs += "&"
        for page_number in range(len(batches)):
            this_batch = batches[page_number]
            urls.append({
                page_number + 1 :
                base_url_template % (
                    qs, this_batch.startNumber() - 1, this_batch.endNumber())})

        return urls

    def currentBatch(self):
        return self.batch
