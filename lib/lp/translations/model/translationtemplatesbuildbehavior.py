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
from lp.translations.model.translationtemplatesbuildjob import (
    TranslationTemplatesBuildJob)


class TranslationTemplatesBuildBehavior(BuildFarmJobBehaviorBase):
    """Dispatches `TranslationTemplateBuildJob`s to slaves."""
    implements(IBuildFarmJobBehavior)

    # Identify the type of job to the slave.
    build_type = 'translation-templates'

    def dispatchBuildToSlave(self, build_queue_item, logger):
        """See `IBuildFarmJobBehavior`."""
        templatesbuildjob = self._findTranslationTemplatesBuildJob(
            build_queue_item)
        chroot = self._getChroot()
        chroot_sha1 = chroot.content.sha1
# XXX: API change in lp:~jml/launchpad/behavior-refactor
        self._builder.cacheFileOnSlave(logger, chroot)
        buildid = templatesbuildjob.getName()

        args = { 'branch_url': templatesbuildjob.branch.url }
        filemap = {}

# XXX: API change in lp:~jml/launchpad/behavior-refactor
        status, info = self._builder.slave.build(
            buildid, self.build_type, chroot_sha1, filemap, args)

    def _getChroot(self):
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        return ubuntu.currentseries.nominatedarchindep.getChroot()

    def _findTranslationTemplatesBuildJob(self, build_queue_item):
        """Find the `TranslationTemplatesBuildJob` for a job.

        :param build_queue_item: A `BuildQueue` entry.
        :return: The matching `TranslationTemplatesBuildJob`.
        """
        return TranslationTemplatesBuildJob.getByJob(build_queue_item.job)

    def logStartBuild(self, build_queue_item, logger):
        """See `IBuildFarmJobBehavior`."""
        specific_job = TranslationTemplatesBuildJob.getByJob(
            build_queue_item.job)
        logger.info("Start templates build for %s" % specific_job.branch.name)
