# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    "IDoInitialiseDistroSeriesJob",
    "IDoInitialiseDistroSeriesJobSource",
    "IInitialiseDistroSeriesJob",
    "IInitialiseDistroSeriesJobSource",
]

from lazr.enum import DBEnumeratedType, DBItem
from zope.interface import Attribute, Interface
from zope.schema import Int, Object
                                                                              
from canonical.launchpad import _

from lp.services.job.interfaces.job import IJob, IJobSource, IRunnableJob
from lp.registry.interfaces.distroseries import IDistroSeries


class IInitialiseDistroSeriesJob(Interface):
    """A Job that initialises a distro series, based on a parent."""
    
    id = Int(
        title=_('DB ID'), required=True, readonly=True,                       
        description=_("The tracking number for this job."))                   

    distroseries = Object(
        title=_('The DistroSeries this job is about.'), schema=IDistroSeries,
        required=True)

    job = Object(
        title=_('The common Job attributes'), schema=IJob, required=True)     
                                                                              
    metadata = Attribute('A dict of data about the job.')  

    def destroySelf():
        """Destroy this object."""


class IInitialiseDistroSeriesJobSource(IJobSource):
    """An interface for acquiring IInitialiseDistroSeriesJobs."""

    def create(distroseries):
        """Create a new IInitialiseDistroSeriesJobs for a distroseries."""


class IDoInitialiseDistroSeriesJob(IRunnableJob):
    """A Job that initialises a distro series, based on a parent."""
   

class IDoInitialiseDistroSeriesJobSource(IInitialiseDistroSeriesJobSource):
    """An interface for acquiring IInitialiseDistroSeriesJobs."""
    
