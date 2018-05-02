# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Builder behaviour for binary package builds."""

__metaclass__ = type

__all__ = [
    'BinaryPackageBuildBehaviour',
    ]

from twisted.internet import defer
from zope.interface import implementer

from lp.buildmaster.interfaces.builder import CannotBuild
from lp.buildmaster.interfaces.buildfarmjobbehaviour import (
    IBuildFarmJobBehaviour,
    )
from lp.buildmaster.model.buildfarmjobbehaviour import (
    BuildFarmJobBehaviourBase,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.webapp import (
    canonical_url,
    urlappend,
    )
from lp.soyuz.adapters.archivedependencies import (
    get_primary_current_component,
    get_sources_list_for_building,
    )
from lp.soyuz.enums import ArchivePurpose
from lp.soyuz.model.publishing import makePoolPath


@implementer(IBuildFarmJobBehaviour)
class BinaryPackageBuildBehaviour(BuildFarmJobBehaviourBase):
    """Define the behaviour of binary package builds."""

    builder_type = "binarypackage"

    def getLogFileName(self):
        """See `IBuildPackageJob`."""
        sourcename = self.build.source_package_release.name
        version = self.build.source_package_release.version
        # we rely on previous storage of current buildstate
        # in the state handling methods.
        state = self.build.status.name

        dar = self.build.distro_arch_series
        distroname = dar.distroseries.distribution.name
        distroseriesname = dar.distroseries.name
        archname = dar.architecturetag

        # logfilename format:
        # buildlog_<DISTRIBUTION>_<DISTROSeries>_<ARCHITECTURE>_\
        # <SOURCENAME>_<SOURCEVERSION>_<BUILDSTATE>.txt
        # as:
        # buildlog_ubuntu_dapper_i386_foo_1.0-ubuntu0_FULLYBUILT.txt
        # it fix request from bug # 30617
        return ('buildlog_%s-%s-%s.%s_%s_%s.txt' % (
            distroname, distroseriesname, archname, sourcename, version,
            state))

    def determineFilesToSend(self):
        """See `IBuildFarmJobBehaviour`."""
        # Build filemap structure with the files required in this build
        # and send them to the slave.
        if self.build.archive.private:
            # Builds in private archive may have restricted files that
            # we can't obtain from the public librarian. Prepare a pool
            # URL from which to fetch them.
            pool_url = urlappend(
                self.build.archive.archive_url,
                makePoolPath(
                    self.build.source_package_release.sourcepackagename.name,
                    self.build.current_component.name))
        filemap = {}
        for source_file in self.build.source_package_release.files:
            lfa = source_file.libraryfile
            if not self.build.archive.private:
                filemap[lfa.filename] = {
                    'sha1': lfa.content.sha1, 'url': lfa.http_url}
            else:
                filemap[lfa.filename] = {
                    'sha1': lfa.content.sha1,
                    'url': urlappend(pool_url, lfa.filename),
                    'username': 'buildd',
                    'password': self.build.archive.buildd_secret}
        return filemap

    def verifyBuildRequest(self, logger):
        """Assert some pre-build checks.

        The build request is checked:
         * Virtualized builds can't build on a non-virtual builder
         * Ensure that we have a chroot
         * Ensure that the build pocket allows builds for the current
           distroseries state.
        """
        build = self.build
        if build.archive.require_virtualized and not self._builder.virtualized:
            raise AssertionError(
                "Attempt to build virtual archive on a non-virtual builder.")

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
        chroot = build.distro_arch_series.getChroot()
        if chroot is None:
            raise CannotBuild(
                "Missing CHROOT for %s/%s/%s" % (
                    build.distro_series.distribution.name,
                    build.distro_series.name,
                    build.distro_arch_series.architecturetag))

        # This should already have been checked earlier, but just check again
        # here in case of programmer errors.
        reason = build.archive.checkUploadToPocket(
            build.distro_series,
            build.pocket)
        assert reason is None, (
                "%s (%s) can not be built for pocket %s: invalid pocket due "
                "to the series status of %s." %
                    (build.title, build.id, build.pocket.name,
                     build.distro_series.name))

    @defer.inlineCallbacks
    def extraBuildArgs(self, logger=None):
        """
        Return the extra arguments required by the slave for the given build.
        """
        build = self.build
        das = build.distro_arch_series

        # Build extra arguments.
        args = yield super(BinaryPackageBuildBehaviour, self).extraBuildArgs(
            logger=logger)
        args['arch_indep'] = build.arch_indep
        args['distribution'] = das.distroseries.distribution.name
        args['series'] = das.distroseries.name
        args['suite'] = das.distroseries.getSuite(build.pocket)
        args['arch_tag'] = das.architecturetag

        archive_purpose = build.archive.purpose
        if (archive_purpose == ArchivePurpose.PPA and
            not build.archive.require_virtualized):
            # If we're building a non-virtual PPA, override the purpose
            # to PRIMARY and use the primary component override.
            # This ensures that the package mangling tools will run over
            # the built packages.
            args['archive_purpose'] = ArchivePurpose.PRIMARY.name
            args["ogrecomponent"] = (
                get_primary_current_component(build.archive,
                    build.distro_series,
                    build.source_package_release.name)).name
        else:
            args['archive_purpose'] = archive_purpose.name
            args["ogrecomponent"] = (
                build.current_component.name)

        args['archives'], args['trusted_keys'] = (
            yield get_sources_list_for_building(
                build, das, build.source_package_release.name, logger=logger))
        args['archive_private'] = build.archive.private
        args['build_url'] = canonical_url(build)
        args['build_debug_symbols'] = build.archive.build_debug_symbols

        defer.returnValue(args)
