# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Code to build recipes on the buildfarm."""

__metaclass__ = type
__all__ = [
    'RecipeBuildBehavior',
    ]

from zope.component import adapts
from zope.interface import implements

from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    IBuildFarmJobBehavior)
from lp.buildmaster.interfaces.builder import CannotBuild
from lp.buildmaster.model.buildfarmjobbehavior import (
    BuildFarmJobBehaviorBase)
from lp.soyuz.adapters.archivedependencies import (
    get_primary_current_component, get_sources_list_for_building)
from lp.soyuz.interfaces.sourcepackagerecipebuild import (
    ISourcePackageRecipeBuildJob)


class RecipeBuildBehavior(BuildFarmJobBehaviorBase):
    """How to build a recipe on the build farm."""

    adapts(ISourcePackageRecipeBuildJob)
    implements(IBuildFarmJobBehavior)

    status = None

    @property
    def build(self):
        return self.buildfarmjob.build

    @property
    def display_name(self):
        sp = self.build.distroseries.getSourcePackage(
            self.build.sourcepackagename)
        ret = "%s, %s" % (
            sp.path, self.build.recipe.name)
        if self._builder is not None:
            ret += " (on %s)" % self._builder.url
        return ret

    def logStartBuild(self, logger):
        """See `IBuildFarmJobBehavior`."""
        logger.info("startBuild(%s)", self.display_name)

    def _extraBuildArgs(self):
        """
        Return the extra arguments required by the slave for the given build.
        """
        # Build extra arguments.
        args = {}
        # XXX: JRV 2010-01-13: When build gets a pocket property, it should 
        # be appended to suite here. (bug 507307)
        args['suite'] = self.build.distroseries.name
        args["package_name"] = self.build.sourcepackagename.name
        args["author_name"] = self.build.requester.displayname
        args["author_email"] = self.build.requester.preferredemail.email
        args["recipe_text"] = str(self.build.recipe.builder_recipe)
        args['archive_purpose'] = self.build.archive.purpose.name
        args["ogrecomponent"] = get_primary_current_component(
            self.build.archive, self.build.sourcepackagename.name, 
            self.build.distroseries)
        #args['archives'] = get_sources_list_for_building(self.build)
        return args

    def dispatchBuildToSlave(self, build_queue_id, logger):
        """See `IBuildFarmJobBehavior`."""

        distroseries = self.build.distroseries
        # Start the binary package build on the slave builder. First
        # we send the chroot.
        distroarchseries = distroseries.getDistroArchSeriesByProcessor(
            self._builder.processor)
        if distroarchseries is None:
            raise CannotBuild("Unable to find distroarchseries for %s in %s" %
                (self._builder.processor.name,
                self.build.distroseries.displayname))

        chroot = distroarchseries.getChroot()
        if chroot is None:
            raise CannotBuild("Unable to find a chroot for %s" % 
                              distroarchseries.displayname)
        self._builder.slave.cacheFile(logger, chroot)

        # Generate a string which can be used to cross-check when obtaining
        # results so we know we are referring to the right database object in
        # subsequent runs.
        buildid = "%s-%s" % (self.build.id, build_queue_id)
        chroot_sha1 = chroot.content.sha1
        logger.debug(
            "Initiating build %s on %s" % (buildid, self._builder.url))

        args = self._extraBuildArgs()
        status, info = self._builder.slave.build(
            buildid, "sourcepackagerecipe", chroot_sha1, {}, args)
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

        # XXX: Check whether this is allowed using 
        # lp.archiveuploader.permission.can_upload_to_archive

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
