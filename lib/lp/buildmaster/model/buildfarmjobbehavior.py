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


class BuildFarmJobBehaviorBase:
    """Ensures that all behaviors inherit the same initialisation.

    All build-farm job behaviors should inherit from this.
    """

    def __init__(self, job_type):
        """
        Store a reference to the job_type with which we were created.
        """
        self._job_type = job_type


class IdleBuildBehavior(BuildFarmJobBehaviorBase):

    implements(IBuildFarmJobBehavior)

    def logStartBuild(self, build_queue_item, logger):
        """See `IBuildFarmJobBehavior`."""
        raise BuildBehaviorMismatch(
            "Builder was idle when asked to log the start of a build.")
