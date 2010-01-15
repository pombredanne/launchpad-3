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

from canonical.launchpad.interfaces import ILaunchpadCelebrities

from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    IBuildFarmJobBehavior)
from lp.buildmaster.model.buildfarmjobbehavior import (
    BuildFarmJobBehaviorBase)


class TranslationTemplatesBuildBehavior(BuildFarmJobBehaviorBase):
    """Dispatches `TranslationTemplateBuildJob`s to slaves."""
    implements(IBuildFarmJobBehavior)

    # Identify the type of job to the slave.
    build_type = 'translation-templates'

    def dispatchBuildToSlave(self, build_queue_item, logger):
        """See `IBuildFarmJobBehavior`."""
        chroot = self._getChroot()
        chroot_sha1 = chroot.content.sha1
        self._builder.slave.cacheFile(logger, chroot)
        buildid = self.buildfarmjob.getName()

        args = { 'branch_url': self.buildfarmjob.branch.url }
        filemap = {}

        status, info = self._builder.slave.build(
            buildid, self.build_type, chroot_sha1, filemap, args)

    def _getChroot(self):
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        return ubuntu.currentseries.nominatedarchindep.getChroot()

    def logStartBuild(self, logger):
        """See `IBuildFarmJobBehavior`."""
        logger.info("Starting templates build.")
