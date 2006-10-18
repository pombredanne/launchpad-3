# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Ticket expiration logic."""

__metaclass__ = type

from logging import getLogger

from zope.component import getUtility

from canonical.config import config
from canonical.database.sqlbase import cursor, sqlvalues
from canonical.launchpad.interfaces import ILaunchpadCelebrities, ITicketSet
from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility
from canonical.launchpad.webapp.interaction import (
    setupInteraction, endInteraction)
from canonical.lp.dbschema import TicketStatus


class TicketJanitor:
    """Object that takes the responsability of expiring tickets
    without activity in a configurable period.
    """

    def __init__(self, days_before_expiration=None, log=None):
        """Create a new TicketJanitor.

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

    def expireTickets(self):
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
            for ticket in self._findExpiredTickets():
                ticket.expireTicket(
                    self.janitor,
                    "This support request was expired because it remained in "
                    "the %s state without activity for the last %d days." % (
                        ticket.status.title, self.days_before_expiration))
                count += 1
            self.log.info('Expired %d tickets.' % count)
        finally:
            self._logout()
        self.log.info('Finished expiration run.')

    def _findExpiredTickets(self):
        """Return an enumerator containg the ticket to expire."""
        cur = cursor()
        cur.execute("""
            SELECT id FROM Ticket
                WHERE status IN (%s, %s)
                    AND (datelastresponse IS NULL
                         OR datelastresponse < (
                            current_timestamp -interval '%s days'))
                    AND
                    datelastquery  < (current_timestamp - interval '%s days')
            """ % sqlvalues(
                TicketStatus.OPEN, TicketStatus.NEEDSINFO,
                self.days_before_expiration, self.days_before_expiration))
        ticket_ids_to_expire = list(cur.fetchall())
        self.log.info(
            'Found %d tickets to expire.' % len(ticket_ids_to_expire))
        ticketset = getUtility(ITicketSet)
        for row in ticket_ids_to_expire:
            ticket_id = row[0]
            yield ticketset.get(ticket_id)

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
