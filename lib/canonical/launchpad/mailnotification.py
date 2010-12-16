# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# XXX: Gavin Panella 2008-11-21 bug=300725: This module need
# refactoring and/or splitting into a package or packages.

"""Event handlers that send email notifications."""

__metaclass__ = type

from difflib import unified_diff
from email.Header import Header
from email.MIMEMessage import MIMEMessage
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.Utils import (
    formataddr,
    make_msgid,
    )
import re

from zope.component import (
    getAdapter,
    getUtility,
    )

from canonical.config import config
from canonical.database.sqlbase import block_implicit_flushes
from canonical.launchpad.helpers import (
    get_contact_email_addresses,
    get_email_template,
    )
from canonical.launchpad.interfaces.launchpad import ILaunchpadRoot
from canonical.launchpad.interfaces.message import (
    IDirectEmailAuthorization,
    QuotaReachedError,
    )
from canonical.launchpad.mail import (
    format_address,
    sendmail,
    simple_sendmail,
    simple_sendmail_from_person,
    )
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.url import urlappend
from lp.blueprints.interfaces.specification import ISpecification
from lp.bugs.mail.bugnotificationbuilder import get_bugmail_error_address
from lp.registry.interfaces.mailinglist import IHeldMessageDetails
from lp.registry.interfaces.person import (
    IPerson,
    IPersonSet,
    )
from lp.registry.interfaces.teammembership import (
    ITeamMembershipSet,
    TeamMembershipStatus,
    )
from lp.services.mail.mailwrapper import MailWrapper
# XXX 2010-06-16 gmb bug=594985
#     This shouldn't be here, but if we take it out lots of things cry,
#     which is sad.
from lp.services.mail.notificationrecipientset import NotificationRecipientSet

# Silence lint warnings.
NotificationRecipientSet


CC = "CC"


def send_process_error_notification(to_address, subject, error_msg,
                                    original_msg, failing_command=None):
    """Send a mail about an error occurring while using the email interface.

    Tells the user that an error was encountered while processing his
    request and attaches the original email which caused the error to
    happen.

        :to_address: The address to send the notification to.
        :subject: The subject of the notification.
        :error_msg: The error message that explains the error.
        :original_msg: The original message sent by the user.
        :failing_command: The command that caused the error to happen.
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


@block_implicit_flushes
def notify_invitation_to_join_team(event):
    """Notify team admins that the team has been invited to join another team.

    The notification will include a link to a page in which any team admin can
    accept the invitation.

    XXX: Guilherme Salgado 2007-05-08:
    At some point we may want to extend this functionality to allow invites
    to be sent to users as well, but for now we only use it for teams.
    """
    member = event.member
    assert member.isTeam()
    team = event.team
    membership = getUtility(ITeamMembershipSet).getByPersonAndTeam(
        member, team)
    assert membership is not None

    reviewer = membership.proposed_by
    admin_addrs = member.getTeamAdminsEmailAddresses()
    from_addr = format_address(
        team.displayname, config.canonical.noreply_from_address)
    subject = 'Invitation for %s to join' % member.name
    templatename = 'membership-invitation.txt'
    template = get_email_template(templatename)
    replacements = {
        'reviewer': '%s (%s)' % (reviewer.displayname, reviewer.name),
        'member': '%s (%s)' % (member.displayname, member.name),
        'team': '%s (%s)' % (team.displayname, team.name),
        'team_url': canonical_url(team),
        'membership_invitations_url':
            "%s/+invitation/%s" % (canonical_url(member), team.name)}
    for address in admin_addrs:
        recipient = getUtility(IPersonSet).getByEmail(address)
        replacements['recipient_name'] = recipient.displayname
        msg = MailWrapper().format(template % replacements, force_wrap=True)
        simple_sendmail(from_addr, address, subject, msg)


def send_team_email(from_addr, address, subject, template, replacements,
                    rationale, headers=None):
    """Send a team message with a rationale."""
    if headers is None:
        headers = {}
    body = MailWrapper().format(template % replacements, force_wrap=True)
    footer = "-- \n%s" % rationale
    message = '%s\n\n%s' % (body, footer)
    simple_sendmail(from_addr, address, subject, message, headers)


@block_implicit_flushes
def notify_team_join(event):
    """Notify team admins that someone has asked to join the team.

    If the team's policy is Moderated, the email will say that the membership
    is pending approval. Otherwise it'll say that the person has joined the
    team and who added that person to the team.
    """
    person = event.person
    team = event.team
    membership = getUtility(ITeamMembershipSet).getByPersonAndTeam(
        person, team)
    assert membership is not None
    approved, admin, proposed = [
        TeamMembershipStatus.APPROVED, TeamMembershipStatus.ADMIN,
        TeamMembershipStatus.PROPOSED]
    admin_addrs = team.getTeamAdminsEmailAddresses()
    from_addr = format_address(
        team.displayname, config.canonical.noreply_from_address)

    reviewer = membership.proposed_by
    if reviewer != person and membership.status in [approved, admin]:
        reviewer = membership.reviewed_by
        # Somebody added this person as a member, we better send a
        # notification to the person too.
        member_addrs = get_contact_email_addresses(person)

        headers = {}
        if person.isTeam():
            templatename = 'new-member-notification-for-teams.txt'
            subject = '%s joined %s' % (person.name, team.name)
            header_rational = "Indirect member (%s)" % team.name
            footer_rationale = (
                "You received this email because "
                "%s is the new member." % person.name)
        else:
            templatename = 'new-member-notification.txt'
            subject = 'You have been added to %s' % team.name
            header_rational = "Member (%s)" % team.name
            footer_rationale = (
                "You received this email because you are the new member.")

        if team.mailing_list is not None:
            template = get_email_template(
                'team-list-subscribe-block.txt')
            editemails_url = urlappend(
                canonical_url(getUtility(ILaunchpadRoot)),
                'people/+me/+editemails')
            list_instructions = template % dict(editemails_url=editemails_url)
        else:
            list_instructions = ''

        template = get_email_template(templatename)
        replacements = {
            'reviewer': '%s (%s)' % (reviewer.displayname, reviewer.name),
            'team_url': canonical_url(team),
            'member': '%s (%s)' % (person.displayname, person.name),
            'team': '%s (%s)' % (team.displayname, team.name),
            'list_instructions': list_instructions,
            }
        headers = {'X-Launchpad-Message-Rationale': header_rational}
        for address in member_addrs:
            recipient = getUtility(IPersonSet).getByEmail(address)
            replacements['recipient_name'] = recipient.displayname
            send_team_email(
                from_addr, address, subject, template, replacements,
                footer_rationale, headers)

        # The member's email address may be in admin_addrs too; let's remove
        # it so the member don't get two notifications.
        admin_addrs = set(admin_addrs).difference(set(member_addrs))

    # Yes, we can have teams with no members; not even admins.
    if not admin_addrs:
        return

    replacements = {
        'person_name': "%s (%s)" % (person.displayname, person.name),
        'team_name': "%s (%s)" % (team.displayname, team.name),
        'reviewer_name': "%s (%s)" % (reviewer.displayname, reviewer.name),
        'url': canonical_url(membership)}

    headers = {}
    if membership.status in [approved, admin]:
        template = get_email_template(
            'new-member-notification-for-admins.txt')
        subject = '%s joined %s' % (person.name, team.name)
    elif membership.status == proposed:
        # In the UI, a user can only propose himself or a team he
        # admins. Some users of the REST API have a workflow, where
        # they propose users that are designated as mentees (Bug 498181).
        if reviewer != person:
            headers = {"Reply-To": reviewer.preferredemail.email}
            template = get_email_template(
                'pending-membership-approval-for-third-party.txt')
        else:
            headers = {"Reply-To": person.preferredemail.email}
            template = get_email_template('pending-membership-approval.txt')
        subject = "%s wants to join" % person.name
    else:
        raise AssertionError(
            "Unexpected membership status: %s" % membership.status)

    for address in admin_addrs:
        recipient = getUtility(IPersonSet).getByEmail(address)
        replacements['recipient_name'] = recipient.displayname
        if recipient.isTeam():
            header_rationale = 'Admin (%s via %s)' % (
                team.name, recipient.name)
            footer_rationale = (
                "you are an admin of the %s team\n"
                "via the %s team." % (
                team.displayname, recipient.displayname))
        elif recipient == team.teamowner:
            header_rationale = 'Owner (%s)' % team.name
            footer_rationale = (
                "you are the owner of the %s team." % team.displayname)
        else:
            header_rationale = 'Admin (%s)' % team.name
            footer_rationale = (
                "you are an admin of the %s team." % team.displayname)
        footer = 'You received this email because %s' % footer_rationale
        headers['X-Launchpad-Message-Rationale'] = header_rationale
        send_team_email(
            from_addr, address, subject, template, replacements,
            footer, headers)


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
    indent = ' '*4
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
    template = get_email_template('new-mailing-list.txt')
    editemails_url = '%s/+editemails'

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
    template = get_email_template('new-held-message.txt')

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

    for person in non_active_subscribers:

        if person.preferredemail is None:
            # Don't send to people without a preferred email.
            continue

        to_address = [person.preferredemail.email]
        recipient_subscriptions_url = "%s/+archivesubscriptions" % (
            canonical_url(person))
        description_blurb = '.'
        if ppa_description is not None and ppa_description != '':
            description_blurb = ' and has the following description:\n%s' % (
                ppa_description)
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


def encode(value):
    """Encode string for transport in a mail header.

    :param value: The raw email header value.
    :type value: unicode
    :return: The encoded header.
    :rtype: `email.Header.Header`
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
    :rtype: `email.Message.Message`
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
    # BarryWarsaw 19-Nov-2008: If any messages were sent, record the fact that
    # the sender contacted the team.  This is not perfect though because we're
    # really recording the fact that the person contacted the last member of
    # the team.  There's little we can do better though because the team has
    # no contact address, and so there isn't actually an address to record as
    # the team's recipient.  It currently doesn't matter though because we
    # don't actually do anything with the recipient information yet.  All we
    # care about is the sender, for quota purposes.  We definitely want to
    # record the contact outside the above loop though, because if there are
    # 10 members of the team with no contact address, one message should not
    # consume the sender's entire quota.
    authorization.record(message)
