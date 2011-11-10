# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    "PackageCopyJob",
    "PlainPackageCopyJob",
    ]

import logging

from lazr.delegates import delegates
import simplejson
from storm.locals import (
    And,
    Int,
    JSON,
    Reference,
    Unicode,
    )
import transaction
from zope.component import getUtility
from zope.interface import (
    classProvides,
    implements,
    )
from zope.security.proxy import removeSecurityProxy

from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import sqlvalues
from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet,
    )
from canonical.launchpad.interfaces.lpstorm import (
    IMasterStore,
    IStore,
    )
from lp.app.errors import NotFoundError
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.registry.enum import DistroSeriesDifferenceStatus
from lp.registry.interfaces.distroseriesdifference import (
    IDistroSeriesDifferenceSource,
    )
from lp.registry.interfaces.distroseriesdifferencecomment import (
    IDistroSeriesDifferenceCommentSource,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.sourcepackagename import ISourcePackageNameSet
from lp.registry.model.distroseries import DistroSeries
from lp.services.database.stormbase import StormBase
from lp.services.job.interfaces.job import (
    JobStatus,
    SuspendJobException,
    )
from lp.services.job.model.job import Job
from lp.services.job.runner import BaseRunnableJob
from lp.soyuz.adapters.overrides import (
    FromExistingOverridePolicy,
    SourceOverride,
    UnknownOverridePolicy,
    )
from lp.soyuz.enums import PackageCopyPolicy
from lp.soyuz.interfaces.archive import CannotCopy
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.copypolicy import ICopyPolicy
from lp.soyuz.interfaces.packagecopyjob import (
    IPackageCopyJob,
    IPackageCopyJobSource,
    IPlainPackageCopyJob,
    IPlainPackageCopyJobSource,
    PackageCopyJobType,
    )
from lp.soyuz.interfaces.packagediff import PackageDiffAlreadyRequested
from lp.soyuz.interfaces.queue import IPackageUploadSet
from lp.soyuz.interfaces.section import ISectionSet
from lp.soyuz.model.archive import Archive
from lp.soyuz.scripts.packagecopier import do_copy


class PackageCopyJob(StormBase):
    """Base class for package copying jobs."""

    implements(IPackageCopyJob)
    classProvides(IPackageCopyJobSource)

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

    package_name = Unicode('package_name')
    copy_policy = EnumCol(enum=PackageCopyPolicy)

    job_type = EnumCol(enum=PackageCopyJobType, notNull=True)

    metadata = JSON('json_data')

    # Derived concrete classes.  The entire class gets one dict for
    # this; it's not meant to be on an instance.
    concrete_classes = {}

    @classmethod
    def registerConcreteClass(cls, new_class):
        """Register a concrete `IPackageCopyJob`-implementing class."""
        assert new_class.class_job_type not in cls.concrete_classes, (
            "Class %s is already registered." % new_class)
        cls.concrete_classes[new_class.class_job_type] = new_class

    @classmethod
    def wrap(cls, package_copy_job):
        """See `IPackageCopyJobSource`."""
        if package_copy_job is None:
            return None
        # Read job_type so You Don't Have To.  If any other code reads
        # job_type, that's probably a sign that the interfaces need more
        # work.
        job_type = removeSecurityProxy(package_copy_job).job_type
        concrete_class = cls.concrete_classes[job_type]
        return concrete_class(package_copy_job)

    @classmethod
    def getByID(cls, pcj_id):
        """See `IPackageCopyJobSource`."""
        return cls.wrap(IStore(PackageCopyJob).get(PackageCopyJob, pcj_id))

    def __init__(self, source_archive, target_archive, target_distroseries,
                 job_type, metadata, requester, package_name=None,
                 copy_policy=None):
        super(PackageCopyJob, self).__init__()
        self.job = Job()
        self.job.requester = requester
        self.job_type = job_type
        self.source_archive = source_archive
        self.target_archive = target_archive
        self.target_distroseries = target_distroseries
        self.package_name = unicode(package_name)
        self.copy_policy = copy_policy
        self.metadata = metadata

    @property
    def package_version(self):
        return self.metadata["package_version"]

    def extendMetadata(self, metadata_dict):
        """Add metadata_dict to the existing metadata."""
        existing = self.metadata
        existing.update(metadata_dict)
        self.metadata = existing

    @property
    def component_name(self):
        """See `IPackageCopyJob`."""
        return self.metadata.get("component_override")

    @property
    def section_name(self):
        """See `IPackageCopyJob`."""
        return self.metadata.get("section_override")


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
        job = IStore(PackageCopyJob).get(PackageCopyJob, job_id)
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

    @property
    def copy_policy(self):
        """See `PlainPackageCopyJob`."""
        return self.context.copy_policy


class PlainPackageCopyJob(PackageCopyJobDerived):
    """Job that copies a package from one archive to another."""
    # This job type serves in different places: it supports copying
    # packages between archives, but also the syncing of packages from
    # parents into a derived distroseries.  We may split these into
    # separate types at some point, but for now we (allenap, bigjools,
    # jtv) chose to keep it as one.

    implements(IPlainPackageCopyJob)

    class_job_type = PackageCopyJobType.PLAIN
    classProvides(IPlainPackageCopyJobSource)

    @classmethod
    def _makeMetadata(cls, target_pocket, package_version, include_binaries):
        """Produce a metadata dict for this job."""
        return {
            'target_pocket': target_pocket.value,
            'package_version': package_version,
            'include_binaries': bool(include_binaries),
        }

    @classmethod
    def create(cls, package_name, source_archive,
               target_archive, target_distroseries, target_pocket,
               include_binaries=False, package_version=None,
               copy_policy=PackageCopyPolicy.INSECURE, requester=None):
        """See `IPlainPackageCopyJobSource`."""
        assert package_version is not None, "No package version specified."
        assert requester is not None, "No requester specified."
        metadata = cls._makeMetadata(
            target_pocket, package_version, include_binaries)
        job = PackageCopyJob(
            job_type=cls.class_job_type,
            source_archive=source_archive,
            target_archive=target_archive,
            target_distroseries=target_distroseries,
            package_name=package_name,
            copy_policy=copy_policy,
            metadata=metadata,
            requester=requester)
        IMasterStore(PackageCopyJob).add(job)
        return cls(job)

    @classmethod
    def _composeJobInsertionTuple(cls, target_distroseries, copy_policy,
                                  include_binaries, job_id, copy_task):
        """Create an SQL fragment for inserting a job into the database.

        :return: A string representing an SQL tuple containing initializers
            for a `PackageCopyJob` in the database (minus `id`, which is
            assigned automatically).  Contents are escaped for use in SQL.
        """
        (
            package_name,
            package_version,
            source_archive,
            target_archive,
            target_pocket,
        ) = copy_task
        metadata = cls._makeMetadata(
            target_pocket, package_version, include_binaries)
        data = (
            cls.class_job_type, target_distroseries, copy_policy,
            source_archive, target_archive, package_name, job_id,
            simplejson.dumps(metadata, ensure_ascii=False))
        format_string = "(%s)" % ", ".join(["%s"] * len(data))
        return format_string % sqlvalues(*data)

    @classmethod
    def createMultiple(cls, target_distroseries, copy_tasks, requester,
                       copy_policy=PackageCopyPolicy.INSECURE,
                       include_binaries=False):
        """See `IPlainPackageCopyJobSource`."""
        store = IMasterStore(Job)
        job_ids = Job.createMultiple(store, len(copy_tasks), requester)
        job_contents = [
            cls._composeJobInsertionTuple(
                target_distroseries, copy_policy, include_binaries, job_id,
                task)
            for job_id, task in zip(job_ids, copy_tasks)]
        result = store.execute("""
            INSERT INTO PackageCopyJob (
                job_type,
                target_distroseries,
                copy_policy,
                source_archive,
                target_archive,
                package_name,
                job,
                json_data)
            VALUES %s
            RETURNING id
            """ % ", ".join(job_contents))
        return [job_id for job_id, in result]

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
            result.setdefault(job.package_name, job)
        return result

    @property
    def target_pocket(self):
        return PackagePublishingPocket.items[self.metadata['target_pocket']]

    @property
    def include_binaries(self):
        return self.metadata['include_binaries']

    def _createPackageUpload(self, unapproved=False):
        pu = self.target_distroseries.createQueueEntry(
            pocket=self.target_pocket, archive=self.target_archive,
            package_copy_job=self.context)
        if unapproved:
            pu.setUnapproved()

    def addSourceOverride(self, override):
        """Add an `ISourceOverride` to the metadata."""
        metadata_changes = {}
        if override.component is not None:
            metadata_changes['component_override'] = override.component.name
        if override.section is not None:
            metadata_changes['section_override'] = override.section.name
        self.context.extendMetadata(metadata_changes)

    def getSourceOverride(self):
        """Fetch an `ISourceOverride` from the metadata."""
        name = self.package_name
        component_name = self.component_name
        section_name = self.section_name
        source_package_name = getUtility(ISourcePackageNameSet)[name]
        try:
            component = getUtility(IComponentSet)[component_name]
        except NotFoundError:
            component = None
        try:
            section = getUtility(ISectionSet)[section_name]
        except NotFoundError:
            section = None

        return SourceOverride(source_package_name, component, section)

    def _checkPolicies(self, source_name, source_component=None):
        # This helper will only return if it's safe to carry on with the
        # copy, otherwise it raises SuspendJobException to tell the job
        # runner to suspend the job.
        override_policy = FromExistingOverridePolicy()
        ancestry = override_policy.calculateSourceOverrides(
            self.target_archive, self.target_distroseries,
            self.target_pocket, [source_name])

        copy_policy = self.getPolicyImplementation()

        if len(ancestry) == 0:
            # We need to get the default overrides and put them in the
            # metadata.
            defaults = UnknownOverridePolicy().calculateSourceOverrides(
                self.target_archive, self.target_distroseries,
                self.target_pocket, [source_name], source_component)
            self.addSourceOverride(defaults[0])

            approve_new = copy_policy.autoApproveNew(
                self.target_archive, self.target_distroseries,
                self.target_pocket)

            if not approve_new:
                # There's no existing package with the same name and the
                # policy says unapproved, so we poke it in the NEW queue.
                self._createPackageUpload()
                raise SuspendJobException
        else:
            # Put the existing override in the metadata.
            self.addSourceOverride(ancestry[0])

        # The package is not new (it has ancestry) so check the copy
        # policy for existing packages.
        approve_existing = copy_policy.autoApprove(
            self.target_archive, self.target_distroseries, self.target_pocket)
        if not approve_existing:
            self._createPackageUpload(unapproved=True)
            raise SuspendJobException

    def _rejectPackageUpload(self):
        # Helper to find and reject any associated PackageUpload.
        pu = getUtility(IPackageUploadSet).getByPackageCopyJobIDs(
            [self.context.id]).any()
        if pu is not None:
            pu.setRejected()

    def run(self):
        """See `IRunnableJob`."""
        try:
            self.attemptCopy()
        except CannotCopy, e:
            logger = logging.getLogger()
            logger.info("Job:\n%s\nraised CannotCopy:\n%s" % (self, e))
            self.abort()  # Abort the txn.
            self.reportFailure(e)

            # If there is an associated PackageUpload we need to reject it,
            # else it will sit in ACCEPTED forever.
            self._rejectPackageUpload()

            # Rely on the job runner to do the final commit.  Note that
            # we're not raising any exceptions here, failure of a copy is
            # not a failure of the job.
        except SuspendJobException:
            raise
        except:
            # Abort work done so far, but make sure that we commit the
            # rejection to the PackageUpload.
            transaction.abort()
            self._rejectPackageUpload()
            transaction.commit()
            raise

    def attemptCopy(self):
        """Attempt to perform the copy.

        :raise CannotCopy: If the copy fails for a reason that the user
            can deal with.
        """
        if self.target_archive.is_ppa:
            if self.target_pocket != PackagePublishingPocket.RELEASE:
                raise CannotCopy(
                    "Destination pocket must be 'release' for a PPA.")

        name = self.package_name
        version = self.package_version
        source_package = self.source_archive.getPublishedSources(
            name=name, version=version, exact_match=True).first()
        if source_package is None:
            raise CannotCopy("Package %r %r not found." % (name, version))
        source_name = getUtility(ISourcePackageNameSet)[name]

        # If there's a PackageUpload associated with this job then this
        # job has just been released by an archive admin from the queue.
        # We don't need to check any policies, but the admin may have
        # set overrides which we will get from the job's metadata.
        pu = getUtility(IPackageUploadSet).getByPackageCopyJobIDs(
            [self.context.id]).any()
        if pu is None:
            self._checkPolicies(
                source_name, source_package.sourcepackagerelease.component)

        # The package is free to go right in, so just copy it now.
        ancestry = self.target_archive.getPublishedSources(
            name=name, distroseries=self.target_distroseries,
            pocket=self.target_pocket, exact_match=True).first()
        override = self.getSourceOverride()
        copy_policy = self.getPolicyImplementation()
        send_email = copy_policy.send_email(self.target_archive)
        copied_sources = do_copy(
            sources=[source_package], archive=self.target_archive,
            series=self.target_distroseries, pocket=self.target_pocket,
            include_binaries=self.include_binaries, check_permissions=True,
            person=self.requester, overrides=[override],
            send_email=send_email, announce_from_person=self.requester)

        # Add a PackageDiff for this new upload if it has ancestry.
        if ancestry is not None:
            to_sourcepackagerelease = ancestry.sourcepackagerelease
            copied_source = copied_sources[0]
            try:
                diff = to_sourcepackagerelease.requestDiffTo(
                    self.requester, copied_source.sourcepackagerelease)
            except PackageDiffAlreadyRequested:
                pass

        if pu is not None:
            # A PackageUpload will only exist if the copy job had to be
            # held in the queue because of policy/ancestry checks.  If one
            # does exist we need to make sure it gets moved to DONE.
            pu.setDone()

    def abort(self):
        """Abort work."""
        transaction.abort()

    def findMatchingDSDs(self):
        """Find any `DistroSeriesDifference`s that this job might resolve."""
        dsd_source = getUtility(IDistroSeriesDifferenceSource)
        target_series = self.target_distroseries
        candidates = dsd_source.getForDistroSeries(
            distro_series=target_series, name_filter=self.package_name,
            status=DistroSeriesDifferenceStatus.NEEDS_ATTENTION)

        # The job doesn't know what distroseries a given package is
        # coming from, and the version number in the DSD may have
        # changed.  We can however filter out DSDs that are from
        # different distributions, based on the job's target archive.
        source_distro_id = self.source_archive.distributionID
        return [
            dsd
            for dsd in candidates
                if dsd.parent_series.distributionID == source_distro_id]

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
        if self.package_name is None:
            parts.append(" no package (!)")
        else:
            parts.append(" package %s" % self.package_name)
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

    def getPolicyImplementation(self):
        """Return the `ICopyPolicy` applicable to this job."""
        return ICopyPolicy(self.copy_policy)


PackageCopyJob.registerConcreteClass(PlainPackageCopyJob)
