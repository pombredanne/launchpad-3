# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Event handlers that send email notifications."""

__metaclass__ = type

from email.header import Header
from email.mime.text import MIMEText
from email.utils import (
    formataddr,
    make_msgid,
    )

from zope.component import (
    getAdapter,
    getUtility,
    )

from lp.registry.interfaces.mailinglist import IHeldMessageDetails
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.persontransferjob import (
    ITeamInvitationNotificationJobSource,
    ITeamJoinNotificationJobSource,
    )
from lp.services.config import config
from lp.services.database.sqlbase import block_implicit_flushes
from lp.services.mail.helpers import get_email_template
from lp.services.mail.mailwrapper import MailWrapper
from lp.services.mail.sendmail import (
    format_address,
    sendmail,
    simple_sendmail,
    )
from lp.services.messages.interfaces.message import (
    IDirectEmailAuthorization,
    QuotaReachedError,
    )
from lp.services.webapp.publisher import canonical_url


@block_implicit_flushes
def notify_invitation_to_join_team(event):
    """Notify team admins that the team has been invited to join another team.

    The notification will include a link to a page in which any team admin can
    accept the invitation.
    """
    getUtility(ITeamInvitationNotificationJobSource).create(
        event.member, event.team)


@block_implicit_flushes
def notify_team_join(event):
    """Notify team admins that someone has asked to join the team.

    If the team's policy is Moderated, the email will say that the membership
    is pending approval. Otherwise it'll say that the person has joined the
    team and who added that person to the team.
    """
    getUtility(ITeamJoinNotificationJobSource).create(event.person, event.team)


def notify_mailinglist_activated(mailinglist, event):
    """Notification that a mailing list is available.

    All active members of a team and its subteams receive notification when
    the team's mailing list is available.
    """
    # We will use the setting of the date_activated field as a hint
    # that this list is new, and that noboby has subscribed yet.  See
    # `MailingList.transitionToStatus()` for the details.
    old_date = event.object_before_modification.date_activated
    new_date = event.object.date_activated
    list_looks_new = old_date is None and new_date is not None

    if not (list_looks_new and mailinglist.is_usable):
        return

    team = mailinglist.team
    from_address = format_address(
        team.displayname, config.canonical.noreply_from_address)
    headers = {}
    subject = "New Mailing List for %s" % team.displayname
    template = get_email_template('new-mailing-list.txt', app='registry')
    editemails_url = '%s/+editmailinglists'

    for person in team.allmembers:
        if person.is_team or person.preferredemail is None:
            # This is either a team or a person without a preferred email, so
            # don't send a notification.
            continue
        to_address = [str(person.preferredemail.email)]
        replacements = {
            'user': person.displayname,
            'team_displayname': team.displayname,
            'team_name': team.name,
            'team_url': canonical_url(team),
            'subscribe_url': editemails_url % canonical_url(person),
            }
        body = MailWrapper(72).format(template % replacements,
                                      force_wrap=True)
        simple_sendmail(from_address, to_address, subject, body, headers)


def notify_message_held(message_approval, event):
    """Send a notification of a message hold to all team administrators."""
    message_details = getAdapter(message_approval, IHeldMessageDetails)
    team = message_approval.mailing_list.team
    from_address = format_address(
        team.displayname, config.canonical.noreply_from_address)
    subject = (
        'New mailing list message requiring approval for %s'
        % team.displayname)
    template = get_email_template('new-held-message.txt', app='registry')

    # Most of the replacements are the same for everyone.
    replacements = {
        'subject': message_details.subject,
        'author_name': message_details.author.displayname,
        'author_url': canonical_url(message_details.author),
        'date': message_details.date,
        'message_id': message_details.message_id,
        'review_url': '%s/+mailinglist-moderate' % canonical_url(team),
        'team': team.displayname,
        }

    # Don't wrap the paragraph with the url.
    def wrap_function(paragraph):
        return (paragraph.startswith('http:') or
                paragraph.startswith('https:'))

    # Send one message to every team administrator.
    person_set = getUtility(IPersonSet)
    for address in team.getTeamAdminsEmailAddresses():
        user = person_set.getByEmail(address)
        replacements['user'] = user.displayname
        body = MailWrapper(72).format(
            template % replacements, force_wrap=True, wrap_func=wrap_function)
        simple_sendmail(from_address, address, subject, body)


def encode(value):
    """Encode string for transport in a mail header.

    :param value: The raw email header value.
    :type value: unicode
    :return: The encoded header.
    :rtype: `email.header.Header`
    """
    try:
        value.encode('us-ascii')
        charset = 'us-ascii'
    except UnicodeEncodeError:
        charset = 'utf-8'
    return Header(value.encode(charset), charset)


def send_direct_contact_email(
    sender_email, recipients_set, subject, body):
    """Send a direct user-to-user email.

    :param sender_email: The email address of the sender.
    :type sender_email: string
    :param recipients_set: The recipients.
    :type recipients_set:' A ContactViaWebNotificationSet
    :param subject: The Subject header.
    :type subject: unicode
    :param body: The message body.
    :type body: unicode
    :return: The sent message.
    :rtype: `email.message.Message`
    """
    # Craft the email message.  Start by checking whether the subject and
    # message bodies are ASCII or not.
    subject_header = encode(subject)
    try:
        body.encode('us-ascii')
        charset = 'us-ascii'
    except UnicodeEncodeError:
        charset = 'utf-8'
    # Get the sender's real name, encoded as per RFC 2047.
    person_set = getUtility(IPersonSet)
    sender = person_set.getByEmail(sender_email)
    assert sender is not None, 'No person for sender %s' % sender_email
    sender_name = str(encode(sender.displayname))
    # Do a single authorization/quota check for the sender.  We consume one
    # quota credit per contact, not per recipient.
    authorization = IDirectEmailAuthorization(sender)
    if not authorization.is_allowed:
        raise QuotaReachedError(sender.displayname, authorization)
    # Add the footer as a unicode string, then encode the body if necessary.
    # This is not entirely optimal if the body has non-ascii characters in it,
    # since the footer may get garbled in a non-MIME aware mail reader.  Who
    # uses those anyway!?  The only alternative is to attach the footer as a
    # MIME attachment with a us-ascii charset, but that has it's own set of
    # problems (and user complaints).  Email sucks.
    additions = u'\n'.join([
        u'',
        u'-- ',
        u'This message was sent from Launchpad by',
        u'%s (%s)' % (sender_name, canonical_url(sender)),
        u'%s.',
        u'For more information see',
        u'https://help.launchpad.net/YourAccount/ContactingPeople',
        ])
    # Craft and send one message per recipient.
    mailwrapper = MailWrapper(width=72)
    message = None
    for recipient_email, recipient in recipients_set.getRecipientPersons():
        recipient_name = str(encode(recipient.displayname))
        reason, rational_header = recipients_set.getReason(recipient_email)
        reason = str(encode(reason)).replace('\n ', '\n')
        formatted_body = mailwrapper.format(body, force_wrap=True)
        formatted_body += additions % reason
        formatted_body = formatted_body.encode(charset)
        message = MIMEText(formatted_body, _charset=charset)
        message['From'] = formataddr((sender_name, sender_email))
        message['To'] = formataddr((recipient_name, recipient_email))
        message['Subject'] = subject_header
        message['Message-ID'] = make_msgid('launchpad')
        message['X-Launchpad-Message-Rationale'] = rational_header
        # Send the message.
        sendmail(message, bulk=False)
    # Use the information from the last message sent to record the action
    # taken. The record will be used to throttle user-to-user emails.
    if message is not None:
        authorization.record(message)
