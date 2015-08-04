# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""An `IBuildFarmJobBehaviour` for `SnapBuild`.

Dispatches snap package build jobs to build-farm slaves.
"""

__metaclass__ = type
__all__ = [
    'SnapBuildBehaviour',
    ]

from zope.component import (
    adapter,
    getUtility,
    )
from zope.interface import implementer

from lp.buildmaster.interfaces.builder import CannotBuild
from lp.buildmaster.interfaces.buildfarmjobbehaviour import (
    IBuildFarmJobBehaviour,
    )
from lp.buildmaster.model.buildfarmjobbehaviour import (
    BuildFarmJobBehaviourBase,
    )
from lp.registry.interfaces.series import SeriesStatus
from lp.services.config import config
from lp.snappy.interfaces.snap import SnapBuildArchiveOwnerMismatch
from lp.snappy.interfaces.snapbuild import ISnapBuild
from lp.soyuz.adapters.archivedependencies import (
    get_sources_list_for_building,
    )
from lp.soyuz.interfaces.archive import (
    ArchiveDisabled,
    IArchiveSet,
    )


@adapter(ISnapBuild)
@implementer(IBuildFarmJobBehaviour)
class SnapBuildBehaviour(BuildFarmJobBehaviourBase):
    """Dispatches `SnapBuild` jobs to slaves."""

    def getLogFileName(self):
        das = self.build.distro_arch_series

        # Examples:
        #   buildlog_snap_ubuntu_wily_amd64_name_FULLYBUILT.txt
        return 'buildlog_snap_%s_%s_%s_%s_%s.txt' % (
            das.distroseries.distribution.name, das.distroseries.name,
            das.architecturetag, self.build.snap.name, self.build.status.name)

    def verifyBuildRequest(self, logger):
        """Assert some pre-build checks.

        The build request is checked:
         * Virtualized builds can't build on a non-virtual builder
         * The source archive may not be disabled
         * If the source archive is private, the snap owner must match the
           archive owner (see `SnapBuildArchiveOwnerMismatch` docstring)
         * Ensure that we have a chroot
        """
        build = self.build
        if build.virtualized and not self._builder.virtualized:
            raise AssertionError(
                "Attempt to build virtual item on a non-virtual builder.")

        if not build.archive.enabled:
            raise ArchiveDisabled(build.archive.displayname)
        if build.archive.private and build.snap.owner != build.archive.owner:
            raise SnapBuildArchiveOwnerMismatch()

        chroot = build.distro_arch_series.getChroot()
        if chroot is None:
            raise CannotBuild(
                "Missing chroot for %s" % build.distro_arch_series.displayname)

    def _extraBuildArgs(self):
        """
        Return the extra arguments required by the slave for the given build.
        """
        build = self.build
        args = {}
        args["name"] = build.snap.name
        args["arch_tag"] = build.distro_arch_series.architecturetag
        # XXX cjwatson 2015-08-03: Allow this to be overridden at some more
        # fine-grained level.
        if config.snappy.tools_archive is not None:
            tools_archive = getUtility(IArchiveSet).getByReference(
                config.snappy.tools_archive)
        else:
            tools_archive = None
        args["archives"] = get_sources_list_for_building(
            build, build.distro_arch_series, None, tools_archive=tools_archive)
        args["archive_private"] = build.archive.private
        if build.snap.branch is not None:
            args["branch"] = build.snap.branch.bzr_identity
        else:
            assert build.snap.git_repository is not None
            args["git_repository"] = build.snap.git_repository.git_https_url
            args["git_path"] = build.snap.git_path
        return args

    def composeBuildRequest(self, logger):
        return (
            "snap", self.build.distro_arch_series, {},
            self._extraBuildArgs())

    def verifySuccessfulBuild(self):
        """See `IBuildFarmJobBehaviour`."""
        # The implementation in BuildFarmJobBehaviourBase checks whether the
        # target suite is modifiable in the target archive.  However, a
        # `SnapBuild`'s archive is a source rather than a target, so that
        # check does not make sense.  We do, however, refuse to build for
        # obsolete series.
        assert self.build.distro_series.status != SeriesStatus.OBSOLETE
