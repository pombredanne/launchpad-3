# Copyright 2008 Canonical Ltd.  All rights reserved.


"""Base class for sending out emails."""


__metaclass__ = type



__all__ = ['BaseMailer']


from zope.security.proxy import removeSecurityProxy

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
        :param recipients: A dict of recipient to NotificationReason.
        :param from_address: The from_addres to use on emails.
        :param delta: A Delta object with members "delta_values", "interface"
            and "new_values", such as BranchMergeProposalDelta.
        """
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

    def getReason(self, recipient):
        """Return a string explaining why the message is being sent.

        This string should be user-oriented, human-readable string.  It should
        ususally vary by recipient.  Typically appears in the message footer.
        """
        raise NotImplementedError(BaseMailer.getReason)

    def textDelta(self):
        """Return a textual version of the class delta."""
        return text_delta(self.delta, self.delta.delta_values,
            self.delta.new_values, self.delta.interface)

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
