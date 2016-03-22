# Copyright 2010-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""`TranslationTemplatesBuild` class."""

__metaclass__ = type
__all__ = [
    'HARDCODED_TRANSLATIONTEMPLATESBUILD_SCORE',
    'TranslationTemplatesBuild',
    ]

from datetime import timedelta
import logging

import pytz
from storm.locals import (
    Bool,
    DateTime,
    Int,
    Reference,
    Storm,
    )
from zope.component import getUtility
from zope.interface import (
    implementer,
    provider,
    )
from zope.security.proxy import removeSecurityProxy

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.buildmaster.enums import (
    BuildFarmJobType,
    BuildStatus,
    )
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJobSource
from lp.buildmaster.model.buildfarmjob import (
    BuildFarmJobMixin,
    SpecificBuildFarmJobSourceMixin,
    )
from lp.code.interfaces.branchjob import IRosettaUploadJobSource
from lp.code.model.branch import Branch
from lp.code.model.branchcollection import GenericBranchCollection
from lp.services.config import config
from lp.services.database.bulk import load_related
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.database.enumcol import DBEnum
from lp.services.database.interfaces import IStore
from lp.translations.interfaces.translationtemplatesbuild import (
    ITranslationTemplatesBuild,
    ITranslationTemplatesBuildSource,
    )
from lp.translations.pottery.detect_intltool import is_intltool_structure


HARDCODED_TRANSLATIONTEMPLATESBUILD_SCORE = 2510


@implementer(ITranslationTemplatesBuild)
@provider(ITranslationTemplatesBuildSource)
class TranslationTemplatesBuild(SpecificBuildFarmJobSourceMixin,
                                BuildFarmJobMixin, Storm):
    """A `BuildFarmJob` extension for translation templates builds."""

    __storm_table__ = 'TranslationTemplatesBuild'

    job_type = BuildFarmJobType.TRANSLATIONTEMPLATESBUILD

    id = Int(name='id', primary=True)
    build_farm_job_id = Int(name='build_farm_job', allow_none=False)
    build_farm_job = Reference(build_farm_job_id, 'BuildFarmJob.id')
    branch_id = Int(name='branch', allow_none=False)
    branch = Reference(branch_id, 'Branch.id')

    processor_id = Int(name='processor')
    processor = Reference(processor_id, 'Processor.id')
    virtualized = Bool(name='virtualized')

    date_created = DateTime(
        name='date_created', tzinfo=pytz.UTC, allow_none=False)
    date_started = DateTime(name='date_started', tzinfo=pytz.UTC)
    date_finished = DateTime(name='date_finished', tzinfo=pytz.UTC)
    date_first_dispatched = DateTime(
        name='date_first_dispatched', tzinfo=pytz.UTC)

    builder_id = Int(name='builder')
    builder = Reference(builder_id, 'Builder.id')

    status = DBEnum(name='status', enum=BuildStatus, allow_none=False)

    log_id = Int(name='log')
    log = Reference(log_id, 'LibraryFileAlias.id')

    failure_count = Int(name='failure_count', allow_none=False)

    @property
    def title(self):
        return u'Translation template build for %s' % (
            self.branch.displayname)

    def __init__(self, build_farm_job, branch, processor):
        super(TranslationTemplatesBuild, self).__init__()
        self.build_farm_job = build_farm_job
        self.branch = branch
        self.status = BuildStatus.NEEDSBUILD
        self.processor = processor
        self.virtualized = True

    def estimateDuration(self):
        """See `IBuildFarmJob`."""
        return timedelta(seconds=10)

    @classmethod
    def _getStore(cls, store=None):
        """Return `store` if given, or the default."""
        if store is None:
            return IStore(cls)
        else:
            return store

    @classmethod
    def _getBuildArch(cls):
        """Returns an `IProcessor` to queue a translation build for."""
        # XXX Danilo Segan bug=580429: we hard-code processor to the Ubuntu
        # default processor architecture.  This stops the buildfarm from
        # accidentally dispatching the jobs to private builders.
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        return ubuntu.currentseries.nominatedarchindep.processor

    @classmethod
    def _hasPotteryCompatibleSetup(cls, branch):
        """Does `branch` look as if pottery can generate templates for it?

        :param branch: A `Branch` object.
        """
        bzr_branch = removeSecurityProxy(branch).getBzrBranch()
        return is_intltool_structure(bzr_branch.basis_tree())

    @classmethod
    def generatesTemplates(cls, branch):
        """See `ITranslationTemplatesBuildSource`."""
        logger = logging.getLogger('translation-templates-build')
        if branch.private:
            # We don't support generating template from private branches
            # at the moment.
            logger.debug("Branch %s is private.", branch.unique_name)
            return False

        utility = getUtility(IRosettaUploadJobSource)
        if not utility.providesTranslationFiles(branch):
            # Nobody asked for templates generated from this branch.
            logger.debug(
                    "No templates requested for branch %s.",
                    branch.unique_name)
            return False

        if not cls._hasPotteryCompatibleSetup(branch):
            # Nothing we could do with this branch if we wanted to.
            logger.debug(
                "Branch %s is not pottery-compatible.", branch.unique_name)
            return False

        # Yay!  We made it.
        return True

    @classmethod
    def create(cls, branch):
        """See `ITranslationTemplatesBuildSource`."""
        processor = cls._getBuildArch()
        build_farm_job = getUtility(IBuildFarmJobSource).new(
            BuildFarmJobType.TRANSLATIONTEMPLATESBUILD)
        build = TranslationTemplatesBuild(build_farm_job, branch, processor)
        store = cls._getStore()
        store.add(build)
        store.flush()
        return build

    @classmethod
    def scheduleTranslationTemplatesBuild(cls, branch):
        """See `ITranslationTemplatesBuildSource`."""
        logger = logging.getLogger('translation-templates-build')
        if not config.rosetta.generate_templates:
            # This feature is disabled by default.
            logging.debug("Templates generation is disabled.")
            return

        try:
            if cls.generatesTemplates(branch):
                # This branch is used for generating templates.
                logger.info(
                    "Requesting templates build for branch %s.",
                    branch.unique_name)
                cls.create(branch).queueBuild()
        except Exception as e:
            logger.error(e)
            raise

    @classmethod
    def getByID(cls, build_id, store=None):
        """See `ITranslationTemplatesBuildSource`."""
        store = cls._getStore(store)
        return store.get(TranslationTemplatesBuild, build_id)

    @classmethod
    def getByBuildFarmJob(cls, buildfarmjob, store=None):
        """See `ITranslationTemplatesBuildSource`."""
        store = cls._getStore(store)
        match = store.find(
            TranslationTemplatesBuild, build_farm_job_id=buildfarmjob.id)
        return match.one()

    @classmethod
    def getByBuildFarmJobs(cls, buildfarmjobs, store=None):
        """See `ITranslationTemplatesBuildSource`."""
        store = cls._getStore(store)
        rows = store.find(
            TranslationTemplatesBuild,
            TranslationTemplatesBuild.build_farm_job_id.is_in(
                bfj.id for bfj in buildfarmjobs))
        return DecoratedResultSet(rows, pre_iter_hook=cls.preloadBuildsData)

    @classmethod
    def preloadBuildsData(cls, builds):
        # Circular imports.
        from lp.services.librarian.model import LibraryFileAlias
        # Load the related branches.
        branches = load_related(
            Branch, builds, ['branch_id'])
        # Preload branches' cached associated targets, product series, and
        # suite source packages for all the related branches.
        GenericBranchCollection.preloadDataForBranches(branches)
        load_related(LibraryFileAlias, builds, ['log_id'])

    @classmethod
    def findByBranch(cls, branch, store=None):
        """See `ITranslationTemplatesBuildSource`."""
        store = cls._getStore(store)
        return store.find(
            TranslationTemplatesBuild,
            TranslationTemplatesBuild.branch == branch)

    @property
    def log_url(self):
        """See `IBuildFarmJob`."""
        if self.log is None:
            return None
        return self.log.http_url

    def calculateScore(self):
        """See `IBuildFarmJob`."""
        # Hard-code score for now.  Most PPA jobs start out at 2505;
        # TranslationTemplateBuild are fast so we want them at a higher
        # priority.
        return HARDCODED_TRANSLATIONTEMPLATESBUILD_SCORE
