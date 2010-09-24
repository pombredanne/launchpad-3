# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface and utility for `TranslationTemplatesBuild`."""

__metaclass__ = type
__all__ = [
    'ITranslationTemplatesBuild',
    'ITranslationTemplatesBuildSource',
    ]

from lazr.restful.fields import Reference
from zope.interface import Interface

from canonical.launchpad import _
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJob
from lp.code.interfaces.branch import IBranch


class ITranslationTemplatesBuild(IBuildFarmJob):
    """The build information for translation templates builds."""

    build_farm_job = Reference(
        title=_("The build farm job that this extends."),
        required=True, readonly=True, schema=IBuildFarmJob)

    branch = Reference(
        title=_("The branch that this build operates on."),
        required=True, readonly=True, schema=IBranch)


class ITranslationTemplatesBuildSource(Interface):
    """Utility for `ITranslationTemplatesBuild`."""

    def create(build_farm_job, branch):
        """Create a new `ITranslationTemplatesBuild`."""

    def findByBranch(branch, store=None):
        """Find `ITranslationTemplatesBuild`s for `branch`."""

    def get(build_id, store=None):
        """Find `ITranslationTemplatesBuild`s by id.

        :param build_id: Numerical id to look for.
        :param store: Optional database store to look in.
        """

    def getByBuildFarmJob(buildfarmjob_id, store=None):
        """Find `ITranslationTemplatesBuild`s by `BuildFarmJob` id."""
