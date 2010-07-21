# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""An `IBuildFarmJobBehavior` for `TranslationTemplatesBuildJob`.

Dispatches translation template build jobs to build-farm slaves.
"""

__metaclass__ = type
__all__ = [
    'TranslationTemplatesBuildBehavior',
    ]

from zope.component import getUtility
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces import ILaunchpadCelebrities

from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    IBuildFarmJobBehavior)
from lp.buildmaster.model.buildfarmjobbehavior import (
    BuildFarmJobBehaviorBase)
from lp.registry.interfaces.productseries import IProductSeriesSet
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue)
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
        self._builder.slave.cacheFile(logger, chroot)
        cookie = self.buildfarmjob.generateSlaveBuildCookie()

        args = self.buildfarmjob.metadata
        filemap = {}

        self._builder.slave.build(
            cookie, self.build_type, chroot_sha1, filemap, args)

    def _getChroot(self):
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        return ubuntu.currentseries.nominatedarchindep.getChroot()

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
            return None

        slave_filename = filemap.get(self.templates_tarball_path)
        if slave_filename is None:
            logger.error("Did not find templates tarball in slave output.")
            return None

        slave = removeSecurityProxy(buildqueue.builder.slave)
        return slave.getFile(slave_filename).read()

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

    def updateBuild_WAITING(self, queue_item, slave_status, logtail, logger):
        """Deal with a finished ("WAITING" state, perversely) build job.

        Retrieves tarball and logs from the slave, then cleans up the
        slave so it's ready for a next job and destroys the queue item.

        If this fails for whatever unforeseen reason, a future run will
        retry it.
        """
        build_status = self.extractBuildStatus(slave_status)

        logger.debug(
            "Templates generation job %s for %s finished with status %s." % (
            queue_item.specific_job.getName(),
            queue_item.specific_job.branch.bzr_identity,
            build_status))

        if build_status == 'OK':
            logger.debug("Processing successful templates build.")
            filemap = slave_status.get('filemap')
            tarball = self._readTarball(queue_item, filemap, logger)

            if tarball is None:
                logger.error("Build produced no tarball.")
            else:
                logger.debug("Uploading translation templates tarball.")
                self._uploadTarball(
                    queue_item.specific_job.branch, tarball, logger)
                logger.debug("Upload complete.")

        queue_item.builder.cleanSlave()
        queue_item.destroySelf()
