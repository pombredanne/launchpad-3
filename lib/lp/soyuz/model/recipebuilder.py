# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Code to build recipes on the buildfarm."""

__metaclass__ = type
__all__ = [
    'RecipeBuildBehavior',
    ]

from zope.component import adapts
from zope.interface import implements

from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    IBuildFarmJobBehavior)
from lp.soyuz.interfaces.sourcepackagebuild import (
    IBuildSourcePackageFromRecipeJob)
from lp.buildmaster.model.buildfarmjobbehavior import (
    BuildFarmJobBehaviorBase)


class RecipeBuildBehavior(BuildFarmJobBehaviorBase):
    """How to build a recipe on the build farm."""

    adapts(IBuildSourcePackageFromRecipeJob)
    implements(IBuildFarmJobBehavior)

    status = None

    def logStartBuild(self, logger):
        """See `IBuildFarmJobBehavior`."""

    def dispatchBuildToSlave(self, build_queue_id, logger):
        """See `IBuildFarmJobBehavior`."""
