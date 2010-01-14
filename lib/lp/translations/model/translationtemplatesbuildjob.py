# Copyright 2010 Canonical Ltd. This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'TranslationTemplatesBuildJob',
    ]

import re
from datetime import timedelta

from zope.component import getUtility
from zope.interface import classProvides, implements

from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR, IStoreSelector, MAIN_STORE, MASTER_FLAVOR)

from lp.buildmaster.interfaces.buildfarmjob import BuildFarmJobType
from lp.buildmaster.model.buildfarmjob import BuildFarmJob
from lp.code.model.branchjob import BranchJob, BranchJobDerived, BranchJobType
from lp.soyuz.model.buildqueue import BuildQueue
from lp.translations.interfaces.translationtemplatesbuildjob import (
    ITranslationTemplatesBuildJob, ITranslationTemplatesBuildJobSource)


class TranslationTemplatesBuildJob(BranchJobDerived, BuildFarmJob):
    """An `IBuildFarmJob` implementation that generates templates.

    Implementation-wise, this is actually a `BranchJob`.
    """
    implements(ITranslationTemplatesBuildJob)
    classProvides(ITranslationTemplatesBuildJobSource)

    duration_estimate = timedelta(seconds=10)

    unsafe_chars = '[^a-zA-Z0-9_+-]'

    def __init__(self, branch_job):
        super(TranslationTemplatesBuildJob, self).__init__(branch_job)

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
        return '%s-%d' % (self.branch.name, self.job.id)

    def getTitle(self):
        """See `IBuildFarmJob`."""
        return '%s translation templates build' % self.branch.bzr_identity

    @classmethod
    def create(cls, branch):
        """See `ITranslationTemplatesBuildJobSource`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)

        # We don't have any JSON metadata for this BranchJob type.
        metadata = {}
        branch_job = BranchJob(
            branch, BranchJobType.TRANSLATION_TEMPLATES_BUILD, metadata)
        store.add(branch_job)
        specific_job = TranslationTemplatesBuildJob(branch_job)

        duration_estimate = cls.duration_estimate
        build_queue_entry = BuildQueue(
            estimated_duration=duration_estimate,
            job_type=BuildFarmJobType.TRANSLATIONTEMPLATESBUILD,
            job=specific_job.job.id)
        store.add(build_queue_entry)

        return specific_job

    @classmethod
    def getForJob(cls, job):
        """See `ITranslationTemplatesBuildJobSource`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        branch_job = store.find(BranchJob, BranchJob.job == job).one()
        if branch_job is None:
            return None
        else:
            return cls(branch_job)
