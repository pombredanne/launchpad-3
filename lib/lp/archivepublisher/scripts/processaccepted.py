# Copyright 2009-2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helper functions for the process-accepted.py script."""

__metaclass__ = type
__all__ = [
    'ProcessAccepted',
    ]

from optparse import OptionValueError
import sys

from zope.component import getUtility

from lp.archivepublisher.publishing import GLOBAL_PUBLISHER_LOCK
from lp.archivepublisher.scripts.base import PublisherScript
from lp.services.limitedlist import LimitedList
from lp.services.webapp.adapter import (
    clear_request_started,
    set_request_started,
    )
from lp.services.webapp.errorlog import (
    ErrorReportingUtility,
    ScriptRequest,
    )
from lp.soyuz.enums import (
    ArchivePurpose,
    PackageUploadStatus,
    )
from lp.soyuz.interfaces.archive import IArchiveSet
from lp.soyuz.model.processacceptedbugsjob import close_bugs_for_queue_item


class ProcessAccepted(PublisherScript):
    """Queue/Accepted processor.

    Given a distribution to run on, obtains all the queue items for the
    distribution and then gets on and deals with any accepted items, preparing
    them for publishing as appropriate.
    """

    @property
    def lockfilename(self):
        """See `LaunchpadScript`."""
        return GLOBAL_PUBLISHER_LOCK

    def add_my_options(self):
        """Command line options for this script."""
        self.addDistroOptions()

        self.parser.add_option(
            "--ppa", action="store_true", dest="ppa", default=False,
            help="Run only over PPA archives.")

        self.parser.add_option(
            "--copy-archives", action="store_true", dest="copy_archives",
            default=False, help="Run only over COPY archives.")

    def validateArguments(self):
        """Validate command-line arguments."""
        if self.options.ppa and self.options.copy_archives:
            raise OptionValueError(
                "Specify only one of copy archives or ppa archives.")
        if self.options.all_derived and self.options.distribution:
            raise OptionValueError(
                "Can't combine --derived with a distribution name.")

    def getTargetArchives(self, distribution):
        """Find archives to target based on given options."""
        if self.options.ppa:
            return distribution.getPendingAcceptancePPAs()
        elif self.options.copy_archives:
            return getUtility(IArchiveSet).getArchivesForDistribution(
                distribution, purposes=[ArchivePurpose.COPY])
        else:
            return distribution.all_distro_archives

    def processQueueItem(self, queue_item):
        """Attempt to process `queue_item`.

        This method swallows exceptions that occur while processing the
        item.

        :param queue_item: A `PackageUpload` to process.
        :return: True on success, or False on failure.
        """
        self.logger.debug("Processing queue item %d" % queue_item.id)
        try:
            queue_item.realiseUpload(self.logger)
        except Exception:
            message = "Failure processing queue_item %d" % queue_item.id
            properties = [('error-explanation', message)]
            request = ScriptRequest(properties)
            ErrorReportingUtility().raising(sys.exc_info(), request)
            self.logger.error('%s (%s)', message, request.oopsid)
            return False
        else:
            self.logger.debug(
                "Successfully processed queue item %d", queue_item.id)
            return True

    def processForDistro(self, distribution):
        """Process all queue items for a distribution.

        Commits between items.

        :param distribution: The `Distribution` to process queue items for.
        :return: A list of all successfully processed items' ids.
        """
        processed_queue_ids = []
        for archive in self.getTargetArchives(distribution):
            set_request_started(
                request_statements=LimitedList(10000),
                txn=self.txn, enable_timeout=False)
            try:
                for distroseries in distribution.series:

                    self.logger.debug("Processing queue for %s %s" % (
                        archive.reference, distroseries.name))

                    queue_items = distroseries.getPackageUploads(
                        status=PackageUploadStatus.ACCEPTED, archive=archive)
                    for queue_item in queue_items:
                        if self.processQueueItem(queue_item):
                            processed_queue_ids.append(queue_item.id)
                        # Commit even on error; we may have altered the
                        # on-disk archive, so the partial state must
                        # make it to the DB.
                        self.txn.commit()
                        close_bugs_for_queue_item(queue_item)
                        self.txn.commit()
            finally:
                clear_request_started()
        return processed_queue_ids

    def main(self):
        """Entry point for a LaunchpadScript."""
        self.validateArguments()
        try:
            for distro in self.findDistros():
                self.processForDistro(distro)
                self.txn.commit()
        finally:
            self.logger.debug("Rolling back any remaining transactions.")
            self.txn.abort()
        return 0
