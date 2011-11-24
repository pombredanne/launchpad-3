# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# XXX: Gavin Panella 2008-11-21 bug=300725: This module need
# refactoring and/or splitting into a package or packages.

"""Event handlers that send email notifications."""

__metaclass__ = type

from difflib import unified_diff
from email import message_from_string
from email.MIMEMessage import MIMEMessage
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
import re

from zope.component import getUtility

from canonical.config import config
from canonical.database.sqlbase import block_implicit_flushes
from canonical.launchpad.helpers import (
    get_contact_email_addresses,
    get_email_template,
    )
from canonical.launchpad.webapp.interfaces import ILaunchpadRoot
from canonical.launchpad.webapp.publisher import canonical_url
from lp.blueprints.interfaces.specification import ISpecification
from lp.bugs.mail.bugnotificationbuilder import get_bugmail_error_address
from lp.registry.interfaces.person import IPerson
from lp.services.mail.mailwrapper import MailWrapper
# XXX 2010-06-16 gmb bug=594985
#     This shouldn't be here, but if we take it out lots of things cry,
#     which is sad.
from lp.services.mail.notificationrecipientset import NotificationRecipientSet
from lp.services.mail.sendmail import (
    format_address,
    sendmail,
    simple_sendmail,
    simple_sendmail_from_person,
    )

# Silence lint warnings.
NotificationRecipientSet


CC = "CC"
MAX_RETURN_MESSAGE_SIZE = config.processmail.max_error_message_return_size


def send_process_error_notification(to_address, subject, error_msg,
                                    original_msg, failing_command=None,
                                    max_return_size=MAX_RETURN_MESSAGE_SIZE):
    """Send a mail about an error occurring while using the email interface.

    Tells the user that an error was encountered while processing his
    request and attaches the original email which caused the error to
    happen.  The original message will be truncated to
    max_return_size bytes.

        :to_address: The address to send the notification to.
        :subject: The subject of the notification.
        :error_msg: The error message that explains the error.
        :original_msg: The original message sent by the user.
        :failing_command: The command that caused the error to happen.
        :max_return_size: The maximum size returned for the original message.
    """
    if isinstance(failing_command, list):
        failing_commands = failing_command
    elif failing_command is None:
        failing_commands = []
    else:
        failing_commands = [failing_command]
    failed_commands_information = ''
    if len(failing_commands) > 0:
        failed_commands_information = 'Failing command:'
        for failing_command in failing_commands:
            failed_commands_information += '\n    %s' % str(failing_command)

    body = get_email_template('email-processing-error.txt') % {
            'failed_command_information': failed_commands_information,
            'error_msg': error_msg}
    mailwrapper = MailWrapper(width=72)
    body = mailwrapper.format(body)
    error_part = MIMEText(body.encode('utf-8'), 'plain', 'utf-8')

    msg = MIMEMultipart()
    msg['To'] = to_address
    msg['From'] = get_bugmail_error_address()
    msg['Subject'] = subject
    msg.attach(error_part)
    original_msg_str = str(original_msg)
    if len(original_msg_str) > max_return_size:
        truncated_msg_str = original_msg_str[:max_return_size]
        original_msg = message_from_string(truncated_msg_str)
    msg.attach(MIMEMessage(original_msg))
    sendmail(msg)


def get_unified_diff(old_text, new_text, text_width):
    r"""Return a unified diff of the two texts.

    Before the diff is produced, the texts are wrapped to the given text
    width.

        >>> print get_unified_diff(
        ...     'Some text\nAnother line\n',
        ...     'Some more text\nAnother line\n',
        ...     text_width=72)
        - Some text
        + Some more text
          Another line

    """
    mailwrapper = MailWrapper(width=72)
    old_text_wrapped = mailwrapper.format(old_text or '')
    new_text_wrapped = mailwrapper.format(new_text or '')

    lines_of_context = len(old_text_wrapped.splitlines())
    text_diff = unified_diff(
        old_text_wrapped.splitlines(),
        new_text_wrapped.splitlines(),
        n=lines_of_context)
    # Remove the diff header, which consists of the first three
    # lines.
    text_diff = list(text_diff)[3:]
    # Let's simplify the diff output by removing the helper lines,
    # which begin with '?'.
    text_diff = [
        diff_line for diff_line in text_diff
        if not diff_line.startswith('?')]
    # Add a whitespace between the +/- and the text line.
    text_diff = [
        re.sub('^([\+\- ])(.*)', r'\1 \2', line)
        for line in text_diff]
    text_diff = '\n'.join(text_diff)
    return text_diff


def specification_notification_subject(spec):
    """Format the email subject line for a specification."""
    return '[Blueprint %s] %s' % (spec.name, spec.title)


@block_implicit_flushes
def notify_specification_modified(spec, event):
    """Notify the related people that a specification has been modifed."""
    user = IPerson(event.user)
    spec_delta = spec.getDelta(event.object_before_modification, user)
    if spec_delta is None:
        # XXX: Bjorn Tillenius 2006-03-08:
        #      Ideally, if an IObjectModifiedEvent event is generated,
        #      spec_delta shouldn't be None. I'm not confident that we
        #      have enough test yet to assert this, though.
        return

    subject = specification_notification_subject(spec)
    indent = ' ' * 4
    info_lines = []
    for dbitem_name in ('definition_status', 'priority'):
        title = ISpecification[dbitem_name].title
        assert ISpecification[dbitem_name].required, (
            "The mail notification assumes %s can't be None" % dbitem_name)
        dbitem_delta = getattr(spec_delta, dbitem_name)
        if dbitem_delta is not None:
            old_item = dbitem_delta['old']
            new_item = dbitem_delta['new']
            info_lines.append("%s%s: %s => %s" % (
                indent, title, old_item.title, new_item.title))

    for person_attrname in ('approver', 'assignee', 'drafter'):
        title = ISpecification[person_attrname].title
        person_delta = getattr(spec_delta, person_attrname)
        if person_delta is not None:
            old_person = person_delta['old']
            if old_person is None:
                old_value = "(none)"
            else:
                old_value = old_person.displayname
            new_person = person_delta['new']
            if new_person is None:
                new_value = "(none)"
            else:
                new_value = new_person.displayname
            info_lines.append(
                "%s%s: %s => %s" % (indent, title, old_value, new_value))

    mail_wrapper = MailWrapper(width=72)
    if spec_delta.whiteboard is not None:
        if info_lines:
            info_lines.append('')
        whiteboard_delta = spec_delta.whiteboard
        if whiteboard_delta['old'] is None:
            info_lines.append('Whiteboard set to:')
            info_lines.append(mail_wrapper.format(whiteboard_delta['new']))
        else:
            whiteboard_diff = get_unified_diff(
                whiteboard_delta['old'], whiteboard_delta['new'], 72)
            info_lines.append('Whiteboard changed:')
            info_lines.append(whiteboard_diff)

    if not info_lines:
        # The specification was modified, but we don't yet support
        # sending notification for the change.
        return
    body = get_email_template('specification-modified.txt') % {
        'editor': user.displayname,
        'info_fields': '\n'.join(info_lines),
        'spec_title': spec.title,
        'spec_url': canonical_url(spec)}

    for address in spec.notificationRecipientAddresses():
        simple_sendmail_from_person(user, address, subject, body)


@block_implicit_flushes
def notify_specification_subscription_created(specsub, event):
    """Notify a user that they have been subscribed to a blueprint."""
    user = IPerson(event.user)
    spec = specsub.specification
    person = specsub.person
    subject = specification_notification_subject(spec)
    mailwrapper = MailWrapper(width=72)
    body = mailwrapper.format(
        'You are now subscribed to the blueprint '
        '%(blueprint_name)s - %(blueprint_title)s.\n\n'
        '-- \n%(blueprint_url)s' %
        {'blueprint_name': spec.name,
         'blueprint_title': spec.title,
         'blueprint_url': canonical_url(spec)})
    for address in get_contact_email_addresses(person):
        simple_sendmail_from_person(user, address, subject, body)


@block_implicit_flushes
def notify_specification_subscription_modified(specsub, event):
    """Notify a subscriber to a blueprint that their
    subscription has changed.
    """
    user = IPerson(event.user)
    spec = specsub.specification
    person = specsub.person
    # Only send a notification if the
    # subscription changed by someone else.
    if person == user:
        return
    subject = specification_notification_subject(spec)
    if specsub.essential:
        specsub_type = 'Participation essential'
    else:
        specsub_type = 'Participation non-essential'
    mailwrapper = MailWrapper(width=72)
    body = mailwrapper.format(
        'Your subscription to the blueprint '
        '%(blueprint_name)s - %(blueprint_title)s '
        'has changed to [%(specsub_type)s].\n\n'
        '--\n  %(blueprint_url)s' %
        {'blueprint_name': spec.name,
         'blueprint_title': spec.title,
         'specsub_type': specsub_type,
         'blueprint_url': canonical_url(spec)})
    for address in get_contact_email_addresses(person):
        simple_sendmail_from_person(user, address, subject, body)


@block_implicit_flushes
def notify_new_ppa_subscription(subscription, event):
    """Notification that a new PPA subscription can be activated."""
    non_active_subscribers = subscription.getNonActiveSubscribers()

    archive = subscription.archive

    # We don't send notification emails for commercial PPAs as these
    # are purchased via software center (and do not mention Launchpad).
    if archive.commercial:
        return

    registrant_name = subscription.registrant.displayname
    ppa_displayname = archive.displayname
    ppa_reference = "ppa:%s/%s" % (
        archive.owner.name, archive.name)
    ppa_description = archive.description
    subject = 'PPA access granted for ' + ppa_displayname

    template = get_email_template('ppa-subscription-new.txt')

    for person, preferred_email in non_active_subscribers:
        to_address = [preferred_email.email]
        root = getUtility(ILaunchpadRoot)
        recipient_subscriptions_url = "%s~/+archivesubscriptions" % (
            canonical_url(root))
        description_blurb = '.'
        if ppa_description is not None and ppa_description != '':
            description_blurb = (
                ' and has the following description:\n\n%s' % ppa_description)
        replacements = {
            'recipient_name': person.displayname,
            'registrant_name': registrant_name,
            'registrant_profile_url': canonical_url(subscription.registrant),
            'ppa_displayname': ppa_displayname,
            'ppa_reference': ppa_reference,
            'ppa_description_blurb': description_blurb,
            'recipient_subscriptions_url': recipient_subscriptions_url,
            }
        body = MailWrapper(72).format(template % replacements,
                                      force_wrap=True)

        from_address = format_address(
            registrant_name, config.canonical.noreply_from_address)

        headers = {
            'Sender': config.canonical.bounce_address,
            }

        # If the registrant has a preferred email, then use it for the
        # Reply-To.
        if subscription.registrant.preferredemail:
            headers['Reply-To'] = format_address(
                registrant_name,
                subscription.registrant.preferredemail.email)

        simple_sendmail(from_address, to_address, subject, body, headers)
