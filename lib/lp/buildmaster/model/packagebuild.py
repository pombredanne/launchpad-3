# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'PackageBuild',
    'PackageBuildDerived',
    ]


from storm.locals import Int, Reference, Storm, Unicode

from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.enumcol import DBEnum

from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.buildmaster.interfaces.packagebuild import IPackageBuild
from lp.buildmaster.model.buildfarmjob import (
    BuildFarmJob, BuildFarmJobDerived)
from lp.registry.interfaces.pocket import PackagePublishingPocket


class PackageBuild(Storm, BuildFarmJob):
    """An implementation of `IBuildFarmJob` for package builds."""

    __storm_table__ = 'PackageBuild'

    implements(IPackageBuild)

    id = Int(primary=True)

    archive_id = Int(name='archive', allow_none=False)
    archive = Reference(archive_id, 'Archive.id')

    pocket = DBEnum(
        name='pocket', allow_none=False,
        enum=PackagePublishingPocket)

    upload_log_id = Int(name='upload_log', allow_none=True)
    upload_log = Reference(upload_log_id, 'LibraryFileAlias.id')

    dependencies = Unicode(name='dependencies', allow_none=True)

    def __init__(self, build):
        """Store the build for this package build farm job.

        XXX 2010-04-12 michael.nelson bug=536700
        The build param will no longer be necessary once BuildFarmJob is
        itself a concrete class. This class (PackageBuild)
        will also be renamed PackageBuild and turned into a concrete class.
        """
        super(PackageBuild, self).__init__()
        self.build = build

    def getTitle(self):
        """See `IBuildFarmJob`."""
        return self.build.title

    def jobStarted(self):
        """See `IBuildFarmJob`."""
        self.build.buildstate = BuildStatus.BUILDING
        # The build started, set the start time if not set already.
        if self.build.date_first_dispatched is None:
            self.build.date_first_dispatched = UTC_NOW

    def jobReset(self):
        """See `IBuildFarmJob`."""
        self.build.buildstate = BuildStatus.NEEDSBUILD

    def jobAborted(self):
        """See `IBuildFarmJob`."""
        self.build.buildstate = BuildStatus.NEEDSBUILD


class PackageBuildDerived(BuildFarmJobDerived):
    """Override the base delegate to use a build farm job specific to
    packages.
    """
    def _set_build_farm_job(self):
        self._build_farm_job = PackageBuild(self.build)


