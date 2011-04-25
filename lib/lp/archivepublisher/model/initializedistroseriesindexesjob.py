# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Job to initialize a distroseries' archive indexes."""

__metaclass__ = type
__all__ = [
    'InitializeDistroSeriesIndexesJob',
    ]

from zope.interface import (
    classProvides,
    implements,
    )

from lp.archivepublisher.interfaces.initializedistroseriesindexesjob import (
    IInitializeDistroSeriesIndexesJobSource,
    )
from lp.services.job import IRunnableJob
from lp.soyuz.interfaces.distributionjob import IDistributionJob
from lp.soyuz.model.distributionjob import DistributionJobDerived


class InitializeDistroSeriesIndexesJob(DistributionJobDerived):
    """Job to initialize a distroseries's archive indexes.

    To do this it runs publish-distro on the distribution, in careful mode.
    """
    implements(IDistributionJob, IRunnableJob)
    classProvides(IInitializeDistroSeriesIndexesJobSource)

    @classmethod
    def makeFor(cls, distroseries):
        """See `IInitializeDistroSeriesIndexesJob`."""
        pass

    def run(self):
        """See `IRunnableJob`."""

    def getSuites(self):
        """List the suites for this `DistroSeries`."""

    def runPublishDistro(self, extra_args=None):
        """Invoke the publish-distro script to initialize indexes.

        Publishes only the distroseries in question, in careful mode.
        """

    def notifyOwners(self, message_text):
        """Notify the distribution's owners of success, or failure.

        :param message_text: Text of the message to send to the owners.
        """
