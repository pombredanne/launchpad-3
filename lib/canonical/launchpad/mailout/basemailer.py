# Copyright 2008 Canonical Ltd.  All rights reserved.


"""Base class for sending out emails."""


__metaclass__ = type


from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.mailout import text_delta
from canonical.launchpad.mail import simple_sendmail, format_address
from canonical.launchpad.helpers import get_email_template
from canonical.launchpad.mailout.notificationrecipientset import (
    NotificationRecipientSet)


class BaseMailer:

    def __init__(self, subject, template_name, recipients, from_address,
                 delta=None):
        self._subject_template = subject
        self._template_name = template_name
        self._recipients = NotificationRecipientSet()
        naked_recipients = removeSecurityProxy(recipients)
        for recipient, reason in naked_recipients.iteritems():
            self._recipients.add(recipient, reason, reason.rationale)
        self.from_address = from_address
        self.delta = delta

    def generateEmail(self, recipient):
        """Generate the email for this recipient.

        :return: (headers, subject, body) of the email.
        """
        headers = self._getHeaders(recipient)
        subject = self._subject_template % self._getTemplateParams(recipient)
        return (headers, subject, self._getBody(recipient))

    def _getReplyToAddress(self):
        """Return the address to use for the reply-to header."""
        return None

    def _getHeaders(self, recipient):
        """Return the mail headers to use."""
        notification_reason, rationale = self._recipients.getReason(
            recipient.preferredemail.email)
        headers = {'X-Launchpad-Message-Rationale': rationale}
        reply_to = self._getReplyToAddress()
        if reply_to is not None:
            headers['Reply-To'] = reply_to
        return headers

    def _getTemplateParams(self, recipient):
        """Return a dict of values to use in the body and subject."""
        params = {'reason': self.getReason(recipient)}
        if self.delta is not None:
            params['delta'] = self.textDelta()
        return params

    def textDelta(self):
        """Return a textual version of the class delta."""
        return text_delta(self.delta, self.delta.delta_values,
            self.delta.new_values, self.diff_interface)

    def _getBody(self, recipient):
        """Return the complete body to use for this email."""
        template = get_email_template(self._template_name)
        return template % self._getTemplateParams(recipient)

    def sendAll(self):
        """Send notifications to all recipients."""
        for recipient in self._recipients.getRecipientPersons():
            to_address = format_address(
                recipient.displayname, recipient.preferredemail.email)
            headers, subject, body = self.generateEmail(recipient)
            simple_sendmail(
                self.from_address, to_address, subject, body, headers)
