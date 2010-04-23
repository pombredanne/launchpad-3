# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'PackageBuild',
    'PackageBuildDerived',
    ]


from storm.locals import Int, Reference, Storm, Unicode

from zope.component import getUtility
from zope.interface import classProvides, implements

from canonical.database.constants import UTC_NOW
from canonical.database.enumcol import DBEnum
from canonical.launchpad.interfaces.lpstorm import IMasterStore

from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJobSource
from lp.buildmaster.interfaces.packagebuild import (
    IPackageBuild, IPackageBuildSource)
from lp.buildmaster.model.buildfarmjob import BuildFarmJobDerived
from lp.registry.interfaces.pocket import PackagePublishingPocket


class PackageBuild(BuildFarmJobDerived, Storm):
    """An implementation of `IBuildFarmJob` for package builds."""

    __storm_table__ = 'PackageBuild'

    implements(IPackageBuild)
    classProvides(IPackageBuildSource)

    id = Int(primary=True)

    archive_id = Int(name='archive', allow_none=False)
    archive = Reference(archive_id, 'Archive.id')

    pocket = DBEnum(
        name='pocket', allow_none=False,
        enum=PackagePublishingPocket)

    upload_log_id = Int(name='upload_log', allow_none=True)
    upload_log = Reference(upload_log_id, 'LibraryFileAlias.id')

    dependencies = Unicode(name='dependencies', allow_none=True)

    build_farm_job_id = Int(name='build_farm_job', allow_none=False)
    build_farm_job = Reference(build_farm_job_id, 'BuildFarmJob.id')

    def __init__(self, build):
        """Construct a PackageBuild.

        XXX 2010-04-21 michael.nelson bug=536700
        This initialiser is only used by IBuildFarmJobDerived classes
        that are not yet expecting a concrete BuildFarmJob (and so are
        expecting to pass in the build to which they refer, such as
        BinaryPackageBuild/BuildPackageJob, SPRecipeBuild/SPRecipeBuildJob
        and TranslationTemplatesBuild). Once they have been updated it
        can be updated for use by new below.
        """
        super(PackageBuild, self).__init__()
        self.build = build

    @classmethod
    def new(cls, job_type, virtualized, archive, pocket,
            processor=None, status=None, dependencies=None):
        """See `IPackageBuildSource`."""
        store = IMasterStore(PackageBuild)

        # Create the BuildFarmJob to which the new PackageBuild
        # will delegate.
        build_farm_job = getUtility(IBuildFarmJobSource).new(
            job_type, status, processor, virtualized)

        # Update the __init__ and call instead once all callsites use
        # instances of this class as a concrete class.
        package_build = cls(None)
        package_build.build_farm_job = build_farm_job
        package_build.archive = archive
        package_build.pocket = pocket
        package_build.dependencies = dependencies
        store.add(package_build)
        return package_build

    def getTitle(self):
        """See `IBuildFarmJob`.

        XXX 2010-04-21 michael.nelson bug=567922. This method
        can be removed once all *Build classes use the concrete
        BuildFarmJob.
        """
        if self.has_concrete_build_farm_job:
            return self.build_farm_job.getTitle()

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
        self.build_farm_job = PackageBuild(self.build)


