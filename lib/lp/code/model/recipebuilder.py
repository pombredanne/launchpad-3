# Copyright 2010-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Code to build recipes on the buildfarm."""

__metaclass__ = type
__all__ = [
    'RecipeBuildBehaviour',
    ]

from twisted.internet import defer
from zope.component import adapter
from zope.interface import implementer
from zope.security.proxy import removeSecurityProxy

from lp.buildmaster.interfaces.builder import CannotBuild
from lp.buildmaster.interfaces.buildfarmjobbehaviour import (
    IBuildFarmJobBehaviour,
    )
from lp.buildmaster.model.buildfarmjobbehaviour import (
    BuildFarmJobBehaviourBase,
    )
from lp.code.interfaces.sourcepackagerecipebuild import (
    ISourcePackageRecipeBuild,
    )
from lp.services.config import config
from lp.services.propertycache import cachedproperty
from lp.soyuz.adapters.archivedependencies import (
    get_primary_current_component,
    get_sources_list_for_building,
    )


@adapter(ISourcePackageRecipeBuild)
@implementer(IBuildFarmJobBehaviour)
class RecipeBuildBehaviour(BuildFarmJobBehaviourBase):
    """How to build a recipe on the build farm."""

    builder_type = "sourcepackagerecipe"

    # The list of build status values for which email notifications are
    # allowed to be sent. It is up to each callback as to whether it will
    # consider sending a notification but it won't do so if the status is not
    # in this list.
    ALLOWED_STATUS_NOTIFICATIONS = ['PACKAGEFAIL', 'DEPFAIL', 'CHROOTFAIL']

    @cachedproperty
    def distro_arch_series(self):
        if self.build is not None and self._builder is not None:
            return self.build.distroseries.getDistroArchSeriesByProcessor(
                self._builder.processor)
        else:
            return None

    @defer.inlineCallbacks
    def extraBuildArgs(self, logger=None):
        """
        Return the extra arguments required by the slave for the given build.
        """
        if self.distro_arch_series is None:
            raise CannotBuild(
                "Unable to find distroarchseries for %s in %s" %
                (self._builder.processor.name,
                 self.build.distroseries.displayname))

        # Build extra arguments.
        args = yield super(RecipeBuildBehaviour, self).extraBuildArgs(
            logger=logger)
        args['suite'] = self.build.distroseries.getSuite(self.build.pocket)
        requester = self.build.requester
        if requester.preferredemail is None:
            # Use a constant, known, name and email.
            args["author_name"] = 'Launchpad Package Builder'
            args["author_email"] = config.canonical.noreply_from_address
        else:
            args["author_name"] = requester.displayname
            # We have to remove the security proxy here b/c there's not a
            # logged in entity, and anonymous email lookups aren't allowed.
            # Don't keep the naked requester around though.
            args["author_email"] = removeSecurityProxy(
                requester).preferredemail.email
        args["recipe_text"] = self.build.recipe.getRecipeText(validate=True)
        args['archive_purpose'] = self.build.archive.purpose.name
        args["ogrecomponent"] = get_primary_current_component(
            self.build.archive, self.build.distroseries,
            None).name
        args['archives'], args['trusted_keys'] = (
            yield get_sources_list_for_building(
                self.build, self.distro_arch_series, None,
                tools_source=config.builddmaster.bzr_builder_sources_list,
                logger=logger))
        # XXX cjwatson 2017-07-26: This duplicates "series", which is common
        # to all build types; this name for it is deprecated and should be
        # removed once launchpad-buildd no longer requires it.
        args['distroseries_name'] = self.build.distroseries.name
        if self.build.recipe.base_git_repository is not None:
            args['git'] = True
        defer.returnValue(args)

    def verifyBuildRequest(self, logger):
        """Assert some pre-build checks.

        The build request is checked:
         * Virtualized builds can't build on a non-virtual builder
         * Ensure that we have a chroot
         * Ensure that the build pocket allows builds for the current
           distroseries state.
        """
        build = self.build
        assert self._builder.virtualized, (
            "Attempt to build virtual item on a non-virtual builder.")

        # This should already have been checked earlier, but just check again
        # here in case of programmer errors.
        reason = build.archive.checkUploadToPocket(
            build.distroseries, build.pocket)
        assert reason is None, (
                "%s (%s) can not be built for pocket %s: invalid pocket due "
                "to the series status of %s." %
                    (build.title, build.id, build.pocket.name,
                     build.distroseries.name))
