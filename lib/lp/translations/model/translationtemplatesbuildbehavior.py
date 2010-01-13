# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""An `IBuildFarmJobBehavior` for `TranslationTemplatesBuildJob`.

Dispatches translation template build jobs to build-farm slaves.
"""

__metaclass__ = type
__all__ = [
    'TranslationTemplatesBuildBehavior',
    ]

import socket
import xmlrpclib

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces import ILaunchpadCelebrities

from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    IBuildFarmJobBehavior)
from lp.buildmaster.model.buildfarmjobbehavior import (
    BuildFarmJobBehaviorBase)
from lp.buildmaster.interfaces.builder import BuildSlaveFailure
from lp.translations.interfaces.translationtemplatesbuildjob import (
    ITranslationTemplatesBuildJobSource)


class TranslationTemplatesBuildBehavior(BuildFarmJobBehaviorBase):
    """Dispatches `TranslationTemplateBuildJob`s to slaves."""
    implements(IBuildFarmJobBehavior)

    # Identify the type of job to the slave.
    build_type = 'translation-templates'

    def dispatchBuildToSlave(self, build_queue_item, logger):
        """See `IBuildFarmJobBehavior`."""
        # XXX JeroenVermeulen 2009-12-24 bug=500110: This method is not
        # covered by tests yet.  Either unify it with Soyuz code into a
        # generalised method, or test it.
        templatesbuildjob = self._findTranslationTemplatesBuildJob(
            build_queue_item)
        chroot = self._getChroot()
        chroot_sha1 = chroot.content.sha1
        self._builder.cacheFileOnSlave(logger, chroot)
        buildid = templatesbuildjob.getName()

        args = { 'branch_url': build_queue_item.branch.url }
        filemap = {}

        try:
            status, info = self._builder.slave.build(
                buildid, self.build_type, chroot_sha1, filemap, args)
        except xmlrpclib.Fault, info:
            # Mark builder as 'failed'.
            logger.debug(
                "Disabling builder: %s" % self._builder.url, exc_info=1)
            self._builder.failBuilder(
                "Exception (%s) when setting up to new job" % info)
            raise BuildSlaveFailure
        except socket.error, info:
            error_message = "Exception (%s) when setting up new job" % info
            self._builder.handleTimeout(logger, error_message)
            raise BuildSlaveFailure

    def _getChroot(self):
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        return ubuntu.currentseries.nominatedarchindep.getChroot()

    def _findTranslationTemplatesBuildJob(self, build_queue_item):
        """Find the `TranslationTemplatesBuildJob` for a job.

        :param build_queue_item: A `BuildQueue` entry.
        :return: The matching `TranslationTemplatesBuildJob`.
        """
        jobsource = getUtility(ITranslationTemplatesBuildJobSource)
        return jobsource.getForJob(build_queue_item.job)
