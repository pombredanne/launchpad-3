# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Code to build recipes on the buildfarm."""

__metaclass__ = type
__all__ = [
    'RecipeBuildBehavior',
    ]

from zope.component import adapts
from zope.interface import implements

from canonical.cachedproperty import cachedproperty

from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    IBuildFarmJobBehavior)
from lp.buildmaster.model.buildfarmjobbehavior import (
    BuildFarmJobBehaviorBase)
from lp.soyuz.adapters.archivedependencies import (
    get_primary_current_component)
from lp.soyuz.interfaces.sourcepackagebuild import (
    IBuildSourcePackageFromRecipeJob)


class RecipeBuildBehavior(BuildFarmJobBehaviorBase):
    """How to build a recipe on the build farm."""

    adapts(IBuildSourcePackageFromRecipeJob)
    implements(IBuildFarmJobBehavior)

    status = None

    @cachedproperty
    def build(self):
        return self.buildfarmjob.build

    @property
    def displayName(self):
        sp = self.build.distroseries.getSourcePackage(
            self.build.sourcepackagename)
        ret = "%s, %s" % (
            sp.path, self.build.recipe.name)
        if self._builder is not None:
            ret += " (on %s)" % self._builder.url
        return ret

    def logStartBuild(self, logger):
        """See `IBuildFarmJobBehavior`."""
        logger.info("startBuild(%s)", self.displayName)

    def _extraBuildArgs(self, build):
        """
        Return the extra arguments required by the slave for the given build.
        """
        # Build extra arguments.
        args = {}
        # XXX: JRV 2010-01-13: When build gets a pocket property, it should 
        # be appended to suite here.
        args['suite'] = build.distroarchseries.distroseries.name
        args["package_name"] = build.sourcepackagename.name
        args["author_name"] = build.requester.displayname
        args["author_email"] = build.requester.preferredemail.email

        archive_purpose = build.archive.purpose
        if (archive_purpose == ArchivePurpose.PPA and
            not build.archive.require_virtualized):
            # If we're building a non-virtual PPA, override the purpose
            # to PRIMARY and use the primary component override.
            # This ensures that the package mangling tools will run over
            # the built packages.
            args['purpose'] = ArchivePurpose.PRIMARY.name
            args["component"] = get_primary_current_component(build)
        else:
            args['purpose'] = archive_purpose.name
            args["ogrecomponent"] = build.current_component.name

        args["recipe_text"] = build.manifest.getRecipe()

        return args

    def dispatchBuildToSlave(self, build_queue_id, logger):
        """See `IBuildFarmJobBehavior`."""

        # Start the binary package build on the slave builder. First
        # we send the chroot.
        distroarchseries = self.build.distroseries.getDistroArchSeries(
            self._builder.processor.family.name)

        chroot = self.distroarchseries.getChroot()
        self._builder.slave.cacheFile(logger, chroot)

        # Generate a string which can be used to cross-check when obtaining
        # results so we know we are referring to the right database object in
        # subsequent runs.
        buildid = "%s-%s" % (self.build.id, build_queue_id)
        chroot_sha1 = chroot.content.sha1
        logger.debug(
            "Initiating build %s on %s" % (buildid, self._builder.url))

        args = self._extraBuildArgs(self.build)
        status, info = self._builder.slave.build(
            buildid, "sourcepackagerecipe", chroot_sha1, {}, args)
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
