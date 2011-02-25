# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Job for merging translations."""

__metaclass__ = type

__all__ = [
    'PackagingJob',
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

    TRANSLATION_SPLIT = DBItem(1, """
        Split translations between productseries and sourcepackage.

        Split translations between productseries and sourcepackage.
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


class RegisteredSubclass(type):
    """Metaclass for when subclasses should be registered."""

    def __init__(cls, name, bases, dict_):
        cls._register_subclass(cls)


class PackagingJobDerived:
    """Base class for specialized Packaging Job types."""

    __metaclass__ = RegisteredSubclass

    delegates(IPackagingJob, 'job')

    _subclass = {}
    _event_types = {}

    @property
    def sourcepackage(self):
        return self.distroseries.getSourcePackage(self.sourcepackagename)

    @staticmethod
    def _register_subclass(cls):
        """Register this class with its enumeration."""
        # This would be a classmethod, except that subclasses (e.g.
        # TranslationPackagingJob) need to be able to override it and call
        # into it, and there's no syntax to call a base class's version of a
        # classmethod with the subclass as the first parameter.
        job_type = getattr(cls, 'class_job_type', None)
        if job_type is not None:
            value = cls._subclass.setdefault(job_type, cls)
            assert value is cls, (
                '%s already registered to %s.' % (
                    job_type.name, value.__name__))
        event_type = getattr(cls, 'create_on_event', None)
        if event_type is not None:
            cls._event_types.setdefault(event_type, []).append(cls)

    def __init__(self, job):
        assert job.job_type == self.class_job_type, (
            "Attempting to create a %s using a %s PackagingJob" %
            (self.__class__.__name__, job.job_type))
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
    def scheduleJob(cls, packaging, event):
        """Event subscriber to create a PackagingJob on events.

        :param packaging: The `Packaging` to create a `TranslationMergeJob`
            for.
        :param event: The event itself.
        """
        for event_type, job_classes in cls._event_types.iteritems():
            if not event_type.providedBy(event):
                continue
            for job_class in job_classes:
                job_class.forPackaging(packaging)

    @classmethod
    def iterReady(cls, extra_clauses):
        """See `IJobSource`.

        This version will emit any ready job based on PackagingJob.
        :param extra_clauses: Extra clauses to reduce the selections.
        """
        store = IStore(PackagingJob)
        jobs = store.find(
            (PackagingJob),
            PackagingJob.job == Job.id,
            Job.id.is_in(Job.ready_jobs),
            *extra_clauses)
        return (cls._subclass[job.job_type](job) for job in jobs)


#make accessible to zcml
schedule_job = PackagingJobDerived.scheduleJob
