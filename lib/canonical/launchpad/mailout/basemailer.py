# Copyright 2008 Canonical Ltd.  All rights reserved.


"""Base class for sending out emails."""


__metaclass__ = type



__all__ = ['BaseMailer']


from canonical.launchpad.helpers import get_email_template
from canonical.launchpad.mail import simple_sendmail, format_address
from canonical.launchpad.mailout import text_delta
from canonical.launchpad.mailout.notificationrecipientset import (
    NotificationRecipientSet)


class BaseMailer:
    """Base class for notification mailers.

    Subclasses must provide getReason (or reimplement _getTemplateParameters
    or generateEmail).

    It is expected that subclasses may override _getHeaders,
    _getTemplateParams, and perhaps _getBody.
    """

    def __init__(self, subject, template_name, recipients, from_address,
                 delta=None):
        """Constructor.

        :param subject: A Python dict-replacement template for the subject
            line of the email.
        :param template: Name of the template to use for the message body.
        :param recipients: A dict of recipient to Subscription.
        :param from_address: The from_address to use on emails.
        :param delta: A Delta object with members "delta_values", "interface"
            and "new_values", such as BranchMergeProposalDelta.
        """
        self._subject_template = subject
        self._template_name = template_name
        self._recipients = NotificationRecipientSet()
        for recipient, reason in recipients.iteritems():
            self._recipients.add(recipient, reason, reason.mail_header)
        self.from_address = from_address
        self.delta = delta

    def generateEmail(self, recipient, email=None):
        """Generate the email for this recipient.

        :return: (headers, subject, body) of the email.
        """
        headers = self._getHeaders(recipient, email=email)
        subject = self._getSubject(recipient, email=email)
        return (headers, subject, self._getBody(recipient, email=email))

    def _getSubject(self, recipient, email=None):
        """The subject template expanded with the template params."""
        return (
            self._subject_template
            % self._getTemplateParams(recipient, email))

    def _getReplyToAddress(self):
        """Return the address to use for the reply-to header."""
        return None

    def _getHeaders(self, recipient, email=None):
        """Return the mail headers to use."""
        if email is None:
            email = recipient.preferredemail.email
        reason, rationale = self._recipients.getReason(email)
        headers = {'X-Launchpad-Message-Rationale': reason.mail_header}
        reply_to = self._getReplyToAddress()
        if reply_to is not None:
            headers['Reply-To'] = reply_to
        return headers

    def _getTemplateParams(self, recipient, email=None):
        """Return a dict of values to use in the body and subject."""
        if email is None:
            email = recipient.preferredemail.email
        reason, rationale = self._recipients.getReason(email)
        params = {'reason': reason.getReason()}
        if self.delta is not None:
            params['delta'] = self.textDelta()
        return params

    def textDelta(self):
        """Return a textual version of the class delta."""
        return text_delta(self.delta, self.delta.delta_values,
            self.delta.new_values, self.delta.interface)

    def _getBody(self, recipient, email=None):
        """Return the complete body to use for this email."""
        template = get_email_template(self._template_name)
        return template % self._getTemplateParams(recipient, email)

    def sendAll(self):
        """Send notifications to all recipients."""
        for email, recipient in self._recipients.getRecipientPersons():
            to_address = format_address(recipient.displayname, email)
            headers, subject, body = self.generateEmail(recipient, email)
            simple_sendmail(
                self.from_address, to_address, subject, body, headers)
