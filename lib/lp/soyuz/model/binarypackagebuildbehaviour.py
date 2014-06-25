# Copyright 2009-2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Builder behaviour for binary package builds."""

__metaclass__ = type

__all__ = [
    'BinaryPackageBuildBehaviour',
    ]

from twisted.internet import defer
from zope.interface import implements

from lp.buildmaster.interfaces.builder import CannotBuild
from lp.buildmaster.interfaces.buildfarmjobbehaviour import (
    IBuildFarmJobBehaviour,
    )
from lp.buildmaster.model.buildfarmjobbehaviour import (
    BuildFarmJobBehaviourBase,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.webapp import urlappend
from lp.soyuz.adapters.archivedependencies import (
    get_primary_current_component,
    get_sources_list_for_building,
    )
from lp.soyuz.enums import ArchivePurpose
from lp.soyuz.model.publishing import makePoolPath


class BinaryPackageBuildBehaviour(BuildFarmJobBehaviourBase):
    """Define the behaviour of binary package builds."""

    implements(IBuildFarmJobBehaviour)

    def logStartBuild(self, logger):
        """See `IBuildFarmJobBehaviour`."""
        spr = self.build.source_package_release
        logger.info("startBuild(%s, %s, %s, %s)", self._builder.url,
                    spr.name, spr.version, self.build.pocket.title)

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

    def composeBuildRequest(self, logger):
        return (
            "binarypackage", self.build.distro_arch_series,
            self.determineFilesToSend(), self._extraBuildArgs(self.build))

    def verifyBuildRequest(self, logger):
        """Assert some pre-build checks.

        The build request is checked:
         * Virtualized builds can't build on a non-virtual builder
         * Ensure that we have a chroot
         * Ensure that the build pocket allows builds for the current
           distroseries state.
        """
        build = self.build
        if build.is_virtualized and not self._builder.virtualized:
            raise AssertionError(
                "Attempt to build virtual item on a non-virtual builder.")

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

    def _extraBuildArgs(self, build):
        """
        Return the extra arguments required by the slave for the given build.
        """
        # Build extra arguments.
        args = {}
        # turn 'arch_indep' ON only if build is archindep or if
        # the specific architecture is the nominatedarchindep for
        # this distroseries (in case it requires any archindep source)
        args['arch_indep'] = build.distro_arch_series.isNominatedArchIndep

        args['suite'] = build.distro_arch_series.distroseries.getSuite(
            build.pocket)
        args['arch_tag'] = build.distro_arch_series.architecturetag

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
                    build.distro_series, build.source_package_release.name))
        else:
            args['archive_purpose'] = archive_purpose.name
            args["ogrecomponent"] = (
                build.current_component.name)

        args['archives'] = get_sources_list_for_building(build,
            build.distro_arch_series, build.source_package_release.name)
        args['archive_private'] = build.archive.private
        args['build_debug_symbols'] = build.archive.build_debug_symbols

        return args
