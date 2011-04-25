# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Job to initialize a distroseries' archive indexes."""

__metaclass__ = type
__all__ = [
    'InitializeDistroSeriesIndexesJob',
    ]

from zope.component import getUtility
from zope.interface import (
    classProvides,
    implements,
    )

from canonical.launchpad.interfaces.lpstorm import IMasterStore
from lp.archivepublisher.interfaces.initializedistroseriesindexesjob import (
    IInitializeDistroSeriesIndexesJobSource,
    )
from lp.archivepublisher.interfaces.publisherconfig import IPublisherConfigSet
from lp.registry.interfaces.pocket import pocketsuffix
from lp.services.job.interfaces.job import IRunnableJob
from lp.soyuz.interfaces.distributionjob import (
    DistributionJobType,
    IDistributionJob,
    )
from lp.soyuz.model.distributionjob import (
    DistributionJob,
    DistributionJobDerived,
    )


class InitializeDistroSeriesIndexesJob(DistributionJobDerived):
    """Job to initialize a distroseries's archive indexes.

    To do this it runs publish-distro on the distribution, in careful mode.
    """
    implements(IDistributionJob, IRunnableJob)
    classProvides(IInitializeDistroSeriesIndexesJobSource)

    class_job_type = DistributionJobType.INITIALIZEDISTROSERIESINDEXES

    @classmethod
    def create(cls, distroseries):
        job = DistributionJob(
            distroseries.distribution, distroseries, cls.class_job_type,
            metadata={})
        IMasterStore(DistributionJob).add(job)
        return cls(job)

    @classmethod
    def makeFor(cls, distroseries):
        """See `IInitializeDistroSeriesIndexesJob`."""
        distro = distroseries.distribution
        config_set = getUtility(IPublisherConfigSet)
        publisher_config = config_set.getByDistribution(distro)
        if publisher_config is None:
            return None
        else:
            return cls.create(distroseries)

    def run(self):
        """See `IRunnableJob`."""
# XXX: Implement

    def getSuites(self):
        """List the suites for this `DistroSeries`."""
        series_name = self.distroseries.name
        return [series_name + suffix for suffix in pocketsuffix.itervalues()]

    def runPublishDistro(self, extra_args=None):
        """Invoke the publish-distro script to initialize indexes.

        Publishes only the distroseries in question, in careful mode.
        """
# XXX: Implement

    def notifyOwners(self, message_text):
        """Notify the distribution's owners of success, or failure.

        :param message_text: Text of the message to send to the owners.
        """
# XXX: Implement

    def getErrorRecipients(self):
        """See `BaseRunnableJob`."""
# XXX: Implement
