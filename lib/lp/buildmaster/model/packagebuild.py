# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'PackageBuild',
    'PackageBuildDerived',
    'PackageBuildSet',
    ]


import datetime
import logging
import os.path
import subprocess

from lazr.delegates import delegates
import pytz
from storm.expr import Desc
from storm.locals import Int, Reference, Storm, Unicode
from zope.component import getUtility
from zope.interface import classProvides, implements
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.database.enumcol import DBEnum
from canonical.database.sqlbase import (
    clear_current_connection_cache, cursor, flush_database_updates)
from canonical.launchpad.browser.librarian import (
    ProxiedLibraryFileAlias)
from canonical.launchpad.interfaces.lpstorm import IMasterStore
from canonical.launchpad.webapp.interfaces import (
        IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from canonical.librarian.utils import copy_and_close

from lp.buildmaster.interfaces.buildbase import (BUILDD_MANAGER_LOG_NAME,
    BuildStatus)
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJobSource
from lp.buildmaster.interfaces.packagebuild import (
    IPackageBuild, IPackageBuildSet, IPackageBuildSource)
from lp.buildmaster.model.buildbase import BuildBase
from lp.buildmaster.model.buildfarmjob import (
    BuildFarmJob, BuildFarmJobDerived)
from lp.registry.interfaces.pocket import (
    PackagePublishingPocket, pocketsuffix)
from lp.soyuz.adapters.archivedependencies import (
    default_component_dependency_name)
from lp.soyuz.interfaces.component import IComponentSet


UPLOAD_LOG_FILENAME = 'uploader.log'


class PackageBuild(BuildFarmJobDerived, Storm):
    """An implementation of `IBuildFarmJob` for package builds."""

    __storm_table__ = 'PackageBuild'

    implements(IPackageBuild)
    classProvides(IPackageBuildSource)

    id = Int(primary=True)

    archive_id = Int(name='archive', allow_none=False)
    archive = Reference(archive_id, 'Archive.id')

    pocket = DBEnum(
        name='pocket', allow_none=False,
        enum=PackagePublishingPocket)

    upload_log_id = Int(name='upload_log', allow_none=True)
    upload_log = Reference(upload_log_id, 'LibraryFileAlias.id')

    dependencies = Unicode(name='dependencies', allow_none=True)

    build_farm_job_id = Int(name='build_farm_job', allow_none=False)
    build_farm_job = Reference(build_farm_job_id, 'BuildFarmJob.id')

    policy_name = 'buildd'

    # The following two properties are part of the IPackageBuild
    # interface, but need to be provided by derived classes.
    distribution = None
    distro_series = None

    def __init__(self, build_farm_job, archive, pocket,
                 dependencies=None):
        """Construct a PackageBuild."""
        super(PackageBuild, self).__init__()
        self.build_farm_job = build_farm_job
        self.archive = archive
        self.pocket = pocket
        self.dependencies = dependencies

    @classmethod
    def new(cls, job_type, virtualized, archive, pocket,
            processor=None, status=BuildStatus.NEEDSBUILD, dependencies=None,
            date_created=None):
        """See `IPackageBuildSource`."""
        store = IMasterStore(PackageBuild)

        # Create the BuildFarmJob to which the new PackageBuild
        # will delegate.
        build_farm_job = getUtility(IBuildFarmJobSource).new(
            job_type, status, processor, virtualized, date_created)

        package_build = cls(build_farm_job, archive, pocket, dependencies)
        store.add(package_build)
        return package_build

    @property
    def current_component(self):
        """See `IPackageBuild`."""
        return getUtility(IComponentSet)[default_component_dependency_name]

    @property
    def upload_log_url(self):
        """See `IPackageBuild`."""
        if self.upload_log is None:
            return None
        return ProxiedLibraryFileAlias(self.upload_log, self).http_url

    @property
    def log_url(self):
        """See `IBuildFarmJob`."""
        if self.log is None:
            return None
        return ProxiedLibraryFileAlias(self.log, self).http_url

    @property
    def is_private(self):
        """See `IBuildFarmJob`"""
        return self.archive.private

    def getUploadDirLeaf(self, build_cookie, now=None):
        """See `IPackageBuild`."""
        # UPLOAD_LEAF: <TIMESTAMP>-<BUILD-COOKIE>
        if now is None:
            now = datetime.datetime.now()
        return '%s-%s' % (now.strftime("%Y%m%d-%H%M%S"), build_cookie)

    def getUploadDir(self, upload_leaf):
        """See `IPackageBuild`."""
        return os.path.join(config.builddmaster.root, 'incoming', upload_leaf)

    @staticmethod
    def getUploaderCommand(package_build, upload_leaf, upload_logfilename):
        """See `IPackageBuild`."""
        root = os.path.abspath(config.builddmaster.root)
        uploader_command = list(config.builddmaster.uploader.split())

        # add extra arguments for processing a binary upload
        extra_args = [
            "--log-file", "%s" % upload_logfilename,
            "-d", "%s" % package_build.distribution.name,
            "-s", "%s" % (package_build.distro_series.name +
                          pocketsuffix[package_build.pocket]),
            "-b", "%s" % package_build.id,
            "-J", "%s" % upload_leaf,
            '--context=%s' % package_build.policy_name,
            "%s" % root,
            ]

        uploader_command.extend(extra_args)
        return uploader_command

    @staticmethod
    def getLogFromSlave(package_build):
        """See `IPackageBuild`."""
        builder = package_build.buildqueue_record.builder
        return builder.transferSlaveFileToLibrarian(
            'buildlog', package_build.buildqueue_record.getLogFileName(),
            package_build.is_private)

    @staticmethod
    def getUploadLogContent(root, leaf):
        """See `IPackageBuild`."""
        return BuildBase.getUploadLogContent(root, leaf)

    def estimateDuration(self):
        """See `IPackageBuild`."""
        raise NotImplementedError

    @staticmethod
    def storeBuildInfo(build, librarian, slave_status):
        """See `IPackageBuild`."""
        naked_build = removeSecurityProxy(build)
        naked_build.log = build.getLogFromSlave(build)
        naked_build.builder = build.buildqueue_record.builder
        # XXX cprov 20060615 bug=120584: Currently buildduration includes
        # the scanner latency, it should really be asking the slave for
        # the duration spent building locally.
        naked_build.date_finished = datetime.datetime.now(pytz.UTC)
        if slave_status.get('dependencies') is not None:
            build.dependencies = unicode(slave_status.get('dependencies'))
        else:
            build.dependencies = None

    def verifySuccessfulUpload(self):
        """See `IPackageBuild`."""
        raise NotImplementedError

    def storeUploadLog(self, content):
        """See `IPackageBuild`."""
        filename = "upload_%s_log.txt" % self.build_farm_job.id
        library_file = BuildBase.createUploadLog(
            self, content, filename=filename)
        self.upload_log = library_file

    def notify(self, extra_info=None):
        """See `IPackageBuild`."""
        raise NotImplementedError

    def handleStatus(self, status, librarian, slave_status):
        """See `IPackageBuild`."""
        raise NotImplementedError

    def queueBuild(self, suspended=False):
        """See `IPackageBuild`."""
        raise NotImplementedError


class PackageBuildDerived:
    """Setup the delegation for package build.

    This class also provides some common implementation for handling
    build status.
    """
    delegates(IPackageBuild, context="package_build")

    @staticmethod
    def getUploadLogContent(root, leaf):
        """Retrieve the upload log contents.

        :param root: Root directory for the uploads
        :param leaf: Leaf for this particular upload
        :return: Contents of log file or message saying no log file was found.
        """
        # Retrieve log file content.
        possible_locations = (
            'failed', 'failed-to-move', 'rejected', 'accepted')
        for location_dir in possible_locations:
            log_filepath = os.path.join(root, location_dir, leaf,
                UPLOAD_LOG_FILENAME)
            if os.path.exists(log_filepath):
                with open(log_filepath, 'r') as uploader_log_file:
                    return uploader_log_file.read()
        else:
            return 'Could not find upload log file'

    def queueBuild(self, suspended=False):
        """See `IPackageBuild`."""
        return BuildBase.queueBuild(self, suspended=suspended)

    def handleStatus(self, status, librarian, slave_status):
        """See `IPackageBuild`."""
        logger = logging.getLogger(BUILDD_MANAGER_LOG_NAME)
        method = getattr(self, '_handleStatus_' + status, None)
        if method is None:
            logger.critical("Unknown BuildStatus '%s' for builder '%s'"
                            % (status, self.buildqueue_record.builder.url))
            return
        method(librarian, slave_status, logger)

    # The following private handlers currently re-use the BuildBase
    # implementation until it is no longer in use. If we find in the
    # future that it would be useful to delegate these also, they can be
    # added to IBuildFarmJob or IPackageBuild as necessary.
    def _handleStatus_OK(self, librarian, slave_status, logger):
        """Handle a package that built successfully.

        Once built successfully, we pull the files, store them in a
        directory, store build information and push them through the
        uploader.
        """
        filemap = slave_status['filemap']

        logger.info("Processing successful build %s from builder %s" % (
            self.buildqueue_record.specific_job.build.title,
            self.buildqueue_record.builder.name))
        # Explode before collect a binary that is denied in this
        # distroseries/pocket
        if not self.archive.allowUpdatesToReleasePocket():
            assert self.distro_series.canUploadToPocket(self.pocket), (
                "%s (%s) can not be built for pocket %s: illegal status"
                % (self.title, self.id, self.pocket.name))

        # ensure we have the correct build root as:
        # <BUILDMASTER_ROOT>/incoming/<UPLOAD_LEAF>/<TARGET_PATH>/[FILES]
        root = os.path.abspath(config.builddmaster.root)

        # create a single directory to store build result files
        upload_leaf = self.getUploadDirLeaf(
            '%s-%s' % (self.id, self.buildqueue_record.id))
        upload_dir = self.getUploadDir(upload_leaf)
        logger.debug("Storing build result at '%s'" % upload_dir)

        # Build the right UPLOAD_PATH so the distribution and archive
        # can be correctly found during the upload:
        #       <archive_id>/distribution_name
        # for all destination archive types.
        archive = self.archive
        distribution_name = self.distribution.name
        target_path = '%s/%s' % (archive.id, distribution_name)
        upload_path = os.path.join(upload_dir, target_path)
        os.makedirs(upload_path)

        slave = removeSecurityProxy(self.buildqueue_record.builder.slave)
        successful_copy_from_slave = True
        for filename in filemap:
            logger.info("Grabbing file: %s" % filename)
            out_file_name = os.path.join(upload_path, filename)
            # If the evaluated output file name is not within our
            # upload path, then we don't try to copy this or any
            # subsequent files.
            if not os.path.realpath(out_file_name).startswith(upload_path):
                successful_copy_from_slave = False
                logger.warning(
                    "A slave tried to upload the file '%s' "
                    "for the build %d." % (filename, self.id))
                break
            out_file = open(out_file_name, "wb")
            slave_file = slave.getFile(filemap[filename])
            copy_and_close(slave_file, out_file)

        # We only attempt the upload if we successfully copied all the
        # files from the slave.
        if successful_copy_from_slave:
            uploader_logfilename = os.path.join(
                upload_dir, UPLOAD_LOG_FILENAME)
            uploader_command = self.getUploaderCommand(
                self, upload_leaf, uploader_logfilename)
            logger.debug("Saving uploader log at '%s'" % uploader_logfilename)

            logger.info("Invoking uploader on %s" % root)
            logger.info("%s" % uploader_command)

            uploader_process = subprocess.Popen(
                uploader_command, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)

            # Nothing should be written to the stdout/stderr.
            upload_stdout, upload_stderr = uploader_process.communicate()

            # XXX cprov 2007-04-17: we do not check uploader_result_code
            # anywhere. We need to find out what will be best strategy
            # when it failed HARD (there is a huge effort in process-upload
            # to not return error, it only happen when the code is broken).
            uploader_result_code = uploader_process.returncode
            logger.info("Uploader returned %d" % uploader_result_code)

        # Quick and dirty hack to carry on on process-upload failures
        if os.path.exists(upload_dir):
            logger.warning("The upload directory did not get moved.")
            failed_dir = os.path.join(root, "failed-to-move")
            if not os.path.exists(failed_dir):
                os.mkdir(failed_dir)
            os.rename(upload_dir, os.path.join(failed_dir, upload_leaf))

        # The famous 'flush_updates + clear_cache' will make visible
        # the DB changes done in process-upload, considering that the
        # transaction was set with ISOLATION_LEVEL_READ_COMMITED
        # isolation level.
        cur = cursor()
        cur.execute('SHOW transaction_isolation')
        isolation_str = cur.fetchone()[0]
        assert isolation_str == 'read committed', (
            'BuildMaster/BuilderGroup transaction isolation should be '
            'ISOLATION_LEVEL_READ_COMMITTED (not "%s")' % isolation_str)

        original_slave = self.buildqueue_record.builder.slave

        # XXX Robert Collins, Celso Providelo 2007-05-26 bug=506256:
        # 'Refreshing' objects  procedure  is forced on us by using a
        # different process to do the upload, but as that process runs
        # in the same unix account, it is simply double handling and we
        # would be better off to do it within this process.
        flush_database_updates()
        clear_current_connection_cache()

        # XXX cprov 2007-06-15: Re-issuing removeSecurityProxy is forced on
        # us by sqlobject refreshing the builder object during the
        # transaction cache clearing. Once we sort the previous problem
        # this step should probably not be required anymore.
        self.buildqueue_record.builder.setSlaveForTesting(
            removeSecurityProxy(original_slave))

        # Store build information, build record was already updated during
        # the binary upload.
        self.storeBuildInfo(self, librarian, slave_status)

        # Retrive the up-to-date build record and perform consistency
        # checks. The build record should be updated during the binary
        # upload processing, if it wasn't something is broken and needs
        # admins attention. Even when we have a FULLYBUILT build record,
        # if it is not related with at least one binary, there is also
        # a problem.
        # For both situations we will mark the builder as FAILEDTOUPLOAD
        # and the and update the build details (datebuilt, duration,
        # buildlog, builder) in LP. A build-failure-notification will be
        # sent to the lp-build-admin celebrity and to the sourcepackagerelease
        # uploader about this occurrence. The failure notification will
        # also contain the information required to manually reprocess the
        # binary upload when it was the case.
        if (self.status != BuildStatus.FULLYBUILT or
            not successful_copy_from_slave or
            not self.verifySuccessfulUpload()):
            logger.warning("Build %s upload failed." % self.id)
            self.status = BuildStatus.FAILEDTOUPLOAD
            uploader_log_content = self.getUploadLogContent(root,
                upload_leaf)
            # Store the upload_log_contents in librarian so it can be
            # accessed by anyone with permission to see the build.
            self.storeUploadLog(uploader_log_content)
            # Notify the build failure.
            self.notify(extra_info=uploader_log_content)
        else:
            logger.info(
                "Gathered %s %d completely" % (
                self.__class__.__name__, self.id))

        # Release the builder for another job.
        self.buildqueue_record.builder.cleanSlave()
        # Remove BuildQueue record.
        self.buildqueue_record.destroySelf()

    def _handleStatus_PACKAGEFAIL(self, librarian, slave_status, logger):
        return BuildBase._handleStatus_PACKAGEFAIL(
            self, librarian, slave_status, logger)

    def _handleStatus_DEPFAIL(self, librarian, slave_status, logger):
        return BuildBase._handleStatus_DEPFAIL(
            self, librarian, slave_status, logger)

    def _handleStatus_CHROOTFAIL(self, librarian, slave_status, logger):
        return BuildBase._handleStatus_CHROOTFAIL(
            self, librarian, slave_status, logger)

    def _handleStatus_BUILDERFAIL(self, librarian, slave_status, logger):
        return BuildBase._handleStatus_BUILDERFAIL(
            self, librarian, slave_status, logger)

    def _handleStatus_GIVENBACK(self, librarian, slave_status, logger):
        return BuildBase._handleStatus_GIVENBACK(
            self, librarian, slave_status, logger)


class PackageBuildSet:
    implements(IPackageBuildSet)

    def getBuildsForArchive(self, archive, status=None, pocket=None):
        """See `IPackageBuildSet`."""

        extra_exprs = []

        if status is not None:
            extra_exprs.append(BuildFarmJob.status == status)

        if pocket:
            extra_exprs.append(PackageBuild.pocket == pocket)

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        result_set = store.find(PackageBuild,
            PackageBuild.archive == archive,
            PackageBuild.build_farm_job == BuildFarmJob.id,
            *extra_exprs)

        # When we have a set of builds that may include pending or
        # superseded builds, we order by -date_created (as we won't
        # always have a date_finished). Otherwise we can order by
        # -date_finished.
        unfinished_states = [
            BuildStatus.NEEDSBUILD,
            BuildStatus.BUILDING,
            BuildStatus.SUPERSEDED]
        if status is None or status in unfinished_states:
            result_set.order_by(
                Desc(BuildFarmJob.date_created), BuildFarmJob.id)
        else:
            result_set.order_by(
                Desc(BuildFarmJob.date_finished), BuildFarmJob.id)

        return result_set
