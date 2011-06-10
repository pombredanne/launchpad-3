# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""BuildPackageJob interfaces."""

__metaclass__ = type

__all__ = [
    'IBuildPackageJob',
    ]

from lazr.restful.fields import Reference
from zope.schema import Int

from canonical.launchpad import _
from lp.services.job.interfaces.job import IJob
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuild
from lp.soyuz.interfaces.buildfarmbuildjob import IBuildFarmBuildJob


class IBuildPackageJob(IBuildFarmBuildJob):
    """A read-only interface for build package jobs."""

    id = Int(title=_('ID'), required=True, readonly=True)

    job = Reference(
        IJob, title=_("Job"), required=True, readonly=True,
        description=_("Data common to all job types."))

    build = Reference(
        IBinaryPackageBuild, title=_("Build"),
        required=True, readonly=True,
        description=_("Build record associated with this job."))
