# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Base and idle BuildFarmJobBehavior classes."""

__metaclass__ = type

__all__ = [
    'get_behavior_for_job_type',
    'BuildFarmJobBehaviorBase',
    'IdleBuildBehavior'
    ]

from zope.interface import implements

from lp.buildmaster.interfaces.buildfarmjob import BuildFarmJobType
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    BuildBehaviorMismatch, IBuildFarmJobBehavior)

# TODO: this should not need to be here... register adapters instead.
from lp.soyuz.model.binarypackagebuildbehavior import (
    BinaryPackageBuildBehavior)

# I've linked the job types to builder behaviors here temporarily
# via a factory, but there must be a better way.
# We could register a factory for each job_type like this
#
#    <adapter
#        for="lp.buildmaster.interfaces.IBinaryPackageJobType"
#        provides="lp.buildmaster.interfaces.IBuildFarmJobBehavior"
#        factory="lp.soyuz.model.BinaryPackageBuildBehavior"
#        permission="zope.Public" />
# but that requires creating a marker interface+class for each
# BuildFarmJobType DBItem or is there a better way? Perhaps
# just defining the marker interface and adding it at run-time?

job_type_behaviors = {
    BuildFarmJobType.PACKAGEBUILD: BinaryPackageBuildBehavior,
    }

def get_behavior_for_job_type(job_type):
    """A factory for creating build farm job behaviors.


    :param job_type: A BuildFarmJobType enum.
    :return: An implementation of IBuildFarmJobBehavior corresponding to
        the job_type, or None if no corresponding behavior is found.
    :raises BuildBehaviorMismatch: If a behavior matching the type was not
        found.
    """
    behavior_cls = job_type_behaviors.get(job_type, None)

    if behavior_cls is None:
        raise BuildBehaviorMismatch(
            "No matching behavior found for build farm job type '%s'" % (
                job_type.title))

    return behavior_cls()


#class BuildFarmJobBehaviorBase:
#    """Ensures that all behaviors inherit the same initialisation.
#
#    All build-farm job behaviors should inherit from this.
#    """
#
#    def __init__(self):
#        """
#        Store a reference to the builder as we'll need to access builder
#        attributes.
#        """
#        self._builder = builder


class IdleBuildBehavior:

    implements(IBuildFarmJobBehavior)

    def logStartBuild(self, build_queue_item, logger):
        """See `IBuildFarmJobBehavior`."""
        raise BuildBehaviorMismatch(
            "Builder was idle when asked to log the start of a build.")
