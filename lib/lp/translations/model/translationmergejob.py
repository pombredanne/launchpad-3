# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Jobs for merging translations."""

__metaclass__ = type


from zope.interface import implements

from lp.services.job.interfaces.job import IRunnableJob
from lp.services.job.model.job import Job
from lp.services.job.runner import BaseRunnableJob

__all__ = ['TranslationMergeJob']


class TranslationMergeJob(BaseRunnableJob):

    implements(IRunnableJob)

    def __init__(self, job, product, distroseries, sourcepackagename):
        self.job = job
        self.distroseries = distroseries
        self.sourcepackagename = sourcepackagename
        self.product = product

    def run(self):
        pass
