# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Job for merging translations."""

__metaclass__ = type


from zope.interface import implements

from lp.services.job.interfaces.job import IRunnableJob
from lp.services.job.runner import BaseRunnableJob
from lp.translations.model.potemplate import POTemplate, POTemplateSubset
from lp.translations.translationmerger import (
    TransactionManager,
    TranslationMerger,
    )

__all__ = ['TranslationMergeJob']


class TranslationMergeJob(BaseRunnableJob):
    """Job for merging translations between a product and sourcepackage."""

    implements(IRunnableJob)

    def __init__(self, job, productseries, distroseries, sourcepackagename):
        """"Constructor.

        :param job: The `Job` to use for storing basic job state.
        :param productseries: The ProductSeries side of the Packaging.
        :param distroseries: The distroseries of the Packaging sourcepackage.
        :param sourcepackagename: The name of the Packaging sourcepackage.
        """
        self.job = job
        self.distroseries = distroseries
        self.sourcepackagename = sourcepackagename
        self.productseries = productseries

    def run(self):
        """See `IRunnableJob`."""
        tm = TransactionManager(None, False)
        TranslationMerger.mergePackagingTemplates(
            self.productseries, self.sourcepackagename, self.distroseries, tm)
