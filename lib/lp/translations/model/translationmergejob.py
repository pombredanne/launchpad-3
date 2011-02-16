# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Job for merging translations."""

__metaclass__ = type


from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    )
from storm.locals import (
    Int,
    Reference,
    )
from zope.interface import (
    classProvides,
    implements,
    )

from canonical.database.enumcol import EnumCol
from canonical.launchpad.interfaces.lpstorm import (
    IStore,
    )
from lp.registry.model.distroseries import DistroSeries
from lp.registry.model.productseries import ProductSeries
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.services.database.stormbase import StormBase
from lp.services.job.interfaces.job import (
    IRunnableJob,
    )
from lp.services.job.model.job import Job
from lp.services.job.runner import BaseRunnableJob
from lp.translations.interfaces.translationmergejob import (
    ITranslationMergeJobSource,
    )
from lp.translations.translationmerger import (
    TransactionManager,
    TranslationMerger,
    )

__all__ = ['TranslationMergeJob']


class PackagingJobType(DBEnumeratedType):
    """Types of Packaging Job."""

    TRANSLATION_MERGE = DBItem(0, """
        Merge translations betweeen productseries and sourcepackage.

        Merge translations betweeen productseries and sourcepackage.
        """)


class TranslationMergeJob(StormBase, BaseRunnableJob):
    """Job for merging translations between a product and sourcepackage."""

    classProvides(ITranslationMergeJobSource)

    implements(IRunnableJob)

    __storm_table__ = 'PackagingJob'

    id = Int(primary=True)

    job_id = Int('job')

    job = Reference(job_id, Job.id)

    job_type = EnumCol(enum=PackagingJobType, notNull=True)

    productseries_id = Int('productseries')

    productseries = Reference(productseries_id, ProductSeries.id)

    distroseries_id = Int('distroseries')

    distroseries = Reference(distroseries_id, DistroSeries.id)

    sourcepackagename_id = Int('sourcepackagename')

    sourcepackagename = Reference(sourcepackagename_id, SourcePackageName.id)

    def __init__(self, job, productseries, distroseries, sourcepackagename):
        """"Constructor.

        :param job: The `Job` to use for storing basic job state.
        :param productseries: The ProductSeries side of the Packaging.
        :param distroseries: The distroseries of the Packaging sourcepackage.
        :param sourcepackagename: The name of the Packaging sourcepackage.
        """
        self.job = job
        self.job_type = PackagingJobType.TRANSLATION_MERGE
        self.distroseries = distroseries
        self.sourcepackagename = sourcepackagename
        self.productseries = productseries

    @classmethod
    def iterReady(cls):
        """See `IJobSource`."""
        store = IStore(cls)
        jobs = store.find(
            (TranslationMergeJob),
            TranslationMergeJob.job_type ==
                PackagingJobType.TRANSLATION_MERGE,
            TranslationMergeJob.job == Job.id,
            Job.id.is_in(Job.ready_jobs),
        )
        return jobs

    def run(self):
        """See `IRunnableJob`."""
        tm = TransactionManager(None, False)
        TranslationMerger.mergePackagingTemplates(
            self.productseries, self.sourcepackagename, self.distroseries, tm)
