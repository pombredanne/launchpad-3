# Copyright 2010 Canonical Ltd. This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'TranslationTemplatesBuildJob',
    ]

from datetime import timedelta
import re

from storm.store import Store
from zope.component import getUtility
from zope.interface import (
    classProvides,
    implements,
    )
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.launchpad.interfaces import ILaunchpadCelebrities
from canonical.launchpad.interfaces.lpstorm import (
    IMasterStore,
    IStore,
    )
from lp.buildmaster.interfaces.buildfarmbranchjob import IBuildFarmBranchJob
from lp.buildmaster.interfaces.buildfarmjob import BuildFarmJobType
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
from lp.translations.interfaces.translationtemplatesbuildjob import (
    ITranslationTemplatesBuildJobSource,
    )
from lp.translations.pottery.detect_intltool import is_intltool_structure


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
        # Hard-code score for now; anything other than 1000 is probably
        # inappropriate.
        return 1000

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
        if branch.private:
            # We don't support generating template from private branches
            # at the moment.
            return False

        utility = getUtility(IRosettaUploadJobSource)
        if not utility.providesTranslationFiles(branch):
            # Nobody asked for templates generated from this branch.
            return False

        if not cls._hasPotteryCompatibleSetup(branch):
            # Nothing we could do with this branch if we wanted to.
            return False

        # Yay!  We made it.
        return True

    @classmethod
    def create(cls, branch):
        """See `ITranslationTemplatesBuildJobSource`."""
        store = IMasterStore(BranchJob)

        # Pass public HTTP URL for the branch.
        metadata = {'branch_url': branch.composePublicURL()}
        branch_job = BranchJob(
            branch, BranchJobType.TRANSLATION_TEMPLATES_BUILD, metadata)
        store.add(branch_job)
        specific_job = TranslationTemplatesBuildJob(branch_job)
        duration_estimate = cls.duration_estimate

        # XXX Danilo Segan bug=580429: we hard-code processor to the Ubuntu
        # default processor architecture.  This stops the buildfarm from
        # accidentally dispatching the jobs to private builders.
        build_queue_entry = BuildQueue(
            estimated_duration=duration_estimate,
            job_type=BuildFarmJobType.TRANSLATIONTEMPLATESBUILD,
            job=specific_job.job.id,
            processor=cls._getBuildArch())
        store.add(build_queue_entry)

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
        if not config.rosetta.generate_templates:
            # This feature is disabled by default.
            return

        if cls.generatesTemplates(branch):
            # This branch is used for generating templates.
            cls.create(branch)

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
