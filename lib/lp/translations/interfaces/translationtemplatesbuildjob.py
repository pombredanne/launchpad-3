# Copyright 2010 Canonical Ltd. This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0213

__metaclass__ = type

__all__ = [
    'ITranslationTemplatesBuildJob',
    'ITranslationTemplatesBuildJobSource',
    ]

from zope.interface import Interface

from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJob
from lp.code.interfaces.branchjob import IBranchJob


class ITranslationTemplatesBuildJob(IBranchJob, IBuildFarmJob):
    """Build-farm job type for generating translation templates."""


class ITranslationTemplatesBuildJobSource(Interface):
    """Container for `ITranslationTemplatesBuildJob`s."""

    def create(branch):
        """Create new `ITranslationTemplatesBuildJob`.

        Also creates the matching `IBuildQueue` and `IJob`.

        :param branch: A `Branch` that this job will check out and
            generate templates for.
        :return: A new `ITranslationTemplatesBuildJob`.
        """

    def getForJob(job):
        """Find `ITranslationTemplatesBuildJob` matching given `Job`."""
