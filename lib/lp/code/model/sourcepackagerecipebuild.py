# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=F0401,E1002

"""Implementation code for source package builds."""

__metaclass__ = type
__all__ = [
    'SourcePackageRecipeBuild',
    ]

from datetime import (
    datetime,
    timedelta,
    )
import logging
import sys

from psycopg2 import ProgrammingError
from pytz import utc
from storm.locals import (
    Int,
    Reference,
    Storm,
    )
from storm.store import Store
from zope.component import (
    getUtility,
    )
from zope.interface import (
    classProvides,
    implements,
    )

from canonical.database.constants import UTC_NOW
from canonical.launchpad.browser.librarian import ProxiedLibraryFileAlias
from canonical.launchpad.interfaces.lpstorm import (
    IMasterStore,
    IStore,
    )
from canonical.launchpad.webapp import errorlog
from lp.app.errors import NotFoundError
from lp.buildmaster.enums import (
    BuildFarmJobType,
    BuildStatus,
    )
from lp.buildmaster.model.buildfarmjob import BuildFarmJobOldDerived
from lp.buildmaster.model.buildqueue import BuildQueue
from lp.buildmaster.model.packagebuild import (
    PackageBuild,
    PackageBuildDerived,
    )
from lp.code.errors import (
    BuildAlreadyPending,
    BuildNotAllowedForDistro,
    )
from lp.code.interfaces.sourcepackagerecipebuild import (
    ISourcePackageRecipeBuild,
    ISourcePackageRecipeBuildJob,
    ISourcePackageRecipeBuildJobSource,
    ISourcePackageRecipeBuildSource,
    )
from lp.code.mail.sourcepackagerecipebuild import (
    SourcePackageRecipeBuildMailer,
    )
from lp.code.model.sourcepackagerecipedata import SourcePackageRecipeData
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.job.model.job import Job
from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
from lp.soyuz.model.buildfarmbuildjob import BuildFarmBuildJob
from lp.soyuz.interfaces.archive import CannotUploadToArchive
from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease


class SourcePackageRecipeBuild(PackageBuildDerived, Storm):

    __storm_table__ = 'SourcePackageRecipeBuild'

    implements(ISourcePackageRecipeBuild)
    classProvides(ISourcePackageRecipeBuildSource)

    package_build_id = Int(name='package_build', allow_none=False)
    package_build = Reference(package_build_id, 'PackageBuild.id')

    build_farm_job_type = BuildFarmJobType.RECIPEBRANCHBUILD

    id = Int(primary=True)

    is_private = False

    # The list of build status values for which email notifications are
    # allowed to be sent. It is up to each callback as to whether it will
    # consider sending a notification but it won't do so if the status is not
    # in this list.
    ALLOWED_STATUS_NOTIFICATIONS = [
        'OK', 'PACKAGEFAIL', 'DEPFAIL', 'CHROOTFAIL']

    @property
    def binary_builds(self):
        """See `ISourcePackageRecipeBuild`."""
        return Store.of(self).find(
            BinaryPackageBuild,
            BinaryPackageBuild.source_package_release ==
                SourcePackageRelease.id,
            SourcePackageRelease.source_package_recipe_build == self.id)

    @property
    def current_component(self):
        # Only PPAs currently have a sane default component at the
        # moment, but we only support recipes for PPAs.
        component = self.archive.default_component
        assert component is not None
        return component

    distroseries_id = Int(name='distroseries', allow_none=True)
    distroseries = Reference(distroseries_id, 'DistroSeries.id')
    distro_series = distroseries

    @property
    def distribution(self):
        """See `IPackageBuild`."""
        return self.distroseries.distribution

    is_virtualized = True

    recipe_id = Int(name='recipe')
    recipe = Reference(recipe_id, 'SourcePackageRecipe.id')

    manifest = Reference(
        id, 'SourcePackageRecipeData.sourcepackage_recipe_build_id',
        on_remote=True)

    def setManifestText(self, text):
        if text is None:
            if self.manifest is not None:
                IStore(self.manifest).remove(self.manifest)
        elif self.manifest is None:
            SourcePackageRecipeData.createManifestFromText(text, self)
        else:
            from bzrlib.plugins.builder.recipe import RecipeParser
            self.manifest.setRecipe(RecipeParser(text).parse())

    def getManifestText(self):
        if self.manifest is None:
            return None
        return str(self.manifest.getRecipe())

    requester_id = Int(name='requester', allow_none=False)
    requester = Reference(requester_id, 'Person.id')

    @property
    def buildqueue_record(self):
        """See `IBuildFarmJob`."""
        store = Store.of(self)
        results = store.find(
            BuildQueue,
            SourcePackageRecipeBuildJob.job == BuildQueue.jobID,
            SourcePackageRecipeBuildJob.build == self.id)
        return results.one()

    @property
    def source_package_release(self):
        """See `ISourcePackageRecipeBuild`."""
        return Store.of(self).find(
            SourcePackageRelease, source_package_recipe_build=self).one()

    @property
    def title(self):
        if self.recipe is None:
            return 'build for deleted recipe'
        else:
            branch_name = self.recipe.base_branch.unique_name
            return '%s recipe build' % branch_name

    def __init__(self, package_build, distroseries, recipe, requester):
        """Construct a SourcePackageRecipeBuild."""
        super(SourcePackageRecipeBuild, self).__init__()
        self.package_build = package_build
        self.distroseries = distroseries
        self.recipe = recipe
        self.requester = requester

    @classmethod
    def new(cls, distroseries, recipe, requester, archive, pocket=None,
            date_created=None, duration=None):
        """See `ISourcePackageRecipeBuildSource`."""
        store = IMasterStore(SourcePackageRecipeBuild)
        if pocket is None:
            pocket = PackagePublishingPocket.RELEASE
        if date_created is None:
            date_created = UTC_NOW
        packagebuild = PackageBuild.new(cls.build_farm_job_type,
            True, archive, pocket, date_created=date_created)
        spbuild = cls(
            packagebuild,
            distroseries,
            recipe,
            requester)
        store.add(spbuild)
        return spbuild

    @staticmethod
    def makeDailyBuilds(logger=None):
        from lp.code.model.sourcepackagerecipe import SourcePackageRecipe
        recipes = SourcePackageRecipe.findStaleDailyBuilds()
        if logger is None:
            logger = logging.getLogger()
        builds = []
        for recipe in recipes:
            recipe.is_stale = False
            logger.debug(
                'Recipe %s/%s is stale', recipe.owner.name, recipe.name)
            if recipe.daily_build_archive is None:
                logger.debug(' - No daily build archive specified.')
                continue
            for distroseries in recipe.distroseries:
                series_name = distroseries.named_version
                try:
                    build = recipe.requestBuild(
                        recipe.daily_build_archive, recipe.owner,
                        distroseries, PackagePublishingPocket.RELEASE)
                except BuildAlreadyPending:
                    logger.debug(
                        ' - build already pending for %s', series_name)
                    continue
                except CannotUploadToArchive, e:
                    # This will catch all PPA related issues -
                    # disabled, security, wrong pocket etc
                    logger.debug(
                        ' - daily build failed for %s: %s',
                        series_name, str(e))
                except BuildNotAllowedForDistro:
                    logger.debug(
                        ' - cannot build against %s.' % series_name)
                except ProgrammingError:
                    raise
                except:
                    logger.exception(' - problem with %s', series_name)
                    info = sys.exc_info()
                    errorlog.globalErrorUtility.raising(info)
                else:
                    logger.debug(' - build requested for %s', series_name)
                    builds.append(build)
        return builds

    def _unqueueBuild(self):
        """Remove the build's queue and job."""
        store = Store.of(self)
        if self.buildqueue_record is not None:
            job = self.buildqueue_record.job
            store.remove(self.buildqueue_record)
            store.find(
                SourcePackageRecipeBuildJob,
                SourcePackageRecipeBuildJob.build == self.id).remove()
            store.remove(job)

    def cancelBuild(self):
        """See `ISourcePackageRecipeBuild.`"""
        self._unqueueBuild()
        self.status = BuildStatus.SUPERSEDED

    def destroySelf(self):
        self._unqueueBuild()
        store = Store.of(self)
        releases = store.find(
            SourcePackageRelease,
            SourcePackageRelease.source_package_recipe_build == self.id)
        for release in releases:
            release.source_package_recipe_build = None
        package_build = self.package_build
        store.remove(self)
        package_build.destroySelf()

    @classmethod
    def getByID(cls, build_id):
        """See `ISourcePackageRecipeBuildSource`."""
        store = IMasterStore(SourcePackageRecipeBuild)
        return store.find(cls, cls.id == build_id).one()

    @classmethod
    def getByBuildFarmJob(cls, build_farm_job):
        """See `ISpecificBuildFarmJobSource`."""
        return Store.of(build_farm_job).find(cls,
            cls.package_build_id == PackageBuild.id,
            PackageBuild.build_farm_job_id == build_farm_job.id).one()

    @classmethod
    def getRecentBuilds(cls, requester, recipe, distroseries, _now=None):
        from lp.buildmaster.model.buildfarmjob import BuildFarmJob
        if _now is None:
            _now = datetime.now(utc)
        store = IMasterStore(SourcePackageRecipeBuild)
        old_threshold = _now - timedelta(days=1)
        return store.find(cls, cls.distroseries_id == distroseries.id,
            cls.requester_id == requester.id, cls.recipe_id == recipe.id,
            BuildFarmJob.date_created > old_threshold,
            BuildFarmJob.id == PackageBuild.build_farm_job_id,
            PackageBuild.id == cls.package_build_id)

    def makeJob(self):
        """See `ISourcePackageRecipeBuildJob`."""
        store = Store.of(self)
        job = Job()
        store.add(job)
        specific_job = getUtility(
            ISourcePackageRecipeBuildJobSource).new(self, job)
        return specific_job

    def estimateDuration(self):
        """See `IPackageBuild`."""
        median = self.recipe.getMedianBuildDuration()
        if median is not None:
            return median
        return timedelta(minutes=10)

    def verifySuccessfulUpload(self):
        return self.source_package_release is not None

    def notify(self, extra_info=None):
        """See `IPackageBuild`."""
        # If our recipe has been deleted, any notification will fail.
        if self.recipe is None:
            return
        if self.status == BuildStatus.FULLYBUILT:
            # Don't send mail for successful recipe builds; it can be just
            # too much.
            return
        mailer = SourcePackageRecipeBuildMailer.forStatus(self)
        mailer.sendAll()

    def lfaUrl(self, lfa):
        """Return the URL for a LibraryFileAlias, in the context of self.
        """
        if lfa is None:
            return None
        return ProxiedLibraryFileAlias(lfa, self).http_url

    @property
    def log_url(self):
        """See `IPackageBuild`.

        Overridden here so that it uses the SourcePackageRecipeBuild as
        context.
        """
        return self.lfaUrl(self.log)

    @property
    def upload_log_url(self):
        """See `IPackageBuild`.

        Overridden here so that it uses the SourcePackageRecipeBuild as
        context.
        """
        return self.lfaUrl(self.upload_log)

    def getFileByName(self, filename):
        """See `ISourcePackageRecipeBuild`."""
        files = dict((lfa.filename, lfa)
                     for lfa in [self.log, self.upload_log]
                     if lfa is not None)
        try:
            return files[filename]
        except KeyError:
            raise NotFoundError(filename)

    def getUploader(self, changes):
        """See `IPackageBuild`."""
        return self.requester


class SourcePackageRecipeBuildJob(BuildFarmJobOldDerived, Storm):
    classProvides(ISourcePackageRecipeBuildJobSource)
    implements(ISourcePackageRecipeBuildJob)

    __storm_table__ = 'sourcepackagerecipebuildjob'

    id = Int(primary=True)

    job_id = Int(name='job', allow_none=False)
    job = Reference(job_id, 'Job.id')

    build_id = Int(name='sourcepackage_recipe_build', allow_none=False)
    build = Reference(
        build_id, 'SourcePackageRecipeBuild.id')

    @property
    def processor(self):
        return self.build.distroseries.nominatedarchindep.default_processor

    @property
    def virtualized(self):
        """See `IBuildFarmJob`."""
        return self.build.is_virtualized

    def __init__(self, build, job):
        self.build = build
        self.job = job
        super(SourcePackageRecipeBuildJob, self).__init__()

    def _set_build_farm_job(self):
        """Setup the IBuildFarmJob delegate.

        We override this to provide a delegate specific to package builds."""
        self.build_farm_job = BuildFarmBuildJob(self.build)

    @classmethod
    def new(cls, build, job):
        """See `ISourcePackageRecipeBuildJobSource`."""
        specific_job = cls(build, job)
        store = IMasterStore(cls)
        store.add(specific_job)
        return specific_job

    def getName(self):
        return "%s-%s" % (self.id, self.build_id)

    def score(self):
        return 2505 + self.build.archive.relative_build_score
