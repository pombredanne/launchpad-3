# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface and utility for `TranslationTemplatesBuild`."""

__metaclass__ = type
__all__ = [
    'ITranslationTemplatesBuild',
    'ITranslationTemplatesBuildSource',
    ]

from lazr.restful.fields import Reference

from lp import _
from lp.buildmaster.interfaces.buildfarmjob import (
    IBuildFarmJob,
    ISpecificBuildFarmJobSource,
    )
from lp.code.interfaces.branch import IBranch


class ITranslationTemplatesBuild(IBuildFarmJob):
    """The build information for translation templates builds."""

    branch = Reference(
        title=_("The branch that this build operates on."),
        required=True, readonly=True, schema=IBranch)


class ITranslationTemplatesBuildSource(ISpecificBuildFarmJobSource):
    """Utility for `ITranslationTemplatesBuild`."""

    def create(branch):
        """Create a new `ITranslationTemplatesBuild`."""

    def findByBranch(branch, store=None):
        """Find `ITranslationTemplatesBuild`s for `branch`."""

    def generatesTemplates(branch):
        """Can this branch usefully generate translation templates?

        If yes, then use `create` to schedule a build-farm job to
        generate the templates based on the source code in the branch.
        """

    def scheduleTranslationTemplatesBuild(branch):
        """Schedule a translation templates build job, if appropriate."""
