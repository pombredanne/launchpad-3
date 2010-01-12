# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Code to build recipes on the buildfarm."""

__metaclass__ = type
__all__ = [
    'RecipeBuildBehavior',
    ]

from zope.component import adapts
from zope.interface import implements

from canonical.cachedproperty import cachedproperty

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

    @cachedproperty
    def build(self):
        return self.buildfarmjob.build

    @property
    def displayName(self):
        sp = self.build.distroseries.getSourcePackage(
            self.build.sourcepackagename)
        ret = "%s, %s" % (
            sp.path, self.build.recipe.name)
        if self._builder is not None:
            ret += " (on %s)" % self._builder.url
        return ret

    def logStartBuild(self, logger):
        """See `IBuildFarmJobBehavior`."""
        logger.info("startBuild(%s)", self.displayName)

    def dispatchBuildToSlave(self, build_queue_id, logger):
        """See `IBuildFarmJobBehavior`."""
