# Copyright 2008, 2009 Canonical Ltd.  All rights reserved.

"""Base class for sending out emails."""

__metaclass__ = type

__all__ = ['BaseMailer']


from canonical.launchpad.helpers import get_email_template
from canonical.launchpad.mail import format_address, MailController
from canonical.launchpad.mailout import text_delta
from lp.services.mail.notificationrecipientset import (
    NotificationRecipientSet)


class BaseMailer:
    """Base class for notification mailers.

    Subclasses must provide getReason (or reimplement _getTemplateParameters
    or generateEmail).

    It is expected that subclasses may override _getHeaders,
    _getTemplateParams, and perhaps _getBody.
    """

    def __init__(self, subject, template_name, recipients, from_address,
                 delta=None, message_id=None):
        """Constructor.

        :param subject: A Python dict-replacement template for the subject
            line of the email.
        :param template: Name of the template to use for the message body.
        :param recipients: A dict of recipient to Subscription.
        :param from_address: The from_address to use on emails.
        :param delta: A Delta object with members "delta_values", "interface"
            and "new_values", such as BranchMergeProposalDelta.
        :param message_id: The Message-Id to use for generated emails.  If
            not supplied, random message-ids will be used.
        """
        self._subject_template = subject
        self._template_name = template_name
        self._recipients = NotificationRecipientSet()
        for recipient, reason in recipients.iteritems():
            self._recipients.add(recipient, reason, reason.mail_header)
        self.from_address = from_address
        self.delta = delta
        self.message_id = message_id

    def generateEmail(self, email, recipient):
        """Generate the email for this recipient.

        :return: (headers, subject, body) of the email.
        """
        to_address = format_address(recipient.displayname, email)
        headers = self._getHeaders(email)
        subject = self._getSubject(email)
        body = self._getBody(email)
        ctrl = MailController(
            self.from_address, to_address, subject, body, headers)
        self._addAttachments(ctrl)
        return ctrl

    def _getSubject(self, email):
        """The subject template expanded with the template params."""
        return self._subject_template % self._getTemplateParams(email)

    def _getReplyToAddress(self):
        """Return the address to use for the reply-to header."""
        return None

    def _getHeaders(self, email):
        """Return the mail headers to use."""
        reason, rationale = self._recipients.getReason(email)
        headers = {'X-Launchpad-Message-Rationale': reason.mail_header}
        reply_to = self._getReplyToAddress()
        if reply_to is not None:
            headers['Reply-To'] = reply_to
        if self.message_id is not None:
            headers['Message-Id'] = self.message_id
        return headers

    def _addAttachments(self, ctrl):
        """Add any appropriate attachments to a MailController.

        Default implementation does nothing.
        """
        pass

    def _getTemplateParams(self, email):
        """Return a dict of values to use in the body and subject."""
        reason, rationale = self._recipients.getReason(email)
        params = {'reason': reason.getReason()}
        if self.delta is not None:
            params['delta'] = self.textDelta()
        return params

    def textDelta(self):
        """Return a textual version of the class delta."""
        return text_delta(self.delta, self.delta.delta_values,
            self.delta.new_values, self.delta.interface)

    def _getBody(self, email):
        """Return the complete body to use for this email."""
        template = get_email_template(self._template_name)
        return template % self._getTemplateParams(email)

    def sendAll(self):
        """Send notifications to all recipients."""
        for email, recipient in self._recipients.getRecipientPersons():
            ctrl = self.generateEmail(email, recipient)
            ctrl.send()
