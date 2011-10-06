# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


import operator
import os
import re

from bzrlib.branch import Branch
from bzrlib.errors import (
    NotAMergeDirective,
    NotBranchError,
    NotStacked,
    )
from bzrlib.merge_directive import MergeDirective
from bzrlib.transport import get_transport
from bzrlib.urlutils import join as urljoin
from lazr.uri import URI
from sqlobject import SQLObjectNotFound
import transaction
from zope.component import getUtility
from zope.interface import implements
from zope.security.interfaces import Unauthorized

from canonical.launchpad.mailnotification import (
    send_process_error_notification,
    )
from canonical.launchpad.webapp import urlparse
from canonical.launchpad.webapp.errorlog import globalErrorUtility
from canonical.launchpad.webapp.interfaces import ILaunchBag
from lp.code.bzr import get_branch_formats
from lp.code.enums import (
    BranchType,
    CodeReviewVote,
    )
from lp.code.errors import (
    BranchCreationException,
    BranchMergeProposalExists,
    UserNotBranchReviewer,
    )
from lp.code.interfaces.branchlookup import IBranchLookup
from lp.code.interfaces.branchmergeproposal import (
    IBranchMergeProposalGetter,
    ICreateMergeProposalJobSource,
    )
from lp.code.interfaces.branchnamespace import (
    lookup_branch_namespace,
    split_unique_name,
    )
from lp.code.interfaces.branchtarget import check_default_stacked_on
from lp.codehosting.bzrutils import is_branch_stackable
from lp.codehosting.vfs import get_lp_server
from lp.services.mail.commands import (
    EmailCommand,
    EmailCommandCollection,
    )
from lp.services.mail.helpers import (
    ensure_not_weakly_authenticated,
    get_error_message,
    get_main_body,
    get_person_or_team,
    IncomingEmailError,
    parse_commands,
    )
from lp.services.mail.interfaces import (
    EmailProcessingError,
    IMailHandler,
    )
from lp.services.mail.sendmail import simple_sendmail
from lp.services.messages.interfaces.message import IMessageSet


error_templates = os.path.join(os.path.dirname(__file__), 'errortemplates')


class BadBranchMergeProposalAddress(Exception):
    """The user-supplied address is not an acceptable value."""


class InvalidBranchMergeProposalAddress(BadBranchMergeProposalAddress):
    """The user-supplied address is not an acceptable value."""


class NonExistantBranchMergeProposalAddress(BadBranchMergeProposalAddress):
    """The BranchMergeProposal specified by the address does not exist."""


class InvalidVoteString(Exception):
    """The user-supplied vote is not an acceptable value."""


class NonLaunchpadTarget(Exception):
    """Target branch is not registered with Launchpad."""


class MissingMergeDirective(Exception):
    """Emailed merge proposal lacks a merge directive"""


class CodeReviewEmailCommandExecutionContext:
    """Passed as the only parameter to each code review email command.

    The execution context is created once for each email and then passed to
    each command object as the execution parameter.  The resulting vote and
    vote tags in the context are used in the final code review comment
    creation.
    """

    def __init__(self, merge_proposal, user, notify_event_listeners=True):
        self.merge_proposal = merge_proposal
        self.user = user
        self.vote = None
        self.vote_tags = None
        self.notify_event_listeners = notify_event_listeners


class CodeReviewEmailCommand(EmailCommand):
    """Commands specific to code reviews."""

    # Some code commands need to happen before others, so we order them.
    sort_order = 1

    def execute(self, context):
        raise NotImplementedError


class VoteEmailCommand(CodeReviewEmailCommand):
    """Record the vote to add to the comment."""

    # Votes should happen first, so set the order lower than
    # status updates.
    sort_order = 0

    _vote_alias = {
        '+1': CodeReviewVote.APPROVE,
        '+0': CodeReviewVote.ABSTAIN,
        '0': CodeReviewVote.ABSTAIN,
        '-0': CodeReviewVote.ABSTAIN,
        '-1': CodeReviewVote.DISAPPROVE,
        'needsfixing': CodeReviewVote.NEEDS_FIXING,
        'needs-fixing': CodeReviewVote.NEEDS_FIXING,
        'needsinfo': CodeReviewVote.NEEDS_INFO,
        'needs-info': CodeReviewVote.NEEDS_INFO,
        'needsinformation': CodeReviewVote.NEEDS_INFO,
        'needs_information': CodeReviewVote.NEEDS_INFO,
        'needs-information': CodeReviewVote.NEEDS_INFO,
        }

    def execute(self, context):
        """Extract the vote and tags from the args."""
        if len(self.string_args) == 0:
            raise EmailProcessingError(
                get_error_message(
                    'num-arguments-mismatch.txt',
                    command_name='review',
                    num_arguments_expected='one or more',
                    num_arguments_got='0'))

        vote_string = self.string_args[0]
        vote_tag_list = self.string_args[1:]
        try:
            context.vote = CodeReviewVote.items[vote_string.upper()]
        except KeyError:
            # If the word doesn't match, check aliases that we allow.
            context.vote = self._vote_alias.get(vote_string)
            if context.vote is None:
                # Replace the _ with - in the names of the items.
                # Slightly easier to type and read.
                valid_votes = ', '.join(sorted(
                    v.name.lower().replace('_', '-')
                    for v in CodeReviewVote.items.items))
                raise EmailProcessingError(
                    get_error_message(
                        'dbschema-command-wrong-argument.txt',
                        command_name='review',
                        arguments=valid_votes,
                        example_argument='needs-fixing'))

        if len(vote_tag_list) > 0:
            context.vote_tags = ' '.join(vote_tag_list)


class UpdateStatusEmailCommand(CodeReviewEmailCommand):
    """Update the status of the merge proposal."""

    _numberOfArguments = 1

    def execute(self, context):
        """Update the status of the merge proposal."""
        # Only accepts approved, and rejected for now.
        self._ensureNumberOfArguments()
        new_status = self.string_args[0].lower()
        # Grab the latest rev_id from the source branch.
        # This is what the browser code does right now.
        rev_id = context.merge_proposal.source_branch.last_scanned_id
        try:
            if new_status in ('approved', 'approve'):
                if context.vote is None:
                    context.vote = CodeReviewVote.APPROVE
                context.merge_proposal.approveBranch(context.user, rev_id)
            elif new_status in ('rejected', 'reject'):
                if context.vote is None:
                    context.vote = CodeReviewVote.DISAPPROVE
                context.merge_proposal.rejectBranch(context.user, rev_id)
            else:
                raise EmailProcessingError(
                    get_error_message(
                        'dbschema-command-wrong-argument.txt',
                        command_name=self.name,
                        arguments='approved, rejected',
                        example_argument='approved'))
        except (UserNotBranchReviewer, Unauthorized):
            raise EmailProcessingError(
                get_error_message(
                    'user-not-reviewer.txt',
                    error_templates=error_templates,
                    command_name=self.name,
                    target=context.merge_proposal.target_branch.bzr_identity))


class AddReviewerEmailCommand(CodeReviewEmailCommand):
    """Add a new reviewer."""

    def execute(self, context):
        reviewer, review_tags = CodeEmailCommands.parseReviewRequest(
            self.name, self.string_args)
        context.merge_proposal.nominateReviewer(
            reviewer, context.user, review_tags,
            _notify_listeners=context.notify_event_listeners)


class CodeEmailCommands(EmailCommandCollection):
    """A colleciton of email commands for code."""

    _commands = {
        'vote': VoteEmailCommand,
        'review': VoteEmailCommand,
        'status': UpdateStatusEmailCommand,
        'merge': UpdateStatusEmailCommand,
        'reviewer': AddReviewerEmailCommand,
        }

    @classmethod
    def getCommands(klass, message_body):
        """Extract the commands from the message body."""
        if message_body is None:
            return []
        commands = [klass.get(name=name, string_args=args) for
                    name, args in parse_commands(message_body,
                                                 klass._commands.keys())]
        return sorted(commands, key=operator.attrgetter('sort_order'))

    @classmethod
    def parseReviewRequest(klass, op_name, string_args):
        if len(string_args) == 0:
            raise EmailProcessingError(
                get_error_message(
                    'num-arguments-mismatch.txt',
                    command_name=op_name,
                    num_arguments_expected='one or more',
                    num_arguments_got='0'))

        # Pop the first arg as the reviewer.
        reviewer = get_person_or_team(string_args.pop(0))
        if len(string_args) > 0:
            review_tags = ' '.join(string_args)
        else:
            review_tags = None
        return (reviewer, review_tags)


class CodeHandler:
    """Mail handler for the code domain."""
    implements(IMailHandler)

    addr_pattern = re.compile(r'(mp\+)([^@]+).*')
    allow_unknown_users = False

    def process(self, mail, email_addr, file_alias):
        """Process an email for the code domain.

        Emails may be converted to CodeReviewComments, and / or
        deferred to jobs to create BranchMergeProposals.
        """
        if email_addr.startswith('merge@'):
            return self.createMergeProposalJob(mail, email_addr, file_alias)
        else:
            try:
                return self.processComment(mail, email_addr, file_alias)
            except AssertionError:
                body = get_error_message('messagemissingsubject.txt')
                simple_sendmail('merge@code.launchpad.net',
                    [mail.get('from')],
                    'Error Creating Merge Proposal', body)
                return True

    def createMergeProposalJob(self, mail, email_addr, file_alias):
        """Check that the message is signed and create the job."""
        try:
            ensure_not_weakly_authenticated(
                mail, email_addr, 'not-signed-md.txt',
                'key-not-registered-md.txt', error_templates)
        except IncomingEmailError, error:
            user = getUtility(ILaunchBag).user
            send_process_error_notification(
                str(user.preferredemail.email),
                'Submit Request Failure',
                error.message, mail, error.failing_command)
            transaction.abort()
        else:
            getUtility(ICreateMergeProposalJobSource).create(file_alias)
        return True

    def processCommands(self, context, commands):
        """Process the various merge proposal commands against the context."""
        processing_errors = []

        for command in commands:
            try:
                command.execute(context)
            except EmailProcessingError, error:
                processing_errors.append((error, command))

        if len(processing_errors) > 0:
            errors, commands = zip(*processing_errors)
            raise IncomingEmailError(
                '\n'.join(str(error) for error in errors),
                list(commands))

        return len(commands)

    def processComment(self, mail, email_addr, file_alias):
        """Process an email and create a CodeReviewComment.

        The only mail command understood is 'vote', which takes 'approve',
        'disapprove', or 'abstain' as values.  Specifically, it takes
        any CodeReviewVote item value, case-insensitively.
        :return: True.
        """
        user = getUtility(ILaunchBag).user
        try:
            merge_proposal = self.getBranchMergeProposal(email_addr)
        except NonExistantBranchMergeProposalAddress:
            send_process_error_notification(
                str(user.preferredemail.email),
                'Submit Request Failure',
                'There is no merge proposal at %s' % email_addr,
                mail)
            return True
        except BadBranchMergeProposalAddress:
            return False
        context = CodeReviewEmailCommandExecutionContext(merge_proposal, user)
        try:
            email_body_text = get_main_body(mail)
            commands = CodeEmailCommands.getCommands(email_body_text)
            processed_count = self.processCommands(context, commands)

            # Make sure that the email is in fact signed.
            if processed_count > 0:
                ensure_not_weakly_authenticated(mail, 'code review')

            message = getUtility(IMessageSet).fromEmail(
                mail.parsed_string,
                owner=getUtility(ILaunchBag).user,
                filealias=file_alias,
                parsed_message=mail)
            merge_proposal.createCommentFromMessage(
                message, context.vote, context.vote_tags, mail)

        except IncomingEmailError, error:
            send_process_error_notification(
                str(user.preferredemail.email),
                'Submit Request Failure',
                error.message, mail, error.failing_command)
            transaction.abort()
        return True

    @staticmethod
    def _getReplyAddress(mail):
        """The address to use for automatic replies."""
        return mail.get('Reply-to', mail['From'])

    @classmethod
    def getBranchMergeProposal(klass, email_addr):
        """Return branch merge proposal designated by email_addr.

        Addresses are of the form mp+5@code.launchpad.net, where 5 is the
        database id of the related branch merge proposal.

        The inverse operation is BranchMergeProposal.address.
        """
        match = klass.addr_pattern.match(email_addr)
        if match is None:
            raise InvalidBranchMergeProposalAddress(email_addr)
        try:
            merge_proposal_id = int(match.group(2))
        except ValueError:
            raise InvalidBranchMergeProposalAddress(email_addr)
        getter = getUtility(IBranchMergeProposalGetter)
        try:
            return getter.get(merge_proposal_id)
        except SQLObjectNotFound:
            raise NonExistantBranchMergeProposalAddress(email_addr)

    def _acquireBranchesForProposal(self, md, submitter):
        """Find or create DB Branches from a MergeDirective.

        If the target is not a Launchpad branch, NonLaunchpadTarget will be
        raised.  If the source is not a Launchpad branch, a REMOTE branch will
        be created implicitly, with submitter as its owner/registrant.

        :param md: The `MergeDirective` to get branch URLs from.
        :param submitter: The `Person` who requested that the merge be
            performed.
        :return: source_branch, target_branch
        """
        mp_target = getUtility(IBranchLookup).getByUrl(md.target_branch)
        if mp_target is None:
            raise NonLaunchpadTarget()
        # If the target branch cannot be stacked upon, then don't try to stack
        # upon it or get revisions form it.
        if md.bundle is None or check_default_stacked_on(mp_target) is None:
            mp_source = self._getSourceNoBundle(
                md, mp_target, submitter)
        else:
            mp_source = self._getSourceWithBundle(
                md, mp_target, submitter)
        return mp_source, mp_target

    @staticmethod
    def _getNewBranchInfo(url, target_branch, submitter):
        """Return the namespace and basename for a branch.

        If an LP URL is provided, the namespace and basename will match the
        LP URL.

        Otherwise, the target is used to determine the namespace, and the base
        depends on what was supplied.

        If a URL is supplied, its base is used.

        If no URL is supplied, 'merge' is used as the base.

        :param url: The public URL of the source branch, if any.
        :param target_branch: The target branch.
        :param submitter: The person submitting the merge proposal.
        """
        if url is not None:
            url = url.rstrip('/')
            branches = getUtility(IBranchLookup)
            unique_name = branches.uriToUniqueName(URI(url))
            if unique_name is not None:
                namespace_name, base = split_unique_name(unique_name)
                return lookup_branch_namespace(namespace_name), base
        if url is None:
            basename = 'merge'
        else:
            basename = urlparse(url)[2].split('/')[-1]
        namespace = target_branch.target.getNamespace(submitter)
        return namespace, basename

    def _getNewBranch(self, branch_type, url, target, submitter):
        """Return a new database branch.

        :param branch_type: The type of branch to create.
        :param url: The public location of the branch to create.
        :param product: The product associated with the branch to create.
        :param submitter: The person who requested the merge.
        """
        namespace, basename = self._getNewBranchInfo(url, target, submitter)
        if branch_type == BranchType.REMOTE:
            db_url = url
        else:
            db_url = None
        return namespace.createBranchWithPrefix(
            branch_type, basename, submitter, url=db_url)

    def _getSourceNoBundle(self, md, target, submitter):
        """Get a source branch for a merge directive with no bundle."""
        source_db_branch = getUtility(IBranchLookup).getByUrl(
            md.source_branch)
        if source_db_branch is None:
            source_db_branch = self._getNewBranch(
                BranchType.REMOTE, md.source_branch, target, submitter)
        return source_db_branch

    def _getOrCreateDBBranch(self, md, db_target, submitter):
        """Return the source branch, creating a new branch if necessary."""
        db_source = None
        if md.source_branch is not None:
            db_source = getUtility(IBranchLookup).getByUrl(md.source_branch)
        if db_source is None:
            db_source = self._getNewBranch(
                BranchType.HOSTED, md.source_branch, db_target, submitter)
            # Commit the transaction to make sure the new source branch is
            # visible to the XMLRPC server which provides the virtual file
            # system information.
            transaction.commit()
        return db_source

    def _openSourceBzrBranch(self, source_url, target_url, stacked_url):
        """Open the source bzr branch, creating a new branch if necessary."""
        try:
            return Branch.open(source_url)
        except NotBranchError:
            bzr_target = Branch.open(target_url)
            transport = get_transport(
                source_url,
                possible_transports=[bzr_target.bzrdir.root_transport])
            bzrdir = bzr_target.bzrdir.sprout(
                transport.base, bzr_target.last_revision(),
                force_new_repo=True, stacked=True, create_tree_if_local=False,
                possible_transports=[transport], source_branch=bzr_target)
            bzr_branch = bzrdir.open_branch()
            # Set the stacked url to be the relative url for the target.
            bzr_branch.set_stacked_on_url(stacked_url)
            return bzr_branch

    def _getSourceWithBundle(self, md, db_target, submitter):
        """Get a source branch for a merge directive with a bundle."""
        db_source = self._getOrCreateDBBranch(md, db_target, submitter)
        # Make sure that the target branch is stackable so that we only
        # install the revisions unique to the source branch. If the target
        # branch is not stackable, return the existing branch or a new hosted
        # source branch - one that has *no* Bazaar data.  Together these
        # prevent users from using Launchpad disk space at a rate that is
        # disproportionately greater than data uploaded.
        mirrored_bzr_target = db_target.getBzrBranch()
        if not is_branch_stackable(mirrored_bzr_target):
            return db_source
        assert db_source.branch_type == BranchType.HOSTED, (
            "Source branch is not hosted.")

        # Create the LP server as if the submitter was pushing a branch to LP.
        lp_server = get_lp_server(submitter.id)
        lp_server.start_server()
        try:
            source_url = urljoin(lp_server.get_url(), db_source.unique_name)
            target_url = urljoin(lp_server.get_url(), db_target.unique_name)
            stacked_url = '/' + db_target.unique_name
            bzr_source = self._openSourceBzrBranch(
                source_url, target_url, stacked_url)
            if is_branch_stackable(bzr_source):
                # Set the stacked on URL if not set.
                try:
                    bzr_source.get_stacked_on_url()
                except NotStacked:
                    # We don't currently support pulling in the revisions if
                    # the source branch exists and isn't stacked.
                    # XXX Tim Penhey 2010-07-27 bug 610292
                    # We should fail here and return an oops email to the
                    # user.
                    return db_source
                self._pullRevisionsFromMergeDirectiveIntoSourceBranch(
                    md, target_url, bzr_source)
                # Get the puller to pull the branch into the mirrored area.
                formats = get_branch_formats(bzr_source)
                db_source.branchChanged(
                    stacked_url, bzr_source.last_revision(), *formats)
            return db_source
        finally:
            lp_server.stop_server()

    def _pullRevisionsFromMergeDirectiveIntoSourceBranch(self, md,
                                                         target_url,
                                                         bzr_branch):
        """Pull the revisions from the merge directive into the branch.

        :param md: The merge directive
        :param target_url: The URL of the branch that the merge directive is
            targetting using the user's LP transport.
        :param bzr_branch: The bazaar branch entity for the branch that the
            revisions from the merge directive are being pulled into.
        """
        # Tell the merge directive to use the user's LP transport URL to get
        # access to any needed but not supplied revisions.
        md.target_branch = target_url
        md.install_revisions(bzr_branch.repository)
        bzr_branch.lock_write()
        try:
            bzr_branch.pull(bzr_branch, stop_revision=md.revision_id,
                            overwrite=True)
        finally:
            bzr_branch.unlock()

    def findMergeDirectiveAndComment(self, message):
        """Extract the comment and Merge Directive from a SignedMessage."""
        body = None
        md = None
        for part in message.walk():
            if part.is_multipart():
                continue
            payload = part.get_payload(decode=True)
            content_type = part.get('Content-type', 'text/plain').lower()
            if content_type.startswith('text/plain'):
                body = payload
                charset = part.get_param('charset')
                if charset is not None:
                    body = body.decode(charset)
            try:
                md = MergeDirective.from_lines(payload.splitlines(True))
            except NotAMergeDirective:
                pass
            if None not in (body, md):
                return body, md
        else:
            raise MissingMergeDirective()

    def processMergeProposal(self, message):
        """Generate a merge proposal (and comment) from an email message.

        The message is expected to contain a merge directive in one of its
        parts.  Its values are used to generate a BranchMergeProposal.
        If the message has a non-empty body, it is turned into a
        CodeReviewComment.
        """
        submitter = getUtility(ILaunchBag).user
        try:
            email_body_text, md = self.findMergeDirectiveAndComment(message)
        except MissingMergeDirective:
            body = get_error_message(
                'missingmergedirective.txt',
                error_templates=error_templates)
            simple_sendmail('merge@code.launchpad.net',
                [message.get('from')],
                'Error Creating Merge Proposal', body)
            return
        oops_message = (
            'target: %r source: %r' %
            (md.target_branch, md.source_branch))
        with globalErrorUtility.oopsMessage(oops_message):
            try:
                source, target = self._acquireBranchesForProposal(
                    md, submitter)
            except NonLaunchpadTarget:
                body = get_error_message('nonlaunchpadtarget.txt',
                    error_templates=error_templates,
                    target_branch=md.target_branch)
                simple_sendmail('merge@code.launchpad.net',
                    [message.get('from')],
                    'Error Creating Merge Proposal', body)
                return
            except BranchCreationException, e:
                body = get_error_message(
                        'branch-creation-exception.txt',
                        error_templates=error_templates,
                        reason=e)
                simple_sendmail('merge@code.launchpad.net',
                    [message.get('from')],
                    'Error Creating Merge Proposal', body)
                return
        with globalErrorUtility.oopsMessage(
            'target: %r source: %r' % (target, source)):
            try:
                # When creating a merge proposal, we need to gather all
                # necessary arguments to addLandingTarget(). So from the email
                # body we need to extract: reviewer, review type, description.
                description = None
                review_requests = []
                email_body_text = email_body_text.strip()
                if email_body_text != '':
                    description = email_body_text
                    review_args = parse_commands(
                        email_body_text, ['reviewer'])
                    if len(review_args) > 0:
                        cmd, args = review_args[0]
                        review_request = (
                            CodeEmailCommands.parseReviewRequest(cmd, args))
                        review_requests.append(review_request)

                bmp = source.addLandingTarget(submitter, target,
                                              needs_review=True,
                                              description=description,
                                              review_requests=review_requests)
                return bmp

            except BranchMergeProposalExists:
                body = get_error_message(
                    'branchmergeproposal-exists.txt',
                    error_templates=error_templates,
                    source_branch=source.bzr_identity,
                    target_branch=target.bzr_identity)
                simple_sendmail('merge@code.launchpad.net',
                    [message.get('from')],
                    'Error Creating Merge Proposal', body)
                transaction.abort()
            except IncomingEmailError, error:
                send_process_error_notification(
                    str(submitter.preferredemail.email),
                    'Submit Request Failure',
                    error.message, email_body_text, error.failing_command)
                transaction.abort()
