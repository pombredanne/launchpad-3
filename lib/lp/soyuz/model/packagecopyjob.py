# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    "PackageCopyJob",
    "PlainPackageCopyJob",
]

from lazr.delegates import delegates
import simplejson
from storm.locals import (
    And,
    Int,
    Reference,
    Unicode,
    )
from zope.interface import (
    classProvides,
    implements,
    )

from canonical.database.enumcol import EnumCol
from canonical.launchpad.interfaces.lpstorm import (
    IMasterStore,
    IStore,
    )
from lp.app.errors import NotFoundError
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.model.distroseries import DistroSeries
from lp.services.database.stormbase import StormBase
from lp.services.job.model.job import Job
from lp.services.job.runner import BaseRunnableJob
from lp.soyuz.interfaces.archive import CannotCopy
from lp.soyuz.interfaces.packagecopyjob import (
    IPackageCopyJob,
    IPackageCopyJobSource,
    PackageCopyJobType,
    )
from lp.soyuz.model.archive import Archive
from lp.soyuz.scripts.packagecopier import do_copy


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

    target_distroseries_id = Int(name='target_archive')
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

    implements(IPackageCopyJob)

    class_job_type = PackageCopyJobType.PLAIN
    classProvides(IPackageCopyJobSource)

    @classmethod
    def create(cls, source_packages, source_archive,
               target_archive, target_distroseries, target_pocket,
               include_binaries=False):
        """See `IPackageCopyJobSource`."""
        metadata = {
            'source_packages': source_packages,
            'target_pocket': target_pocket.value,
            'include_binaries': bool(include_binaries),
            }
        job = PackageCopyJob(
            target_distroseries.distribution, target_distroseries,
            cls.class_job_type, metadata)
        IMasterStore(PackageCopyJob).add(job)
        return cls(job)

    @classmethod
    def getActiveJobs(cls, target_archive):
        """See `IPackageCopyJobSource`."""
        return IStore(PackageCopyJob).find(
            PackageCopyJob,
            PackageCopyJob.job_type == cls.class_job_type,
            PackageCopyJob.target_archive == target_archive)

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
