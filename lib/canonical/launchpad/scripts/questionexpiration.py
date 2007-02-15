# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

"""Question expiration logic."""

__metaclass__ = type

from logging import getLogger

from zope.component import getUtility

from canonical.config import config
from canonical.database.sqlbase import cursor, sqlvalues
from canonical.launchpad.interfaces import ILaunchpadCelebrities, IQuestionSet
from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility
from canonical.launchpad.webapp.interaction import (
    setupInteraction, endInteraction)


class QuestionJanitor:
    """Object that takes the responsability of expiring tickets
    without activity in a configurable period.
    """

    def __init__(self, days_before_expiration=None, log=None):
        """Create a new QuestionJanitor.

        :days_before_expiration: Days of inactivity before a ticket is
            expired. Defaults to config.tickettracker.days_before_expiration
        :log: A logger instance to use for logging. Defaults to the default
            logger.
        """

        if days_before_expiration is None:
            days_before_expiration = (
                config.tickettracker.days_before_expiration)

        if log is None:
            log = getLogger()
        self.days_before_expiration = days_before_expiration
        self.log = log

        self.janitor = (
            getUtility(ILaunchpadCelebrities).support_tracker_janitor)

    def expireQuestions(self, transaction_manager):
        """Expire old tickets.

        All tickets in the OPEN or NEEDSINFO state without activity
        in the last X days are expired.

        This method will login as the support_tracker_janitor celebrity and
        logout after the expiration is done.
        """
        self.log.info(
            'Expiring OPEN and NEEDSINFO tickets without activity for the '
            'last %d days.' % self.days_before_expiration)
        self._login()
        try:
            count = 0
            expired_tickets = getUtility(IQuestionSet).findExpiredQuestions(
                self.days_before_expiration)
            self.log.info(
                'Found %d tickets to expire.' % expired_tickets.count())
            for ticket in expired_tickets:
                ticket.expireQuestion(
                    self.janitor,
                    "This support request was expired because it remained in "
                    "the '%s' state without activity for the last %d days."
                        % (ticket.status.title, self.days_before_expiration))
                # XXX flacoste 2006/10/24 We commit after each and every
                # expiration because of bug #29744 (emails are sent
                # immediately in zopeless). This minimuze the risk of
                # duplicate expiration email being sent in case an error occurs
                # later on.
                transaction_manager.commit()
                count += 1
            self.log.info('Expired %d tickets.' % count)
        finally:
            self._logout()
        self.log.info('Finished expiration run.')


    def _login(self):
        """Setup an interaction as the Support Tracker Janitor."""
        auth_utility = getUtility(IPlacelessAuthUtility)
        janitor_email = self.janitor.preferredemail.email
        setupInteraction(
            auth_utility.getPrincipalByLogin(janitor_email),
            login=janitor_email)

    def _logout(self):
        """Removed the Support Tracker Janitor interaction."""
        endInteraction()
