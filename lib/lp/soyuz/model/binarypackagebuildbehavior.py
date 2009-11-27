# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Builder behavior for binary package builds."""

__metaclass__ = type

__all__ = [
    'BinaryPackageBuildBehavior',
    ]

from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    IBuildFarmJobBehavior)
from lp.buildmaster.model.buildfarmjobbehavior import (
    BuildFarmJobBehaviorBase)
from lp.soyuz.interfaces.build import IBuildSet

from zope.component import getUtility
from zope.interface import implements


class BinaryPackageBuildBehavior(BuildFarmJobBehaviorBase):
    """Define the behavior of binary package builds."""

    implements(IBuildFarmJobBehavior)

    def logStartBuild(self, build_queue_item, logger):
        """See `IBuildFarmJobBehavior`.""" 
        build = getUtility(IBuildSet).getByQueueEntry(build_queue_item)
        spr = build.sourcepackagerelease

        # Gar - need a reference back to the builder for self.url

        logger.info("startBuild(%s, %s, %s, %s)", self._builder.url,
                    spr.name, spr.version, build.pocket.title)
