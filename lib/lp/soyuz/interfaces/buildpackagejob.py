# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""BuildPackageJob interfaces."""

__metaclass__ = type

__all__ = [
    'IBuildPackageJob',
    ]

from zope.interface import Interface
from zope.schema import Int

from canonical.launchpad import _
from lazr.restful.fields import Reference
from lp.services.job.interfaces.job import IJob
from lp.soyuz.interfaces.build import IBuild
from lp.soyuz.interfaces.soyuzjob import ISoyuzJob


class IBuildPackageJob(ISoyuzJob):
    """A read-only interface for build package jobs."""
    id = Int(title=_('ID'), required=True, readonly=True)

    job = exported(Reference(
        IJob, title=_("General build job data"), required=True, readonly=True,
        description=_("General data about this build job.")))

    build = exported(Reference(
        IBuild, title=_("Associated build record"),
        required=True,readonly=True,
        description=_("The build record associated with this job.")))
