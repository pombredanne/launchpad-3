# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    "PackageCopyJob",
    "PlainPackageCopyJob",
    "specify_dsd_package",
]

from lazr.delegates import delegates
import simplejson
from storm.locals import (
    And,
    Int,
    Reference,
    Unicode,
    )
import transaction
from zope.component import getUtility
from zope.interface import (
    classProvides,
    implements,
    )

from canonical.database.enumcol import EnumCol
from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet,
    )
from canonical.launchpad.interfaces.lpstorm import (
    IMasterStore,
    IStore,
    )
from lp.app.errors import NotFoundError
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.registry.interfaces.distroseriesdifference import (
    IDistroSeriesDifferenceSource,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.sourcepackagename import ISourcePackageNameSet
from lp.registry.model.distroseries import DistroSeries
from lp.registry.interfaces.distroseriesdifferencecomment import (
    IDistroSeriesDifferenceCommentSource,
    )
from lp.services.database.stormbase import StormBase
from lp.services.job.interfaces.job import JobStatus
from lp.services.job.model.job import Job
from lp.services.job.runner import BaseRunnableJob
from lp.soyuz.interfaces.archive import CannotCopy
from lp.soyuz.interfaces.packagecopyjob import (
    IPackageCopyJob,
    IPlainPackageCopyJob,
    IPlainPackageCopyJobSource,
    PackageCopyJobType,
    )
from lp.soyuz.model.archive import Archive
from lp.soyuz.scripts.packagecopier import do_copy


def specify_dsd_package(dsd):
    """Return (name, parent version) for `dsd`'s package.

    This describes the package that `dsd` is for in a format suitable for
    `PlainPackageCopyJobSource`.

    :param dsd: A `DistroSeriesDifference`.
    """
    return (dsd.source_package_name.name, dsd.parent_source_version)


class PackageCopyJob(StormBase):
    """Base class for package copying jobs."""

    implements(IPackageCopyJob)

    __storm_table__ = 'PackageCopyJob'

    id = Int(primary=True)

    job_id = Int(name='job')
    job = Reference(job_id, Job.id)

    source_archive_id = Int(name='source_archive')
    source_archive = Reference(source_archive_id, Archive.id)

    target_archive_id = Int(name='target_archive')
    target_archive = Reference(target_archive_id, Archive.id)

    target_distroseries_id = Int(name='target_distroseries')
    target_distroseries = Reference(target_distroseries_id, DistroSeries.id)

    job_type = EnumCol(enum=PackageCopyJobType, notNull=True)

    _json_data = Unicode('json_data')

    def __init__(self, source_archive, target_archive, target_distroseries,
                 job_type, metadata):
        super(PackageCopyJob, self).__init__()
        self.job = Job()
        self.source_archive = source_archive
        self.target_archive = target_archive
        self.target_distroseries = target_distroseries
        self.job_type = job_type
        self._json_data = self.serializeMetadata(metadata)

    @classmethod
    def serializeMetadata(cls, metadata_dict):
        """Serialize a dict of metadata into a unicode string."""
        return simplejson.dumps(metadata_dict).decode('utf-8')

    @property
    def metadata(self):
        return simplejson.loads(self._json_data)

    def extendMetadata(self, metadata_dict):
        """Add metadata_dict to the existing metadata."""
        existing = self.metadata
        existing.update(metadata_dict)
        self._json_data = self.serializeMetadata(existing)


class PackageCopyJobDerived(BaseRunnableJob):
    """Abstract class for deriving from PackageCopyJob."""

    delegates(IPackageCopyJob)

    def __init__(self, job):
        self.context = job

    @classmethod
    def get(cls, job_id):
        """Get a job by id.

        :return: the PackageCopyJob with the specified id, as the current
            PackageCopyJobDerived subclass.
        :raises: NotFoundError if there is no job with the specified id, or
            its job_type does not match the desired subclass.
        """
        job = PackageCopyJob.get(job_id)
        if job.job_type != cls.class_job_type:
            raise NotFoundError(
                'No object found with id %d and type %s' % (job_id,
                cls.class_job_type.title))
        return cls(job)

    @classmethod
    def iterReady(cls):
        """Iterate through all ready PackageCopyJobs."""
        jobs = IStore(PackageCopyJob).find(
            PackageCopyJob,
            And(PackageCopyJob.job_type == cls.class_job_type,
                PackageCopyJob.job == Job.id,
                Job.id.is_in(Job.ready_jobs)))
        return (cls(job) for job in jobs)

    def getOopsVars(self):
        """See `IRunnableJob`."""
        vars = super(PackageCopyJobDerived, self).getOopsVars()
        vars.extend([
            ('source_archive_id', self.context.source_archive_id),
            ('target_archive_id', self.context.target_archive_id),
            ('target_distroseries_id', self.context.target_distroseries_id),
            ('package_copy_job_id', self.context.id),
            ('package_copy_job_type', self.context.job_type.title),
            ])
        return vars


class PlainPackageCopyJob(PackageCopyJobDerived):
    """Job that copies packages between archives."""
    # This job type serves in different places: it supports copying
    # packages between archives, but also the syncing of packages from
    # parents into a derived distroseries.  We may split these into
    # separate types at some point, but for now we (allenap, bigjools,
    # jtv) chose to keep it as one.

    implements(IPlainPackageCopyJob)

    class_job_type = PackageCopyJobType.PLAIN
    classProvides(IPlainPackageCopyJobSource)

    @classmethod
    def create(cls, source_packages, source_archive,
               target_archive, target_distroseries, target_pocket,
               include_binaries=False):
        """See `IPlainPackageCopyJobSource`."""
        metadata = {
            'source_packages': source_packages,
            'target_pocket': target_pocket.value,
            'include_binaries': bool(include_binaries),
            }
        job = PackageCopyJob(
            source_archive=source_archive,
            target_archive=target_archive,
            target_distroseries=target_distroseries,
            job_type=cls.class_job_type,
            metadata=metadata)
        IMasterStore(PackageCopyJob).add(job)
        return cls(job)

    @classmethod
    def getActiveJobs(cls, target_archive):
        """See `IPlainPackageCopyJobSource`."""
        jobs = IStore(PackageCopyJob).find(
            PackageCopyJob,
            PackageCopyJob.job_type == cls.class_job_type,
            PackageCopyJob.target_archive == target_archive,
            Job.id == PackageCopyJob.job_id,
            Job._status == JobStatus.WAITING)
        jobs = jobs.order_by(PackageCopyJob.id)
        return DecoratedResultSet(jobs, cls)

    @classmethod
    def getPendingJobsForTargetSeries(cls, target_series):
        """Get upcoming jobs for `target_series`, ordered by age."""
        raw_jobs = IStore(PackageCopyJob).find(
            PackageCopyJob,
            Job.id == PackageCopyJob.job_id,
            PackageCopyJob.job_type == cls.class_job_type,
            PackageCopyJob.target_distroseries == target_series,
            Job._status.is_in(Job.PENDING_STATUSES))
        raw_jobs = raw_jobs.order_by(PackageCopyJob.id)
        return DecoratedResultSet(raw_jobs, cls)

    @classmethod
    def getPendingJobsPerPackage(cls, target_series):
        """See `IPlainPackageCopyJobSource`."""
        result = {}
        # Go through jobs in-order, picking the first matching job for
        # any (package, version) tuple.  Because of how
        # getPendingJobsForTargetSeries orders its results, the first
        # will be the oldest and thus presumably the first to finish.
        for job in cls.getPendingJobsForTargetSeries(target_series):
            for package in job.metadata["source_packages"]:
                result.setdefault(tuple(package), job)
        return result

    @property
    def source_packages(self):
        getPublishedSources = self.source_archive.getPublishedSources
        for name, version in self.metadata['source_packages']:
            yield name, version, getPublishedSources(
                name=name, version=version, exact_match=True).first()

    @property
    def target_pocket(self):
        return PackagePublishingPocket.items[self.metadata['target_pocket']]

    @property
    def include_binaries(self):
        return self.metadata['include_binaries']

    def run(self):
        """See `IRunnableJob`."""
        try:
            self.attemptCopy()
        except CannotCopy, e:
            self.abort()
            self.reportFailure(e)

    def attemptCopy(self):
        """Attempt to perform the copy.

        :raise CannotCopy: If the copy fails for a reason that the user
            can deal with.
        """
        if self.target_archive.is_ppa:
            if self.target_pocket != PackagePublishingPocket.RELEASE:
                raise CannotCopy(
                    "Destination pocket must be 'release' for a PPA.")

        source_packages = set()
        for name, version, source_package in self.source_packages:
            if source_package is None:
                raise CannotCopy(
                    "Package %r %r not found." % (name, version))
            else:
                source_packages.add(source_package)

        do_copy(
            sources=source_packages, archive=self.target_archive,
            series=self.target_distroseries, pocket=self.target_pocket,
            include_binaries=self.include_binaries, check_permissions=False)

    def abort(self):
        """Abort work."""
        transaction.abort()

    def findMatchingDSDs(self):
        """Find any `DistroSeriesDifference`s that this job might resolve."""
        dsd_source = getUtility(IDistroSeriesDifferenceSource)
        target_series = self.target_distroseries
        candidates = dsd_source.getForDistroSeries(
            distro_series=target_series)
        # The job doesn't know what distroseries a given package is
        # coming from, and the version number in the DSD may have
        # changed.  We can however filter out DSDs that are from
        # different distributions, based on the job's target archive.
        source_distro_id = self.source_archive.distributionID
        package_ids = set(
            getUtility(ISourcePackageNameSet).queryByName(name).id
            for name, version in self.metadata["source_packages"])
        return [
            dsd
            for dsd in candidates
                if dsd.parent_series.distributionID == source_distro_id and
                    dsd.source_package_name_id in package_ids]

    def reportFailure(self, cannotcopy_exception):
        """Attempt to report failure to the user."""
        message = unicode(cannotcopy_exception)
        dsds = self.findMatchingDSDs()
        comment_source = getUtility(IDistroSeriesDifferenceCommentSource)

        # Register the error comment in the name of the Janitor.  Not a
        # great choice, but we have no user identity to represent
        # Launchpad; it's far too costly to create one; and
        # impersonating the requester can be misleading and would also
        # involve extra bookkeeping.
        reporting_persona = getUtility(ILaunchpadCelebrities).janitor

        for dsd in dsds:
            comment_source.new(dsd, reporting_persona, message)

    def __repr__(self):
        """Returns an informative representation of the job."""
        parts = ["%s to copy" % self.__class__.__name__]
        source_packages = self.metadata["source_packages"]
        if len(source_packages) == 0:
            parts.append(" no packages (!)")
        else:
            parts.append(" %d package(s)" % len(source_packages))
        parts.append(
            " from %s/%s" % (
                self.source_archive.distribution.name,
                self.source_archive.name))
        parts.append(
            " to %s/%s" % (
                self.target_archive.distribution.name,
                self.target_archive.name))
        parts.append(
            ", %s pocket," % self.target_pocket.name)
        if self.target_distroseries is not None:
            parts.append(" in %s" % self.target_distroseries)
        if self.include_binaries:
            parts.append(", including binaries")
        return "<%s>" % "".join(parts)
