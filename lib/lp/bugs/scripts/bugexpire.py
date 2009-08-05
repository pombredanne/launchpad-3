# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""BugTask expiration rules."""

__metaclass__ = type

__all__ = ['BugJanitor']


from logging import getLogger

from zope.component import getUtility
from zope.event import notify
from zope.interface import providedBy

from lazr.lifecycle.snapshot import Snapshot

from canonical.config import config
from lazr.lifecycle.event import ObjectModifiedEvent
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from lp.bugs.interfaces.bugtask import BugTaskStatus, IBugTaskSet
from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility
from canonical.launchpad.webapp.interaction import (
    setupInteraction, endInteraction)


class BugJanitor:
    """Expire Incomplete BugTasks that are older than a configurable period.
    
    The BugTask must be unassigned, and the project it is associated with
    must use Malone for bug tracking.
    """

    def __init__(self, days_before_expiration=None, log=None):
        """Create a new BugJanitor.

        :days_before_expiration: Days of inactivity before a question is
            expired. Defaults to config.malone.days_before_expiration.
        :log: A logger instance to use for logging. Defaults to the default
            logger.
        """

        if days_before_expiration is None:
            days_before_expiration = (config.malone.days_before_expiration)

        if log is None:
            log = getLogger()
        self.days_before_expiration = days_before_expiration
        self.log = log

        self.janitor = getUtility(ILaunchpadCelebrities).janitor

    def expireBugTasks(self, transaction_manager):
        """Expire old, unassigned, Incomplete BugTasks.

        Only BugTasks for projects that use Malone are updated. This method
        will login as the bug_watch_updater celebrity and logout after the
        expiration is done.
        """
        message_template = ('[Expired for %s because there has been no '
            'activity for %d days.]')
        self.log.info(
            'Expiring unattended, INCOMPLETE bugtasks older than '
            '%d days for projects that use Launchpad Bugs.' %
            self.days_before_expiration)
        self._login()
        try:
            expired_count = 0
            bugtask_set = getUtility(IBugTaskSet)
            incomplete_bugtasks = bugtask_set.findExpirableBugTasks(
                self.days_before_expiration, user=self.janitor)
            self.log.info(
                'Found %d bugtasks to expire.' % incomplete_bugtasks.count())
            for bugtask in incomplete_bugtasks:
                # We don't expire bugtasks with conjoined masters.
                if bugtask.conjoined_master:
                    continue

                bugtask_before_modification = Snapshot(
                    bugtask, providing=providedBy(bugtask))
                bugtask.transitionToStatus(
                    BugTaskStatus.INVALID, self.janitor)
                content = message_template % (
                    bugtask.bugtargetdisplayname, self.days_before_expiration)
                bugtask.bug.newMessage(
                    owner=self.janitor,
                    subject=bugtask.bug.followup_subject(),
                    content=content)
                bugtask.statusexplanation = content
                notify(ObjectModifiedEvent(
                    bugtask, bugtask_before_modification,
                    ['status', 'statusexplanation'], user=self.janitor))
                # XXX sinzui 2007-08-02 bug=29744:
                # We commit after each expiration because emails are sent
                # immediately in zopeless. This minimize the risk of
                # duplicate expiration emails being sent in case an error
                # occurs later on.
                transaction_manager.commit()
                expired_count += 1
            self.log.info('Expired %d bugtasks.' % expired_count)
        finally:
            self._logout()
        self.log.info('Finished expiration run.')

    def _login(self):
        """Setup an interaction as the bug janitor.
        
        The role of bug janitor is usually played by bug_watch_updater.
        """
        auth_utility = getUtility(IPlacelessAuthUtility)
        janitor_email = self.janitor.preferredemail.email
        setupInteraction(
            auth_utility.getPrincipalByLogin(
                janitor_email, want_password=False),
            login=janitor_email)

    def _logout(self):
        """End the bug janitor interaction."""
        endInteraction()
