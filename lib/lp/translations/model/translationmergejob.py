# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Job for merging translations."""

__metaclass__ = type


from zope.interface import (
    classProvides,
    implements,
    )

from lp.services.job.interfaces.job import (
    IRunnableJob,
    )
from lp.services.job.runner import BaseRunnableJob
from lp.translations.interfaces.translationmergejob import (
    ITranslationMergeJobSource,
    )
from lp.registry.model.packagingjob import (
    PackagingJob,
    PackagingJobDerived,
    PackagingJobType,
    )
from lp.translations.translationmerger import (
    TransactionManager,
    TranslationMerger,
    )

__all__ = ['TranslationMergeJob']


def schedule_merge(packaging, event):
    """Event subscriber to create a TranslationMergeJob on new packagings.

    :param packaging: The `Packaging` to create a `TranslationMergeJob` for.
    :param event: The event itself.
    """
    return TranslationMergeJob.forPackaging(packaging)


class TranslationMergeJob(PackagingJobDerived, BaseRunnableJob):
    """Job for merging translations between a product and sourcepackage."""

    classProvides(ITranslationMergeJobSource)

    implements(IRunnableJob)

    class_job_type = PackagingJobType.TRANSLATION_MERGE

    @classmethod
    def forPackaging(cls, packaging):
        """Create a TranslationMergeJob for a Packaging.

        :param packaging: The `Packaging` to create the job for.
        :return: A `TranslationMergeJob`.
        """
        return cls.create(
            packaging.productseries, packaging.distroseries,
            packaging.sourcepackagename)

    @classmethod
    def iterReady(cls):
        """See `IJobSource`."""
        return super(TranslationMergeJob, cls).iterReady(
            [PackagingJob.job_type == cls.class_job_type])

    def run(self):
        """See `IRunnableJob`."""
        if not self.distroseries.distribution.full_functionality:
            return
        tm = TransactionManager(None, False)
        TranslationMerger.mergePackagingTemplates(
            self.productseries, self.sourcepackagename, self.distroseries, tm)
