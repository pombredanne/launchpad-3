# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Builder behavior for binary package builds."""

__metaclass__ = type

__all__ = [
    'BinaryPackageBuildBehavior',
    ]

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.webapp import urlappend

from lp.archiveuploader.permission import check_upload_to_pocket
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    IBuildFarmJobBehavior)
from lp.buildmaster.model.buildfarmjobbehavior import (
    BuildFarmJobBehaviorBase)
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.adapters.archivedependencies import (
    get_primary_current_component, get_sources_list_for_building)
from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.buildmaster.interfaces.builder import CannotBuild

from zope.interface import implements


class BinaryPackageBuildBehavior(BuildFarmJobBehaviorBase):
    """Define the behavior of binary package builds."""

    implements(IBuildFarmJobBehavior)

    @cachedproperty
    def build(self):
        return self.buildfarmjob.build

    def logStartBuild(self, logger):
        """See `IBuildFarmJobBehavior`."""
        spr = self.build.sourcepackagerelease
        logger.info("startBuild(%s, %s, %s, %s)", self._builder.url,
                    spr.name, spr.version, self.build.pocket.title)

    @property
    def status(self):
        """See `IBuildFarmJobBehavior`."""
        msg = 'Building %s' % self.build.title
        archive = self.build.archive
        if not archive.owner.private and (archive.is_ppa or archive.is_copy):
            return '%s [%s/%s]' % (msg, archive.owner.name, archive.name)
        else:
            return msg

    def dispatchBuildToSlave(self, build_queue_id, logger):
        """See `IBuildFarmJobBehavior`."""

        # Start the binary package build on the slave builder. First
        # we send the chroot.
        chroot = self.build.distroarchseries.getChroot()
        self._builder.slave.cacheFile(logger, chroot)

        # Build filemap structure with the files required in this build
        # and send them to the slave.
        # If the build is private we tell the slave to get the files from the
        # archive instead of the librarian because the slaves cannot
        # access the restricted librarian.
        private = self.build.archive.private
        if private:
            self._cachePrivateSourceOnSlave(logger)
        filemap = {}
        for source_file in self.build.sourcepackagerelease.files:
            lfa = source_file.libraryfile
            filemap[lfa.filename] = lfa.content.sha1
            if not private:
                self._builder.slave.cacheFile(logger, source_file.libraryfile)

        # Generate a string which can be used to cross-check when obtaining
        # results so we know we are referring to the right database object in
        # subsequent runs.
        buildid = "%s-%s" % (self.build.id, build_queue_id)
        chroot_sha1 = chroot.content.sha1
        logger.debug(
            "Initiating build %s on %s" % (buildid, self._builder.url))

        args = self._extraBuildArgs(self.build)
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

    def verifyBuildRequest(self, logger):
        """Assert some pre-build checks.

        The build request is checked:
         * Virtualized builds can't build on a non-virtual builder
         * Ensure that we have a chroot
         * Ensure that the build pocket allows builds for the current
           distroseries state.
        """
        build = self.build
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
                    build.distroarchseries.architecturetag))

        # This should already have been checked earlier, but just check again 
        # here in case of programmer errors.
        check_upload_to_pocket(build.archive, build.distroseries, build.pocket)

    def slaveStatus(self, raw_slave_status):
        """Parse and return the binary build specific status info.

        This includes:
        * build_id => string
        * build_status => string or None
        * logtail => string or None
        * filename => dictionary or None
        * dependencies => string or None
        """
        builder_status = raw_slave_status[0]
        extra_info = {}
        if builder_status == 'BuilderStatus.WAITING':
            extra_info['build_status'] = raw_slave_status[1]
            extra_info['build_id'] = raw_slave_status[2]
            build_status_with_files = [
                'BuildStatus.OK',
                'BuildStatus.PACKAGEFAIL',
                'BuildStatus.DEPFAIL',
                ]
            if extra_info['build_status'] in build_status_with_files:
                extra_info['filemap'] = raw_slave_status[3]
                extra_info['dependencies'] = raw_slave_status[4]
        else:
            extra_info['build_id'] = raw_slave_status[1]
            if builder_status == 'BuilderStatus.BUILDING':
                extra_info['logtail'] = raw_slave_status[2]

        return extra_info

    def _cachePrivateSourceOnSlave(self, logger):
        """Ask the slave to download source files for a private build.

        :param logger: A logger used for providing debug information.
        """
        # The URL to the file in the archive consists of these parts:
        # archive_url / makePoolPath() / filename
        # Once this is constructed we add the http basic auth info.

        # Avoid circular imports.
        from lp.soyuz.model.publishing import makePoolPath

        archive = self.build.archive
        archive_url = archive.archive_url
        component_name = self.build.current_component.name
        for source_file in self.build.sourcepackagerelease.files:
            file_name = source_file.libraryfile.filename
            sha1 = source_file.libraryfile.content.sha1
            spn = self.build.sourcepackagerelease.sourcepackagename
            poolpath = makePoolPath(spn.name, component_name)
            url = urlappend(archive_url, poolpath)
            url = urlappend(url, file_name)
            logger.debug("Asking builder on %s to ensure it has file %s "
                         "(%s, %s)" % (
                            self._builder.url, file_name, url, sha1))
            self._builder.slave._sendFileToSlave(
                url, sha1, "buildd", archive.buildd_secret)

    def _extraBuildArgs(self, build):
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
                get_primary_current_component(build.archive, 
                    build.sourcepackagerelease.name, build.distroseries))
        else:
            args['archive_purpose'] = archive_purpose.name
            args["ogrecomponent"] = (
                build.current_component.name)

        args['archives'] = get_sources_list_for_building(build, 
            build.sourcepackagerelease.name, build.distroarchseries)

        # Let the build slave know whether this is a build in a private
        # archive.
        args['archive_private'] = build.archive.private
        return args
