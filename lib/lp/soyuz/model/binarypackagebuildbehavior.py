# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Builder behavior for binary package builds."""

__metaclass__ = type

__all__ = [
    'BinaryPackageBuildBehavior',
    ]

import socket
import xmlrpclib

from canonical.launchpad.webapp import urlappend
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    IBuildFarmJobBehavior)
from lp.buildmaster.model.buildfarmjobbehavior import (
    BuildFarmJobBehaviorBase)
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.adapters.archivedependencies import (
    get_primary_current_component, get_sources_list_for_building)
from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.soyuz.interfaces.build import IBuildSet
from lp.soyuz.interfaces.builder import BuildSlaveFailure

from zope.component import getUtility
from zope.interface import implements


class BinaryPackageBuildBehavior(BuildFarmJobBehaviorBase):
    """Define the behavior of binary package builds."""

    implements(IBuildFarmJobBehavior)

    def log_start_build(self, build_queue_item, logger):
        """See `IBuildFarmJobBehavior`.""" 
        build = getUtility(IBuildSet).getByQueueEntry(build_queue_item)
        spr = build.sourcepackagerelease

        logger.info("startBuild(%s, %s, %s, %s)", self._builder.url,
                    spr.name, spr.version, build.pocket.title)

    def dispatch_build_to_slave(self, build_queue_item, logger):
        """See `IBuildFarmJobBehavior`."""

        # Start the binary package build on the slave builder. First
        # we send the chroot.
        build = getUtility(IBuildSet).getByQueueEntry(build_queue_item)
        chroot = build.distroarchseries.getChroot()
        self._builder.cacheFileOnSlave(logger, chroot)

        # Build filemap structure with the files required in this build
        # and send them to the slave.
        # If the build is private we tell the slave to get the files from the
        # archive instead of the librarian because the slaves cannot
        # access the restricted librarian.
        private = build.archive.private
        if private:
            self._cache_private_source_on_slave(build_queue_item, logger)
        filemap = {}
        for source_file in build.sourcepackagerelease.files:
            lfa = source_file.libraryfile
            filemap[lfa.filename] = lfa.content.sha1
            if not private:
                self._builder.cacheFileOnSlave(
                    logger, source_file.libraryfile)

        # Generate a string which can be used to cross-check when obtaining
        # results so we know we are referring to the right database object in
        # subsequent runs.
        buildid = "%s-%s" % (build.id, build_queue_item.id)
        chroot_sha1 = chroot.content.sha1
        logger.debug(
            "Initiating build %s on %s" % (buildid, self._builder.url))

        try:
            args = self._extra_build_args(build)
            status, info = self._builder.slave.build(
                buildid, "debian", chroot_sha1, filemap, args)
            message = """%s (%s):
            ***** RESULT *****
            %s
            %s
            %s: %s
            ******************
            """ % (
                self._builder.name,
                self._builder.url,
                filemap,
                args,
                status,
                info,
                )
            logger.info(message)
        except xmlrpclib.Fault, info:
            # Mark builder as 'failed'.
            logger.debug(
                "Disabling builder: %s" % self._builder.url, exc_info=1)
            self._builder.failbuilder(
                "Exception (%s) when setting up to new job" % info)
            raise BuildSlaveFailure
        except socket.error, info:
            error_message = "Exception (%s) when setting up new job" % info
            self._builder.handleTimeout(logger, error_message)
            raise BuildSlaveFailure

    def verify_build_request(self, build_queue_item, logger):
        """Assert some pre-build checks.

        The build request is checked:
         * Virtualized builds can't build on a non-virtual builder
         * Ensure that we have a chroot
         * Ensure that the build pocket allows builds for the current
           distroseries state.
        """
        build = getUtility(IBuildSet).getByQueueEntry(build_queue_item)
        assert not (not self._builder.virtualized and build.is_virtualized), (
            "Attempt to build non-virtual item on a virtual builder.")

        # Assert that we are not silently building SECURITY jobs.
        # See findBuildCandidates. Once we start building SECURITY
        # correctly from EMBARGOED archive this assertion can be removed.
        # XXX Julian 2007-12-18 spec=security-in-soyuz: This is being
        # addressed in the work on the blueprint:
        # https://blueprints.launchpad.net/soyuz/+spec/security-in-soyuz
        target_pocket = build.pocket
        assert target_pocket != PackagePublishingPocket.SECURITY, (
            "Soyuz is not yet capable of building SECURITY uploads.")

        # Ensure build has the needed chroot
        chroot = build.distroarchseries.getChroot()
        if chroot is None:
            raise CannotBuild(
                "Missing CHROOT for %s/%s/%s" % (
                    build.distroseries.distribution.name,
                    build.distroseries.name,
                    build.distroarchseries.architecturetag)
                )

        # The main distribution has policies to prevent uploads to some
        # pockets (e.g. security) during different parts of the distribution
        # series lifecycle. These do not apply to PPA builds nor any archive
        # that allows release pocket updates.
        if (build.archive.purpose != ArchivePurpose.PPA and
            not build.archive.allowUpdatesToReleasePocket()):
            # XXX Robert Collins 2007-05-26: not an explicit CannotBuild
            # exception yet because the callers have not been audited
            assert build.distroseries.canUploadToPocket(build.pocket), (
                "%s (%s) can not be built for pocket %s: invalid pocket due "
                "to the series status of %s."
                % (build.title, build.id, build.pocket.name,
                   build.distroseries.name))

    def _cache_private_source_on_slave(self, build_queue_item, logger):
        """Ask the slave to download source files for a private build.

        The slave will cache the files for the source in build_queue_item
        to its local disk in preparation for a private build.  Private builds
        will always take the source files from the archive rather than the
        librarian since the archive has more granular access to each
        archive's files.

        :param build_queue_item: The `IBuildQueue` being built.
        :param logger: A logger used for providing debug information.
        """
        # The URL to the file in the archive consists of these parts:
        # archive_url / makePoolPath() / filename
        # Once this is constructed we add the http basic auth info.

        # Avoid circular imports.
        from lp.soyuz.model.publishing import makePoolPath

        build = getUtility(IBuildSet).getByQueueEntry(build_queue_item)
        archive = build.archive
        archive_url = archive.archive_url
        component_name = build.current_component.name
        for source_file in build.sourcepackagerelease.files:
            file_name = source_file.libraryfile.filename
            sha1 = source_file.libraryfile.content.sha1
            source_name = build.sourcepackagerelease.sourcepackagename.name
            poolpath = makePoolPath(source_name, component_name)
            url = urlappend(archive_url, poolpath)
            url = urlappend(url, file_name)
            logger.debug("Asking builder on %s to ensure it has file %s "
                         "(%s, %s)" % (
                            self._builder.url, file_name, url, sha1))
            self._builder._sendFileToSlave(
                url, sha1, "buildd", archive.buildd_secret)

    def _extra_build_args(self, build):
        """
        Return the extra arguments required by the slave for the given build.
        """
        # Build extra arguments.
        args = {}
        # turn 'arch_indep' ON only if build is archindep or if
        # the specific architecture is the nominatedarchindep for
        # this distroseries (in case it requires any archindep source)
        args['arch_indep'] = build.distroarchseries.isNominatedArchIndep

        suite = build.distroarchseries.distroseries.name
        if build.pocket != PackagePublishingPocket.RELEASE:
            suite += "-%s" % (build.pocket.name.lower())
        args['suite'] = suite

        archive_purpose = build.archive.purpose
        if (archive_purpose == ArchivePurpose.PPA and
            not build.archive.require_virtualized):
            # If we're building a non-virtual PPA, override the purpose
            # to PRIMARY and use the primary component override.
            # This ensures that the package mangling tools will run over
            # the built packages.
            args['archive_purpose'] = ArchivePurpose.PRIMARY.name
            args["ogrecomponent"] = (
                get_primary_current_component(build))
        else:
            args['archive_purpose'] = archive_purpose.name
            args["ogrecomponent"] = (
                build.current_component.name)

        args['archives'] = get_sources_list_for_building(build)

        # Let the build slave know whether this is a build in a private
        # archive.
        args['archive_private'] = build.archive.private
        return args
