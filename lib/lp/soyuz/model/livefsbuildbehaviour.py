# Copyright 2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""An `IBuildFarmJobBehaviour` for `LiveFSBuild`.

Dispatches live filesystem build jobs to build-farm slaves.
"""

__metaclass__ = type
__all__ = [
    'LiveFSBuildBehaviour',
    ]

from twisted.internet import defer
from zope.component import adapts
from zope.interface import implements

from lp.buildmaster.interfaces.builder import CannotBuild
from lp.buildmaster.interfaces.buildfarmjobbehaviour import (
    IBuildFarmJobBehaviour,
    )
from lp.buildmaster.model.buildfarmjobbehaviour import (
    BuildFarmJobBehaviourBase,
    )
from lp.soyuz.adapters.archivedependencies import get_sources_list_for_building
from lp.soyuz.interfaces.livefsbuild import ILiveFSBuild


class LiveFSBuildBehaviour(BuildFarmJobBehaviourBase):
    """Dispatches `LiveFSBuild` jobs to slaves."""

    adapts(ILiveFSBuild)
    implements(IBuildFarmJobBehaviour)

    # Identify the type of job to the slave.
    build_type = 'livefs'

    @property
    def displayname(self):
        ret = self.build.title
        if self._builder is not None:
            ret += " (on %s)" % self._builder.url
        return ret

    def logStartBuild(self, logger):
        """See `IBuildFarmJobBehaviour`."""
        logger.info("startBuild(%s)", self.displayname)

    def getLogFileName(self):
        das = self.build.distroarchseries
        archname = das.architecturetag
        if self.build.unique_key:
            archname += '_%s' % self.build.unique_key

        # Examples:
        #   buildlog_ubuntu_trusty_i386_ubuntu-desktop_FULLYBUILT.txt
        return 'buildlog_%s_%s_%s_%s_%s.txt' % (
            das.distroseries.distribution.name, das.distroseries.name,
            archname, self.build.livefs.name, self.build.status.name)

    def verifyBuildRequest(self, logger):
        """Assert some pre-build checks.

        The build request is checked:
         * Virtualized builds can't build on a non-virtual builder
         * Ensure that we have a chroot
        """
        build = self.build
        if build.is_virtualized and not self._builder.virtualized:
            raise AssertionError(
                "Attempt to build virtual item on a non-virtual builder.")

        chroot = build.distroarchseries.getChroot()
        if chroot is None:
            raise CannotBuild(
                "Missing chroot for %s" % build.distroarchseries.displayname)

    def _extraBuildArgs(self):
        """
        Return the extra arguments required by the slave for the given build.
        """
        build = self.build
        args = dict(build.livefs.metadata)
        args.update(build.metadata_override)
        args["suite"] = build.distroarchseries.distroseries.getSuite(
            build.pocket)
        args["arch_tag"] = build.distroarchseries.architecturetag
        args["datestamp"] = build.version
        args["archives"] = get_sources_list_for_building(
            build, build.distroarchseries, None)
        args["archive_private"] = build.archive.private
        return args

    @defer.inlineCallbacks
    def dispatchBuildToSlave(self, build_queue_id, logger):
        """See `IBuildFarmJobBehaviour`."""

        # Start the build on the slave builder.  First we send the chroot.
        distroarchseries = self.build.distroarchseries
        chroot = distroarchseries.getChroot()
        if chroot is None:
            raise CannotBuild(
                "Unable to find a chroot for %s" %
                distroarchseries.displayname)
        logger.info(
            "Sending chroot file for live filesystem build to %s" %
            self._builder.name)
        yield self._slave.cacheFile(logger, chroot)

        # Generate a string which can be used to cross-check when obtaining
        # results so we know we are referring to the right database object
        # in subsequent runs.
        buildid = "%s-%s" % (self.build.id, build_queue_id)
        logger.info("Initiating build %s on %s" % (buildid, self._builder.url))

        cookie = self.getBuildCookie()
        args = self._extraBuildArgs()
        status, info = yield self._slave.build(
            cookie, "livefs", chroot.content.sha1, {}, args)

        message = """%s (%s):
        ***** RESULT *****
        %s
        %s: %s
        ******************
        """ % (
            self._builder.name,
            self._builder.url,
            args,
            status,
            info,
            )
        logger.info(message)
