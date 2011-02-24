# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Job for merging translations."""

__metaclass__ = type

__all__ = [
    'PackagingJobType',
    'PackagingJobDerived',
    ]

from lazr.delegates import delegates
from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    )
from storm.locals import (
    Int,
    Reference,
    )

from canonical.database.enumcol import EnumCol
from canonical.launchpad.interfaces.lpstorm import (
    IStore,
    )
from lp.registry.interfaces.packagingjob import IPackagingJob
from lp.registry.model.distroseries import DistroSeries
from lp.registry.model.productseries import ProductSeries
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.services.database.stormbase import StormBase
from lp.services.job.interfaces.job import IJob
from lp.services.job.model.job import Job

class PackagingJobType(DBEnumeratedType):
    """Types of Packaging Job."""

    TRANSLATION_MERGE = DBItem(0, """
        Merge translations betweeen productseries and sourcepackage.

        Merge translations betweeen productseries and sourcepackage.
        """)


class PackagingJob(StormBase):
    """Base class for jobs related to a packaging."""

    __storm_table__ = 'PackagingJob'

    id = Int(primary=True)

    job_id = Int('job')

    job = Reference(job_id, Job.id)

    delegates(IJob, 'job')

    job_type = EnumCol(enum=PackagingJobType, notNull=True)

    productseries_id = Int('productseries')

    productseries = Reference(productseries_id, ProductSeries.id)

    distroseries_id = Int('distroseries')

    distroseries = Reference(distroseries_id, DistroSeries.id)

    sourcepackagename_id = Int('sourcepackagename')

    sourcepackagename = Reference(sourcepackagename_id, SourcePackageName.id)

    def __init__(self, job, job_type, productseries, distroseries,
                 sourcepackagename):
        """"Constructor.

        :param job: The `Job` to use for storing basic job state.
        :param productseries: The ProductSeries side of the Packaging.
        :param distroseries: The distroseries of the Packaging sourcepackage.
        :param sourcepackagename: The name of the Packaging sourcepackage.
        """
        self.job = job
        self.job_type = job_type
        self.distroseries = distroseries
        self.sourcepackagename = sourcepackagename
        self.productseries = productseries


class PackagingJobDerived:

    delegates(IPackagingJob, 'job')

    def __init__(self, job):
        assert job.job_type == self.class_job_type
        self.job = job

    @classmethod
    def create(cls, productseries, distroseries, sourcepackagename):
        """"Create a TranslationMergeJob backed by a PackageJob.

        :param productseries: The ProductSeries side of the Packaging.
        :param distroseries: The distroseries of the Packaging sourcepackage.
        :param sourcepackagename: The name of the Packaging sourcepackage.
        """
        context = PackagingJob(
            Job(), cls.class_job_type, productseries,
            distroseries, sourcepackagename)
        return cls(context)

    @classmethod
    def iterReady(cls):
        """See `IJobSource`."""
        store = IStore(PackagingJob)
        jobs = store.find(
            (PackagingJob),
            PackagingJob.job_type == cls.class_job_type,
            PackagingJob.job == Job.id,
            Job.id.is_in(Job.ready_jobs),
        )
        return (cls(job) for job in jobs)
