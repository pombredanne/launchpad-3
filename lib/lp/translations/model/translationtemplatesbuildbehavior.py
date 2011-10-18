# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""An `IBuildFarmJobBehavior` for `TranslationTemplatesBuildJob`.

Dispatches translation template build jobs to build-farm slaves.
"""

__metaclass__ = type
__all__ = [
    'TranslationTemplatesBuildBehavior',
    ]

import datetime
import os
import pytz
import tempfile

from twisted.internet import defer
from zope.component import getUtility
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    IBuildFarmJobBehavior,
    )
from lp.buildmaster.model.buildfarmjobbehavior import BuildFarmJobBehaviorBase
from lp.registry.interfaces.productseries import IProductSeriesSet
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue,
    )
from lp.translations.model.approver import TranslationBuildApprover


class TranslationTemplatesBuildBehavior(BuildFarmJobBehaviorBase):
    """Dispatches `TranslationTemplateBuildJob`s to slaves."""
    implements(IBuildFarmJobBehavior)

    # Identify the type of job to the slave.
    build_type = 'translation-templates'

    # Filename for the tarball of templates that the slave builds.
    templates_tarball_path = 'translation-templates.tar.gz'

    def dispatchBuildToSlave(self, build_queue_item, logger):
        """See `IBuildFarmJobBehavior`."""
        chroot = self._getChroot()
        chroot_sha1 = chroot.content.sha1
        d = self._builder.slave.cacheFile(logger, chroot)

        def got_cache_file(ignored):
            cookie = self.buildfarmjob.generateSlaveBuildCookie()

            args = {
                'arch_tag': self._getDistroArchSeries().architecturetag,
                'branch_url': self.buildfarmjob.branch.composePublicURL(),
                }

            filemap = {}

            return self._builder.slave.build(
                cookie, self.build_type, chroot_sha1, filemap, args)
        return d.addCallback(got_cache_file)

    def _getChroot(self):
        return self._getDistroArchSeries().getChroot()

    def _getDistroArchSeries(self):
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        return ubuntu.currentseries.nominatedarchindep

    def logStartBuild(self, logger):
        """See `IBuildFarmJobBehavior`."""
        logger.info(
            "Starting templates build %s for %s." % (
            self.buildfarmjob.getName(),
            self.buildfarmjob.branch.bzr_identity))

    def _readTarball(self, buildqueue, filemap, logger):
        """Read tarball with generated translation templates from slave."""
        if filemap is None:
            logger.error("Slave returned no filemap.")
            return defer.succeed(None)

        slave_filename = filemap.get(self.templates_tarball_path)
        if slave_filename is None:
            logger.error("Did not find templates tarball in slave output.")
            return defer.succeed(None)

        slave = removeSecurityProxy(buildqueue.builder.slave)

        fd, fname = tempfile.mkstemp()
        tarball_file = os.fdopen(fd, 'wb')
        d = slave.getFile(slave_filename, tarball_file)
        # getFile will close the file object.
        return d.addCallback(lambda ignored: fname)

    def _uploadTarball(self, branch, tarball, logger):
        """Upload tarball to productseries that want it."""
        queue = getUtility(ITranslationImportQueue)
        productseriesset = getUtility(IProductSeriesSet)
        related_series = (
            productseriesset.findByTranslationsImportBranch(branch))
        for series in related_series:
            queue.addOrUpdateEntriesFromTarball(
                tarball, False, branch.owner, productseries=series,
                approver_factory=TranslationBuildApprover)

    def updateSlaveStatus(self, raw_slave_status, status):
        """See `IBuildFarmJobBehavior`."""
        if status['builder_status'] == 'BuilderStatus.WAITING':
            if len(raw_slave_status) >= 4:
                status['filemap'] = raw_slave_status[3]

    def setBuildStatus(self, status):
        self.build.status = status

    @staticmethod
    def getLogFromSlave(templates_build, queue_item):
        """See `IPackageBuild`."""
        SLAVE_LOG_FILENAME = 'buildlog'
        builder = queue_item.builder
        d = builder.transferSlaveFileToLibrarian(
            SLAVE_LOG_FILENAME,
            templates_build.buildfarmjob.getLogFileName(),
            False)
        return d

    @staticmethod
    def storeBuildInfo(build, queue_item, build_status):
        """See `IPackageBuild`."""
        def got_log(lfa_id):
            build.build.log = lfa_id
            build.build.builder = queue_item.builder
            build.build.date_started = queue_item.date_started
            # XXX cprov 20060615 bug=120584: Currently buildduration includes
            # the scanner latency, it should really be asking the slave for
            # the duration spent building locally.
            build.build.date_finished = datetime.datetime.now(pytz.UTC)

        d = build.getLogFromSlave(build, queue_item)
        return d.addCallback(got_log)

    def updateBuild_WAITING(self, queue_item, slave_status, logtail, logger):
        """Deal with a finished ("WAITING" state, perversely) build job.

        Retrieves tarball and logs from the slave, then cleans up the
        slave so it's ready for a next job and destroys the queue item.

        If this fails for whatever unforeseen reason, a future run will
        retry it.
        """
        build_status = self.extractBuildStatus(slave_status)

        logger.info(
            "Templates generation job %s for %s finished with status %s." % (
            queue_item.specific_job.getName(),
            queue_item.specific_job.branch.bzr_identity,
            build_status))

        def clean_slave(ignored):
            d = queue_item.builder.cleanSlave()
            return d.addCallback(lambda ignored: queue_item.destroySelf())

        def got_tarball(filename):
            # XXX 2010-11-12 bug=674575
            # Please make addOrUpdateEntriesFromTarball() take files on
            # disk; reading arbitrarily sized files into memory is
            # dangerous.
            if filename is None:
                logger.error("Build produced no tarball.")
                return

            tarball_file = open(filename)
            try:
                tarball = tarball_file.read()
                if tarball is None:
                    logger.error("Build produced empty tarball.")
                else:
                    logger.debug("Uploading translation templates tarball.")
                    self._uploadTarball(
                        queue_item.specific_job.branch, tarball, logger)
                    logger.debug("Upload complete.")
            finally:
                self.setBuildStatus(BuildStatus.FULLYBUILT)
                tarball_file.close()
                os.remove(filename)

        def build_info_stored(ignored):
            if build_status == 'OK':
                self.setBuildStatus(BuildStatus.UPLOADING)
                logger.debug("Processing successful templates build.")
                filemap = slave_status.get('filemap')
                d = self._readTarball(queue_item, filemap, logger)
                d.addCallback(got_tarball)
                d.addCallback(clean_slave)
                return d

            self.setBuildStatus(BuildStatus.FAILEDTOBUILD)
            return clean_slave(None)

        d = self.storeBuildInfo(self, queue_item, build_status)
        d.addCallback(build_info_stored)
        return d
