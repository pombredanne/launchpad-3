# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0703

"""Verify (and refresh) `POFile`s' cached statistics."""

__metaclass__ = type
__all__ = ['VerifyPOFileStatsProcess']


from datetime import (
    datetime,
    timedelta,
    )
import logging

import pytz
from zope.component import getUtility
from zope.interface import implements

from canonical.config import config
from canonical.launchpad import helpers
from canonical.launchpad.interfaces.looptuner import ITunableLoop
from canonical.launchpad.mailnotification import MailWrapper
from canonical.launchpad.utilities.looptuner import DBLoopTuner
from lp.services.mail.sendmail import simple_sendmail
from lp.translations.interfaces.pofile import IPOFileSet


class Verifier:
    """`ITunableLoop` that recomputes & checks all `POFile`s' statistics."""
    implements(ITunableLoop)

    total_checked = 0
    total_incorrect = 0
    total_exceptions = 0

    def __init__(self, transaction, logger, start_at_id=0):
        self.transaction = transaction
        self.logger = logger
        self.start_id = start_at_id
        self.pofileset = getUtility(IPOFileSet)

    def isDone(self):
        """See `ITunableLoop`."""
        # When the main loop hits the end of the POFile table, it sets
        # start_id to None.  Until we know we hit the end, it always has a
        # numerical value.
        return self.start_id is None

    def getPOFilesBatch(self, chunk_size):
        """Return a batch of POFiles to work with."""
        pofiles = self.pofileset.getBatch(self.start_id, int(chunk_size))
        return pofiles

    def __call__(self, chunk_size):
        """See `ITunableLoop`.

        Retrieve a batch of `POFile`s in ascending id order, and verify and
        refresh their cached statistics.
        """
        pofiles = self.getPOFilesBatch(chunk_size)

        self.start_id = None
        for pofile in pofiles:
            self.total_checked += 1
            # Set starting point of next batch to right after the POFile we're
            # looking at.  If we don't get any POFiles, this loop iterates
            # zero times and start_id will remain set to None.
            self.start_id = pofile.id + 1
            try:
                self._verify(pofile)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception, error:
                # Verification failed for this POFile.  Don't bail out: if
                # there's a pattern of failure, we'll want to report that and
                # not just the first problem we encounter.
                self.total_exceptions += 1
                self.logger.warning(
                    "Error %s while recomputing stats for POFile %d: %s"
                    % (type(error), pofile.id, error))

        self.transaction.commit()
        self.transaction.begin()

    def _verify(self, pofile):
        """Re-compute statistics for pofile, and compare to cached stats.

        Logs a warning if the recomputed stats do not match the ones stored in
        the database.  The stored statistics are replaced with the freshly
        computed ones.
        """
        old_stats = pofile.getStatistics()
        new_stats = pofile.updateStatistics()
        if new_stats != old_stats:
            self.total_incorrect += 1
            self.logger.info(
                "POFile %d: cached stats were %s, recomputed as %s"
                % (pofile.id, str(old_stats), str(new_stats)))


class QuickVerifier(Verifier):
    """`ITunableLoop` to verify statistics on POFiles touched recently."""

    def __init__(self, transaction, logger, start_at_id=0):
        super(QuickVerifier, self).__init__(transaction, logger, start_at_id)
        days_considered_recent = int(
            config.rosetta_pofile_stats.days_considered_recent)
        cutoff_time = (
            datetime.now(pytz.UTC) - timedelta(days_considered_recent))
        self.touched_pofiles = self.pofileset.getPOFilesTouchedSince(
            cutoff_time)
        self.logger.info(
            "Verifying a total of %d POFiles." % self.touched_pofiles.count())

    def getPOFilesBatch(self, chunk_size):
        """Return a batch of POFiles to work with."""
        pofiles = self.touched_pofiles[
            self.total_checked: self.total_checked + int(chunk_size)]
        return pofiles


class VerifyPOFileStatsProcess:
    """Recompute & verify `POFile` translation statistics."""

    def __init__(self, transaction, logger=None, start_at_id=0):
        self.transaction = transaction
        self.logger = logger
        self.start_at_id = start_at_id
        if logger is None:
            self.logger = logging.getLogger("pofile-stats")

    def run(self):
        self.logger.info("Starting verification of POFile stats at id %d"
            % self.start_at_id)
        loop = Verifier(self.transaction, self.logger, self.start_at_id)

        # Since the script can run for a long time, our deployment
        # process might remove the Launchpad tree the script was run
        # from, thus the script failing to find the email template
        # if it was attempted after DBLoopTuner run is completed.
        # See bug #811447 for OOPS we used to get then.
        template = helpers.get_email_template(
            'pofile-stats.txt', 'translations')

        # Each iteration of our loop collects all statistics first, before
        # modifying any rows in the database.  With any locks on the database
        # acquired only at the very end of the iteration, we can afford to
        # make relatively long, low-overhead iterations without disrupting
        # application response times.
        iteration_duration = (
            config.rosetta_pofile_stats.looptuner_iteration_duration)
        DBLoopTuner(loop, iteration_duration).run()

        if loop.total_incorrect > 0 or loop.total_exceptions > 0:
            # Not all statistics were correct, or there were failures while
            # checking them.  Email the admins.
            message = template % {
                'exceptions': loop.total_exceptions,
                'errors': loop.total_incorrect,
                'total': loop.total_checked}
            simple_sendmail(
                from_addr=config.rosetta.admin_email,
                to_addrs=[config.rosetta.admin_email],
                subject="POFile statistics errors",
                body=MailWrapper().format(message))
            self.transaction.commit()

        self.logger.info("Done.")


class VerifyRecentPOFileStatsProcess:
    """Recompute & verify `POFile` translation statistics."""

    def __init__(self, transaction, logger=None):
        self.transaction = transaction
        self.logger = logger
        if logger is None:
            self.logger = logging.getLogger("pofile-stats-daily")

    def run(self):
        self.logger.info(
            "Verifying stats of POFiles updated in the last %s days." % (
                config.rosetta_pofile_stats.days_considered_recent))
        loop = QuickVerifier(self.transaction, self.logger)
        iteration_duration = (
            config.rosetta_pofile_stats.looptuner_iteration_duration)
        DBLoopTuner(loop, iteration_duration).run()

        if loop.total_incorrect > 0 or loop.total_exceptions > 0:
            # Not all statistics were correct, or there were failures while
            # checking them.  Email the admins.
            template = helpers.get_email_template(
                'pofile-stats.txt', 'translations')
            message = template % {
                'exceptions': loop.total_exceptions,
                'errors': loop.total_incorrect,
                'total': loop.total_checked}
            simple_sendmail(
                from_addr=config.rosetta.admin_email,
                to_addrs=[config.rosetta.admin_email],
                subject="POFile statistics errors (daily)",
                body=MailWrapper().format(message))
            self.transaction.commit()

        self.logger.info("Done.")
