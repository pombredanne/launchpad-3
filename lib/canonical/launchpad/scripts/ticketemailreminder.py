# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Functions for sending out answered ticket email reminders."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.interfaces import ITicketSet
from canonical.launchpad.mail import simple_sendmail
from canonical.launchpad.mailnotification import (
    get_email_template, MailWrapper)
from canonical.launchpad.scripts import log
from canonical.launchpad.webapp import canonical_url

def send_ticket_email_reminders():
    """Sends reminders regarding answered support tickets.

    It gets all the tickets that are in an Answered state, and sends a
    reminder to the submitter of the ticket, that he should either
    close or re-open the ticket.
    """
    ticketset = getUtility(ITicketSet)
    reminder_email = get_email_template('answered-ticket-reminder.txt')
    mailwrapper = MailWrapper()

    answered_tickets = ticketset.getAnsweredTickets()
    nr_of_tickets = len(answered_tickets)
    if nr_of_tickets > 0:
        log.info("Found %i answered tickets in the database." % len(
            answered_tickets))
    else:
        log.info("There are no answered tickets in the database")

    for ticket in ticketset.getAnsweredTickets():
        submitter = ticket.owner
        if submitter.givenname:
            given_or_display_name = submitter.givenname
        else:
            given_or_display_name = submitter.displayname
        body = reminder_email % {
            'given_or_display_name': given_or_display_name,
            'ticket_title': ticket.title,
            'answerer': ticket.answerer.displayname,
            'ticket_url': canonical_url(ticket)}
        submitter_email = submitter.preferredemail.email
        simple_sendmail(
            "Launchpad Support System <noreply@launchpad.net>",
            submitter_email,
            "Your Launchpad support request #%s on %s has been answered" % (
                ticket.id, ticket.target.displayname),
            mailwrapper.format(body))
        log.info("Sent reminder to %s regarding ticket #%s" % (
            submitter_email, ticket.id))

