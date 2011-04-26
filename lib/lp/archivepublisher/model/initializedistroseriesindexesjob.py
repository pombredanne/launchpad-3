# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Job to initialize a distroseries' archive indexes."""

__metaclass__ = type
__all__ = [
    'InitializeDistroSeriesIndexesJob',
    ]

from optparse import OptionParser
from storm.locals import Store
from textwrap import dedent
import transaction
from zope.component import getUtility
from zope.interface import (
    classProvides,
    implements,
    )

from canonical.config import config
from canonical.launchpad.interfaces.lpstorm import IMasterStore
from lp.archivepublisher.interfaces.initializedistroseriesindexesjob import (
    IInitializeDistroSeriesIndexesJobSource,
    )
from lp.archivepublisher.interfaces.publisherconfig import IPublisherConfigSet
from lp.registry.interfaces.pocket import pocketsuffix
from lp.services.features import getFeatureFlag
from lp.services.job.interfaces.job import IRunnableJob
from lp.services.mail.sendmail import (
    format_address_for_person,
    MailController,
    )
from lp.soyuz.interfaces.distributionjob import (
    DistributionJobType,
    IDistributionJob,
    )
from lp.soyuz.model.distributionjob import (
    DistributionJob,
    DistributionJobDerived,
    )
from lp.soyuz.scripts import publishdistro


FEATURE_FLAG_ENABLE_MODULE = u"archivepublisher.auto_create_indexes.enabled"


def get_addresses_for(person):
    """Get list of contact email address(es) for `person`."""
    if person.is_team:
        return [
        format_address_for_person(member)
        for member in person.getMembersWithPreferredEmails()]
    else:
        return [format_address_for_person(person)]


class InitializeDistroSeriesIndexesJob(DistributionJobDerived):
    """Job to initialize a distroseries's archive indexes.

    To do this it runs publish-distro on the distribution, in careful mode.
    """
    implements(IDistributionJob, IRunnableJob)
    classProvides(IInitializeDistroSeriesIndexesJobSource)

    class_job_type = DistributionJobType.INITIALIZEDISTROSERIESINDEXES

    # Injection point for tests: optional publish_distro logger.
    logger = None

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
        if not getFeatureFlag(FEATURE_FLAG_ENABLE_MODULE):
            return None

        distro = distroseries.distribution
        config_set = getUtility(IPublisherConfigSet)
        publisher_config = config_set.getByDistribution(distro)
        if publisher_config is None:
            return None
        else:
            return cls.create(distroseries)

    def run(self):
        """See `IRunnableJob`."""
        self.runPublishDistro()
        if self.distribution.getArchiveByComponent('partner') is not None:
            self.runPublishDistro('--partner')

        self.notifySuccess()

    def getOperationDescription(self):
        """See `IRunnableJob`."""
        return "initializing archive indexes for %s" % self.distroseries.title

    def getSuites(self):
        """List the suites for this `DistroSeries`."""
        series_name = self.distroseries.name
        return [series_name + suffix for suffix in pocketsuffix.itervalues()]

    def runPublishDistro(self, extra_args=None):
        """Invoke the publish-distro script to initialize indexes.

        Publishes only the distroseries in question, in careful mode.
        """
        arguments = [
            "-A",
            "-d", self.distribution.name,
            ]
        for suite in self.getSuites():
            arguments += ["-s", suite]
        if extra_args is not None:
            arguments.append(extra_args)

        parser = OptionParser()
        publishdistro.add_options(parser)
        options, args = parser.parse_args(arguments)
        publishdistro.run_publisher(options, transaction, self.logger)

    def getMailRecipients(self):
        """List email addresses to notify of success or failure."""
        recipient = self.distroseries.driver or self.distribution.owner
        return get_addresses_for(recipient)

    def notifySuccess(self):
        """Notify the distribution's owners of success."""
        subject = "Launchpad has created archive indexes for %s." % (
            self.distroseries.name)
        message = dedent("""\
            You are receiving this email because you are registered in
            Launchpad as a release manager for %s.

            The archive indexes for %s have been successfully created.

            This automated process is one of many steps in setting up a
            new distribution release series in Launchpad.  The fact that
            this part of the work is now done may mean that you can now
            proceed with subsequent steps.

            This is an automated email; please do not reply.  Contact
            the Launchpad development team if you have any problems.
            """ % (self.distribution.displayname, self.distroseries.title))
        from_addr = config.canonical.noreply_from_address
        controller = MailController(
            from_addr, self.getMailRecipients(), subject, message)
        if controller is not None:
            controller.send()

    def getErrorRecipients(self):
        """See `BaseRunnableJob`."""
        return self.getMailRecipients()

    def destroySelf(self):
        """See `IDistributionJob`."""
        Store.of(self.context).remove(self.context)
