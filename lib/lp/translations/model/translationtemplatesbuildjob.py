# Copyright 2010 Canonical Ltd. This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'HARDCODED_TRANSLATIONTEMPLATESBUILD_SCORE',
    'TranslationTemplatesBuildJob',
    ]

from datetime import timedelta
import logging
import re

from storm.store import Store
from zope.component import getUtility
from zope.interface import (
    classProvides,
    implements,
    )
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.launchpad.interfaces.lpstorm import (
    IMasterStore,
    IStore,
    )
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.buildmaster.enums import BuildFarmJobType
from lp.buildmaster.interfaces.buildfarmbranchjob import IBuildFarmBranchJob
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJobSource
from lp.buildmaster.interfaces.buildqueue import IBuildQueueSet
from lp.buildmaster.model.buildfarmjob import (
    BuildFarmJobOld,
    BuildFarmJobOldDerived,
    )
from lp.buildmaster.model.buildqueue import BuildQueue
from lp.code.interfaces.branchjob import IRosettaUploadJobSource
from lp.code.model.branchjob import (
    BranchJob,
    BranchJobDerived,
    BranchJobType,
    )
from lp.translations.interfaces.translationtemplatesbuild import (
    ITranslationTemplatesBuildSource,
    )
from lp.translations.interfaces.translationtemplatesbuildjob import (
    ITranslationTemplatesBuildJobSource,
    )
from lp.translations.pottery.detect_intltool import is_intltool_structure


HARDCODED_TRANSLATIONTEMPLATESBUILD_SCORE = 2510


class TranslationTemplatesBuildJob(BuildFarmJobOldDerived, BranchJobDerived):
    """An `IBuildFarmJob` implementation that generates templates.

    Implementation-wise, this is actually a `BranchJob`.
    """
    implements(IBuildFarmBranchJob)
    class_job_type = BranchJobType.TRANSLATION_TEMPLATES_BUILD

    classProvides(ITranslationTemplatesBuildJobSource)

    duration_estimate = timedelta(seconds=10)

    unsafe_chars = '[^a-zA-Z0-9_+-]'

    def __init__(self, branch_job):
        super(TranslationTemplatesBuildJob, self).__init__(branch_job)

    def _set_build_farm_job(self):
        """Setup the IBuildFarmJob delegate.

        We override this to provide a non-database delegate that simply
        provides required functionality to the queue system."""
        self.build_farm_job = BuildFarmJobOld()

    def score(self):
        """See `IBuildFarmJob`."""
        # Hard-code score for now.  Most PPA jobs start out at 2505;
        # TranslationTemplateBuildJobs are fast so we want them at a
        # higher priority.
        return HARDCODED_TRANSLATIONTEMPLATESBUILD_SCORE

    def getLogFileName(self):
        """See `IBuildFarmJob`."""
        sanitized_name = re.sub(self.unsafe_chars, '_', self.getName())
        return "translationtemplates_%s" % sanitized_name

    def getName(self):
        """See `IBuildFarmJob`."""
        buildqueue = getUtility(IBuildQueueSet).getByJob(self.job)
        return '%s-%d' % (self.branch.name, buildqueue.id)

    def getTitle(self):
        """See `IBuildFarmJob`."""
        return '%s translation templates build' % self.branch.bzr_identity

    def cleanUp(self):
        """See `IBuildFarmJob`."""
        # This class is not itself database-backed.  But it delegates to
        # one that is.  We can't call its SQLObject destroySelf method
        # though, because then the BuildQueue and the BranchJob would
        # both try to delete the attached Job.
        Store.of(self.context).remove(self.context)

    @property
    def build(self):
        """Return a TranslationTemplateBuild for this build job."""
        build_id = self.context.metadata.get('build_id', None)
        if build_id is None:
            return None
        else:
            return getUtility(ITranslationTemplatesBuildSource).getByID(
                int(build_id))

    @classmethod
    def _hasPotteryCompatibleSetup(cls, branch):
        """Does `branch` look as if pottery can generate templates for it?

        :param branch: A `Branch` object.
        """
        bzr_branch = removeSecurityProxy(branch).getBzrBranch()
        return is_intltool_structure(bzr_branch.basis_tree())

    @classmethod
    def generatesTemplates(cls, branch):
        """See `ITranslationTemplatesBuildJobSource`."""
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
    def create(cls, branch, testing=False):
        """See `ITranslationTemplatesBuildJobSource`."""
        logger = logging.getLogger('translation-templates-build')
        # XXX Danilo Segan bug=580429: we hard-code processor to the Ubuntu
        # default processor architecture.  This stops the buildfarm from
        # accidentally dispatching the jobs to private builders.
        processor = cls._getBuildArch()

        build_farm_job = getUtility(IBuildFarmJobSource).new(
            BuildFarmJobType.TRANSLATIONTEMPLATESBUILD, processor=processor)
        build = getUtility(ITranslationTemplatesBuildSource).create(
            build_farm_job, branch)
        logger.debug(
            "Made BuildFarmJob %s, TranslationTemplatesBuild %s.",
            build_farm_job.id, build.id)

        specific_job = build.makeJob()
        if testing:
            removeSecurityProxy(specific_job)._constructed_build = build
        logger.debug("Made %s.", specific_job)

        duration_estimate = cls.duration_estimate

        build_queue_entry = BuildQueue(
            estimated_duration=duration_estimate,
            job_type=BuildFarmJobType.TRANSLATIONTEMPLATESBUILD,
            job=specific_job.job, processor=processor)
        IMasterStore(BuildQueue).add(build_queue_entry)

        logger.debug("Made BuildQueue %s.", build_queue_entry.id)

        return specific_job

    @classmethod
    def _getBuildArch(cls):
        """Returns an `IProcessor` to queue a translation build for."""
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        # A round-about way of hard-coding i386.
        return ubuntu.currentseries.nominatedarchindep.default_processor

    @classmethod
    def scheduleTranslationTemplatesBuild(cls, branch):
        """See `ITranslationTemplatesBuildJobSource`."""
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
                cls.create(branch)
        except Exception, e:
            logger.error(e)
            raise

    @classmethod
    def getByJob(cls, job):
        """See `IBuildFarmJob`.

        Overridden here to search via a BranchJob, rather than a Job.
        """
        store = IStore(BranchJob)
        branch_job = store.find(BranchJob, BranchJob.job == job).one()
        if branch_job is None:
            return None
        else:
            return cls(branch_job)

    @classmethod
    def getByBranch(cls, branch):
        """See `ITranslationTemplatesBuildJobSource`."""
        store = IStore(BranchJob)
        branch_job = store.find(BranchJob, BranchJob.branch == branch).one()
        if branch_job is None:
            return None
        else:
            return cls(branch_job)
