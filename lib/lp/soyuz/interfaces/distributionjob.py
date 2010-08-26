# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    "IDoDistributionJob",
    "IDoDistributionJobSource",
    "IDistributionJob",
    "IDistributionJobSource",
    "DistributionJobType",
]

from lazr.enum import DBEnumeratedType, DBItem
from zope.interface import Attribute, Interface
from zope.schema import Int, Object
                                                                              
from canonical.launchpad import _

from lp.services.job.interfaces.job import IJob, IJobSource, IRunnableJob
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distroseries import IDistroSeries


class IDistributionJob(Interface):
    """A Job that initialises a distro series, based on a parent."""
    
    id = Int(
        title=_('DB ID'), required=True, readonly=True,                       
        description=_("The tracking number for this job."))                   

    distribution = Object(
        title=_('The Distribution this job is about.'),
        schema=IDistribution, required=True)

    distroseries = Object(
        title=_('The DistroSeries this job is about.'),
        schema=IDistroSeries, required=False)

    job = Object(
        title=_('The common Job attributes'), schema=IJob, required=True)     
                                                                              
    metadata = Attribute('A dict of data about the job.')  

    def destroySelf():
        """Destroy this object."""


class IDistributionJobSource(IJobSource):
    """An interface for acquiring IDistributionJobs."""

    def create(distribution, distroseries):
        """Create a new IDistributionJob for a distribution."""


class DistributionJobType(DBEnumeratedType):

    DO_INITIALISE = DBItem(0, """
        Initialise a Distro Series.

        This job initialises a given distro series, creating builds, and
        populating the archive from the parent distroseries.
        """)


class IDoDistributionJob(IRunnableJob):
    """A Job that performs actions on a distribution."""
   

class IDoDistributionJobSource(IDistributionJobSource):
    """An interface for acquiring IDistributionJobs."""
    
