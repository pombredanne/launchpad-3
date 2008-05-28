# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import re
from urlparse import urlunparse

from zope.component import getUtility
from zope.interface import implements
from zope.event import notify
from canonical.config import config
from canonical.database.sqlbase import rollback

from canonical.launchpad.helpers import get_email_template
from canonical.launchpad.interfaces import (
    BugAttachmentType, BugNotificationLevel, CreatedBugWithNoBugTasksError,
    EmailProcessingError, IBranchMergeProposalGetter, IBugAttachmentSet,
    IBugEditEmailCommand, IBugEmailCommand, IBugMessageSet,
    IBugTaskEditEmailCommand, IBugTaskEmailCommand, CodeReviewVote,
    IDistroBugTask, IDistroSeriesBugTask, ILaunchBag, IMailHandler,
    IMessageSet, IQuestionSet, ISpecificationSet, IUpstreamBugTask,
    IWeaklyAuthenticatedPrincipal, QuestionStatus)
from canonical.launchpad.mail.commands import emailcommands, get_error_message
from canonical.launchpad.mail.sendmail import sendmail, simple_sendmail
from canonical.launchpad.mail.specexploder import get_spec_url_from_moin_mail
from canonical.launchpad.mailnotification import (
    MailWrapper, send_process_error_notification)
from canonical.launchpad.webapp import canonical_url, urlparse
from canonical.launchpad.webapp.interaction import get_current_principal

from canonical.launchpad.event import (
    SQLObjectCreatedEvent)
from canonical.launchpad.event.interfaces import (
    ISQLObjectCreatedEvent)


def get_main_body(signed_msg):
    """Returns the first text part of the email."""
    msg = signed_msg.signedMessage
    if msg is None:
        # The email wasn't signed.
        msg = signed_msg
    if msg.is_multipart():
        for part in msg.get_payload():
            if part.get_content_type() == 'text/plain':
                return part.get_payload(decode=True)
    else:
        return msg.get_payload(decode=True)


def get_bugtask_type(bugtask):
    """Returns the specific IBugTask interface the the bugtask provides.

        >>> from canonical.launchpad.interfaces import (
        ...     IUpstreamBugTask, IDistroBugTask, IDistroSeriesBugTask)
        >>> from zope.interface import classImplementsOnly
        >>> class BugTask:
        ...     pass

    :bugtask: has to provide a specific bugtask interface:

        >>> get_bugtask_type(BugTask()) #doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        AssertionError...

    When it does, the specific interface is returned:

        >>> classImplementsOnly(BugTask, IUpstreamBugTask)
        >>> get_bugtask_type(BugTask()) #doctest: +ELLIPSIS
        <...IUpstreamBugTask>

        >>> classImplementsOnly(BugTask, IDistroBugTask)
        >>> get_bugtask_type(BugTask()) #doctest: +ELLIPSIS
        <...IDistroBugTask>

        >>> classImplementsOnly(BugTask, IDistroSeriesBugTask)
        >>> get_bugtask_type(BugTask()) #doctest: +ELLIPSIS
        <...IDistroSeriesBugTask>
    """
    bugtask_interfaces = [
        IUpstreamBugTask, IDistroBugTask, IDistroSeriesBugTask
        ]
    for interface in bugtask_interfaces:
        if interface.providedBy(bugtask):
            return interface
    # The bugtask didn't provide any specific interface.
    raise AssertionError(
        'No specific bugtask interface was provided by %r' % bugtask)


def guess_bugtask(bug, person):
    """Guess which bug task the person intended to edit.

    Return None if no bug task could be guessed.
    """
    if len(bug.bugtasks) == 1:
        return bug.bugtasks[0]
    else:
        for bugtask in bug.bugtasks:
            if IUpstreamBugTask.providedBy(bugtask):
                # Is the person an upstream maintainer?
                if person.inTeam(bugtask.product.owner):
                    return bugtask
            elif IDistroBugTask.providedBy(bugtask):
                # Is the person a member of the distribution?
                if person.inTeam(bugtask.distribution.members):
                    return bugtask
                else:
                    # Is the person one of the package subscribers?
                    bug_sub = bugtask.target.getSubscription(person)
                    if bug_sub is not None:
                        if (bug_sub.bug_notification_level >
                            BugNotificationLevel.NOTHING):
                            # The user is subscribed to bug notifications
                            # for this package
                            return bugtask
    return None


class IncomingEmailError(Exception):
    """Indicates that something went wrong processing the mail."""

    def __init__(self, message, failing_command=None):
        Exception.__init__(self, message)
        self.message = message
        self.failing_command = failing_command


def reformat_wiki_text(text):
    """Transform moin formatted raw text to readable text."""

    # XXX Tom Berger 2008-02-20:
    # This implementation is neither correct nor complete.
    # See https://bugs.launchpad.net/launchpad/+bug/193646

    # Strip macros (anchors, TOC, etc'...)
    re_macro = re.compile('\[\[.*?\]\]')
    text = re_macro.sub('', text)

    # sterilize links
    re_link = re.compile('\[(.*?)\]')
    text = re_link.sub(
        lambda match: ' '.join(match.group(1).split(' ')[1:]), text)

    # Strip comments
    re_comment = re.compile('^#.*?$', re.MULTILINE)
    text = re_comment.sub('', text)

    return text

def parse_commands(content, command_names):
    """Extract commands from a bug-style string.

    All commands must be indented using either spaces or tabs.  They must be
    listed in command_names-- if not, they are silently ignored.

    The special command 'done' terminates processing.  It takes no arguments.
    Any commands that follow it will be ignored.  'done' should not be listed
    in command_names.

    While this syntax is the Launchpad standard, bug #29572 says it should be
    changed to only accept commands at the beginning and to not require
    indentation.

    A list of (command, args) tuples is returned.
    """
    commands = []
    for line in content.splitlines():
        # All commands have to be indented.
        if line.startswith(' ') or line.startswith('\t'):
            command_string = line.strip()
            if command_string == 'done':
                # If the 'done' statement is encountered,
                # stop reading any more commands.
                break
            words = command_string.split(' ')
            if len(words) > 0 and words[0] in command_names:
                commands.append((words[0], words[1:]))
    return commands


class MaloneHandler:
    """Handles emails sent to Malone.

    It only handles mail sent to new@... and $bugid@..., where $bugid is a
    positive integer.
    """
    implements(IMailHandler)

    allow_unknown_users = False

    def getCommands(self, signed_msg):
        """Returns a list of all the commands found in the email."""
        content = get_main_body(signed_msg)
        if content is None:
            return []
        return [emailcommands.get(name=name, string_args=args) for
                name, args in parse_commands(content, emailcommands.names())]

    def process(self, signed_msg, to_addr, filealias=None, log=None):
        """See IMailHandler."""
        commands = self.getCommands(signed_msg)
        user, host = to_addr.split('@')
        add_comment_to_bug = False

        try:
            if len(commands) > 0:
                cur_principal = get_current_principal()
                # The security machinery doesn't know about
                # IWeaklyAuthenticatedPrincipal yet, so do a manual
                # check. Later we can rely on the security machinery to
                # cause Unauthorized errors.
                if IWeaklyAuthenticatedPrincipal.providedBy(cur_principal):
                    if signed_msg.signature is None:
                        error_message = get_error_message('not-signed.txt')
                    else:
                        import_url = canonical_url(
                            getUtility(ILaunchBag).user) + '/+editpgpkeys'
                        error_message = get_error_message(
                            'key-not-registered.txt', import_url=import_url)
                    raise IncomingEmailError(error_message)

            if user.lower() == 'new':
                # A submit request.
                commands.insert(0, emailcommands.get('bug', ['new']))
                if signed_msg.signature is None:
                    raise IncomingEmailError(
                        get_error_message('not-gpg-signed.txt'))
            elif user.isdigit():
                # A comment to a bug. We set add_comment_to_bug to True so
                # that the comment gets added to the bug later. We don't add
                # the comment now, since we want to let the 'bug' command
                # handle the possible errors that can occur while getting
                # the bug.
                add_comment_to_bug = True
                commands.insert(0, emailcommands.get('bug', [user]))
            elif user.lower() == 'help':
                from_user = getUtility(ILaunchBag).user
                if from_user is not None:
                    preferredemail = from_user.preferredemail
                    if preferredemail is not None:
                        to_address = str(preferredemail.email)
                        self.sendHelpEmail(to_address)
                return True
            elif user.lower() != 'edit':
                # Indicate that we didn't handle the mail.
                return False

            bug = None
            bug_event = None
            bugtask = None
            bugtask_event = None

            processing_errors = []
            while len(commands) > 0:
                command = commands.pop(0)
                try:
                    if IBugEmailCommand.providedBy(command):
                        if bug_event is not None:
                            notify(bug_event)
                            bug_event = None

                        bug, bug_event = command.execute(
                            signed_msg, filealias)
                        if add_comment_to_bug:
                            messageset = getUtility(IMessageSet)
                            message = messageset.fromEmail(
                                signed_msg.as_string(),
                                owner=getUtility(ILaunchBag).user,
                                filealias=filealias,
                                parsed_message=signed_msg,
                                fallback_parent=bug.initial_message)

                            # If the new message's parent is linked to
                            # a bug watch we also link this message to
                            # that bug watch.
                            bug_message_set = getUtility(IBugMessageSet)
                            parent_bug_message = (
                                bug_message_set.getByBugAndMessage(
                                    bug, message.parent))

                            if (parent_bug_message is not None and
                                parent_bug_message.bugwatch):
                                bug_watch = parent_bug_message.bugwatch
                            else:
                                bug_watch = None

                            bugmessage = bug.linkMessage(
                                message, bug_watch)

                            notify(SQLObjectCreatedEvent(bugmessage))
                            add_comment_to_bug = False
                        else:
                            message = bug.initial_message
                        self.processAttachments(bug, message, signed_msg)
                    elif IBugTaskEmailCommand.providedBy(command):
                        if bugtask_event is not None:
                            if not ISQLObjectCreatedEvent.providedBy(
                                bug_event):
                                notify(bugtask_event)
                            bugtask_event = None
                        bugtask, bugtask_event = command.execute(bug)
                    elif IBugEditEmailCommand.providedBy(command):
                        bug, bug_event = command.execute(bug, bug_event)
                    elif IBugTaskEditEmailCommand.providedBy(command):
                        if bugtask is None:
                            bugtask = guess_bugtask(
                                bug, getUtility(ILaunchBag).user)
                            if bugtask is None:
                                raise IncomingEmailError(get_error_message(
                                    'no-default-affects.txt',
                                    bug_id=bug.id,
                                    nr_of_bugtasks=len(bug.bugtasks)))
                        bugtask, bugtask_event = command.execute(
                            bugtask, bugtask_event)

                except EmailProcessingError, error:
                    processing_errors.append((error, command))
                    if error.stop_processing:
                        commands = []
                        rollback()
                    else:
                        continue

            if len(processing_errors) > 0:
                raise IncomingEmailError(
                    '\n'.join(str(error) for error, command
                              in processing_errors),
                    [command for error, command in processing_errors])

            if bug_event is not None:
                try:
                    notify(bug_event)
                except CreatedBugWithNoBugTasksError:
                    rollback()
                    raise IncomingEmailError(
                        get_error_message('no-affects-target-on-submit.txt'))
            if bugtask_event is not None:
                if not ISQLObjectCreatedEvent.providedBy(bug_event):
                    notify(bugtask_event)

        except IncomingEmailError, error:
            send_process_error_notification(
                str(getUtility(ILaunchBag).user.preferredemail.email),
                'Submit Request Failure',
                error.message, signed_msg, error.failing_command)

        return True

    def sendHelpEmail(self, to_address):
        """Send usage help to `to_address`."""
        # Get the help text (formatted as MoinMoin markup)
        help_text = get_email_template('help.txt')
        help_text = reformat_wiki_text(help_text)
        # Wrap text
        mailwrapper = MailWrapper(width=72)
        help_text = mailwrapper.format(help_text)
        simple_sendmail(
            'help@bugs.launchpad.net', to_address,
            'Launchpad Bug Tracker Email Interface Help',
            help_text)

    # Some content types indicate that an attachment has a special
    # purpose. The current set is based on parsing emails from
    # one mail account and may need to be extended.
    #
    # Mail signatures are most likely generated by the mail client
    # and hence contain not data that is interesting except for
    # mail authentication.
    #
    # Resource forks of MacOS files are not easily represented outside
    # MacOS; if a resource fork contains useful debugging information,
    # the entire MacOS file should be sent encapsulated for example in
    # MacBinary format.
    #
    # application/ms-tnef attachment are created by Outlook; they 
    # seem to store no more than an RTF representation of an email.

    irrelevant_content_types = set((
        'application/applefile', # the resource fork of a MacOS file
        'application/pgp-signature',
        'application/pkcs7-signature',
        'application/x-pkcs7-signature',
        'text/x-vcard',
        'application/ms-tnef',
        ))

    def processAttachments(self, bug, message, signed_mail):
        """Create Bugattachments for "reasonable" mail attachments.

        A mail attachment is stored as a bugattachment if its
        content type is not listed in irrelevant_content_types.
        """
        for chunk in message.chunks:
            blob = chunk.blob
            if blob is None:
                continue
            # Mutt (other mail clients too?) appends the filename to the
            # content type.
            content_type = blob.mimetype.split(';', 1)[0]
            if content_type in self.irrelevant_content_types:
                continue

            if content_type in ('text/x-diff', 'text/x-patch'):
                attach_type = BugAttachmentType.PATCH
            else:
                attach_type = BugAttachmentType.UNSPECIFIED

            getUtility(IBugAttachmentSet).create(
                bug=bug, filealias=blob, attach_type=attach_type,
                title=blob.filename, message=message, send_notifications=True)


class AnswerTrackerHandler:
    """Handles emails sent to the Answer Tracker."""

    implements(IMailHandler)

    allow_unknown_users = False

    # XXX flacoste 2007-04-23: The 'ticket' part is there for backward
    # compatibility with the old notification address. We probably want to
    # remove it in the future.
    _question_address = re.compile(r'^(ticket|question)(?P<id>\d+)@.*')

    def process(self, signed_msg, to_addr, filealias=None, log=None):
        """See IMailHandler."""
        match = self._question_address.match(to_addr)
        if not match:
            return False

        question_id = int(match.group('id'))
        question = getUtility(IQuestionSet).get(question_id)
        if question is None:
            # No such question, don't process the email.
            return False

        messageset = getUtility(IMessageSet)
        message = messageset.fromEmail(
            signed_msg.parsed_string,
            owner=getUtility(ILaunchBag).user,
            filealias=filealias,
            parsed_message=signed_msg)

        if message.owner == question.owner:
            self.processOwnerMessage(question, message)
        else:
            self.processUserMessage(question, message)
        return True

    def processOwnerMessage(self, question, message):
        """Choose the right workflow action for a message coming from
        the question owner.

        When the question status is OPEN or NEEDINFO,
        the message is a GIVEINFO action; when the status is ANSWERED
        or EXPIRED, we interpret the message as a reopenening request;
        otherwise it's a comment.
        """
        if question.status in [
            QuestionStatus.OPEN, QuestionStatus.NEEDSINFO]:
            question.giveInfo(message)
        elif question.status in [
            QuestionStatus.ANSWERED, QuestionStatus.EXPIRED]:
            question.reopen(message)
        else:
            question.addComment(message.owner, message)

    def processUserMessage(self, question, message):
        """Choose the right workflow action for a message coming from a user
        that is not the question owner.

        When the question status is OPEN, NEEDSINFO, or ANSWERED, we interpret
        the message as containing an answer. (If it was really a request for
        more information, the owner will still be able to answer it while
        reopening the request.)

        In the other status, the message is a comment without status change.
        """
        if question.status in [
            QuestionStatus.OPEN, QuestionStatus.NEEDSINFO,
	    QuestionStatus.ANSWERED]:
            question.giveAnswer(message.owner, message)
        else:
            # In the other states, only a comment can be added.
            question.addComment(message.owner, message)


class InvalidBranchMergeProposalAddress(Exception):
    pass


class CodeHandler:

    addr_pattern = re.compile(r'(mp\+)([^@]+).*')

    def process(self, mail, email_addr, file_alias):
        try:
            self._process(mail, email_addr, file_alias)
        except:
            return False
        return True

    def _process(self, mail, email_addr, file_alias):
        merge_proposal = self.getBranchMergeProposal(email_addr)
        messageset = getUtility(IMessageSet)
        plain_message = messageset.fromEmail(
            mail.parsed_string,
            owner=getUtility(ILaunchBag).user,
            filealias=file_alias,
            parsed_message=mail)
        vote, vote_tag = self._getVote(mail)
        message = merge_proposal.createMessageFromMessage(
            plain_message, vote, vote_tag)

    @staticmethod
    def _getVote(message):
        content = get_main_body(message)
        if content is None:
            return None, None
        commands = parse_commands(content, ['vote'])
        if len(commands) == 0:
            return None, None
        args = commands[0][1]
        if len(args) == 0:
            return None, None
        else:
            vote_text = args[0]
        vote_tag_list = args[1:]
        vote = getattr(CodeReviewVote, vote_text.upper())
        if len(vote_tag_list) == 0:
            vote_tag = None
        else:
            vote_tag = ' '.join(vote_tag_list)
        return vote, vote_tag

    @classmethod
    def getBranchMergeProposal(klass, email_addr):
        match = klass.addr_pattern.match(email_addr)
        if match is None:
            raise InvalidBranchMergeProposalAddress(email_addr)
        try:
            merge_proposal_id = int(match.group(2))
        except ValueError:
            raise InvalidBranchMergeProposalAddress(email_addr)
        return getUtility(IBranchMergeProposalGetter).get(merge_proposal_id)


class SpecificationHandler:
    """Handles emails sent to specs.launchpad.net."""

    implements(IMailHandler)

    allow_unknown_users = True

    _spec_changes_address = re.compile(r'^notifications@.*')

    # The list of hosts where the Ubuntu wiki is located. We could do a
    # more general solution, but this kind of setup is unusual, and it
    # will be mainly the Ubuntu and Launchpad wikis that will use this
    # notification forwarder.
    UBUNTU_WIKI_HOSTS = [
        'wiki.ubuntu.com', 'wiki.edubuntu.org', 'wiki.kubuntu.org']

    def _getSpecByURL(self, url):
        """Returns a spec that is associated with the URL.

        It takes into account that the same Ubuntu wiki is on three
        different hosts.
        """
        scheme, host, path, params, query, fragment = urlparse(url)
        if host in self.UBUNTU_WIKI_HOSTS:
            for ubuntu_wiki_host in self.UBUNTU_WIKI_HOSTS:
                possible_url = urlunparse(
                    (scheme, ubuntu_wiki_host, path, params, query,
                     fragment))
                spec = getUtility(ISpecificationSet).getByURL(possible_url)
                if spec is not None:
                    return spec
        else:
            return getUtility(ISpecificationSet).getByURL(url)

    def process(self, signed_msg, to_addr, filealias=None, log=None):
        """See IMailHandler."""
        match = self._spec_changes_address.match(to_addr)
        if not match:
            # We handle only spec-changes at the moment.
            return False
        our_address = "notifications@%s" % config.launchpad.specs_domain
        # Check for emails that we sent.
        xloop = signed_msg['X-Loop']
        if xloop and our_address in signed_msg.get_all('X-Loop'):
            if log and filealias:
                log.warning(
                    'Got back a notification we sent: %s' %
                    filealias.http_url)
            return True
        # Check for emails that Launchpad sent us.
        if signed_msg['Sender'] == config.canonical.bounce_address:
            if log and filealias:
                log.warning('We received an email from Launchpad: %s'
                            % filealias.http_url)
            return True
        # When sending the email, the sender will be set so that it's
        # clear that we're the one sending the email, not the original
        # sender.
        del signed_msg['Sender']

        mail_body = signed_msg.get_payload(decode=True)
        spec_url = get_spec_url_from_moin_mail(mail_body)
        if spec_url is not None:
            if log is not None:
                log.debug('Found a spec URL: %s' % spec_url)
            spec = self._getSpecByURL(spec_url)
            if spec is not None:
                if log is not None:
                    log.debug('Found a corresponding spec: %s' % spec.name)
                # Add an X-Loop header, in order to prevent mail loop.
                signed_msg.add_header('X-Loop', our_address)
                notification_addresses = spec.notificationRecipientAddresses()
                if log is not None:
                    log.debug(
                        'Sending notification to: %s' %
                            ', '.join(notification_addresses))
                sendmail(signed_msg, to_addrs=notification_addresses)

            elif log is not None:
                log.debug(
                    "Didn't find a corresponding spec for %s" % spec_url)
        elif log is not None:
            log.debug("Didn't find a specification URL")
        return True


class MailHandlers:
    """All the registered mail handlers."""

    def __init__(self):
        self._handlers = {
            config.launchpad.bugs_domain: MaloneHandler(),
            config.launchpad.specs_domain: SpecificationHandler(),
            config.answertracker.email_domain: AnswerTrackerHandler(),
            # XXX flacoste 2007-04-23 Backward compatibility for old domain.
            # We probably want to remove it in the future.
            'support.launchpad.net': AnswerTrackerHandler(),
            config.vhost.code.hostname: CodeHandler(),
            }

    def get(self, domain):
        """Return the handler for the given email domain.

        Return None if no such handler exists.

            >>> handlers = MailHandlers()
            >>> handlers.get('bugs.launchpad.net') #doctest: +ELLIPSIS
            <...MaloneHandler...>
            >>> handlers.get('no.such.domain') is None
            True
        """
        return self._handlers.get(domain)

    def add(self, domain, handler):
        """Adds a handler for a domain.

            >>> handlers = MailHandlers()
            >>> handlers.get('some.domain') is None
            True
            >>> handler = object()
            >>> handlers.add('some.domain', handler)
            >>> handlers.get('some.domain') is handler
            True

        If there already is a handler for the domain, the old one will
        get overwritten:

            >>> new_handler = object()
            >>> handlers.add('some.domain', new_handler)
            >>> handlers.get('some.domain') is new_handler
            True
        """
        self._handlers[domain] = handler


mail_handlers = MailHandlers()
