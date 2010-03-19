# Copyright 2009, 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).


"""Job classes related to BranchMergeProposals are in here.

This includes both jobs for the proposals themselves, or jobs that are
creating proposals, or diffs relating to the proposals.
"""


from __future__ import with_statement


__metaclass__ = type


__all__ = [
    'BranchMergeProposalJob',
    'CodeReviewCommentEmailJob',
    'CreateMergeProposalJob',
    'MergeProposalCreatedJob',
    'ReviewRequestedEmailJob',
    'UpdatePreviewDiffJob',
    ]

import contextlib
from email.utils import parseaddr
import transaction

from lazr.delegates import delegates
from lazr.enum import DBEnumeratedType, DBItem
import simplejson
from sqlobject import SQLObjectNotFound
from storm.base import Storm
from storm.expr import And, Or
from storm.locals import Int, Reference, Unicode
from storm.store import Store
from zope.component import getUtility
from zope.interface import classProvides, implements

from canonical.database.enumcol import EnumCol
from canonical.launchpad.database.message import MessageJob, MessageJobAction
from canonical.launchpad.interfaces.message import IMessageJob
from canonical.launchpad.webapp import errorlog
from canonical.launchpad.webapp.interaction import setupInteraction
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR, IPlacelessAuthUtility, IStoreSelector, MAIN_STORE,
    MASTER_FLAVOR)
from lp.code.enums import BranchType
from lp.code.interfaces.branchmergeproposal import (
    IBranchMergeProposalJob, ICodeReviewCommentEmailJob,
    ICodeReviewCommentEmailJobSource, ICreateMergeProposalJob,
    ICreateMergeProposalJobSource, IMergeProposalCreatedJob,
    IMergeProposalCreatedJobSource, IMergeProposalUpdatedEmailJob,
    IMergeProposalUpdatedEmailJobSource, IReviewRequestedEmailJob,
    IReviewRequestedEmailJobSource, IUpdatePreviewDiffJobSource,
    )
from lp.code.mail.branch import RecipientReason
from lp.code.mail.branchmergeproposal import BMPMailer
from lp.code.mail.codereviewcomment import CodeReviewCommentMailer
from lp.code.model.branchmergeproposal import BranchMergeProposal
from lp.code.model.diff import PreviewDiff
from lp.codehosting.vfs import get_multi_server, get_scanner_server
from lp.registry.interfaces.person import IPersonSet
from lp.services.job.model.job import Job
from lp.services.job.interfaces.job import IRunnableJob
from lp.services.job.runner import BaseRunnableJob


class BranchMergeProposalJobType(DBEnumeratedType):
    """Values that ICodeImportJob.state can take."""

    MERGE_PROPOSAL_CREATED = DBItem(0, """
        Merge proposal created

        This job generates the review diff for a BranchMergeProposal if
        needed, then sends mail to all interested parties.
        """)

    UPDATE_PREVIEW_DIFF = DBItem(1, """
        Update the preview diff for the BranchMergeProposal.

        This job generates the preview diff for a BranchMergeProposal.
        """)

    CODE_REVIEW_COMMENT_EMAIL = DBItem(2, """
        Send the code review comment to the subscribers.

        This job sends the email to the merge proposal subscribers and
        reviewers.
        """)

    REVIEW_REQUEST_EMAIL = DBItem(3, """
        Send the review request email to the requested reviewer.

        This job sends an email to the requested reviewer, or members of the
        requested reviewer team asking them to review the proposal.
        """)

    MERGE_PROPOSAL_UPDATED = DBItem(4, """
        Merge proposal updated

        This job sends an email to the subscribers informing them of fields
        that have been changed on the merge proposal itself.
        """)


class BranchMergeProposalJob(Storm):
    """Base class for jobs related to branch merge proposals."""

    implements(IBranchMergeProposalJob)

    __storm_table__ = 'BranchMergeProposalJob'

    id = Int(primary=True)

    jobID = Int('job')
    job = Reference(jobID, Job.id)

    branch_merge_proposalID = Int('branch_merge_proposal', allow_none=False)
    branch_merge_proposal = Reference(
        branch_merge_proposalID, BranchMergeProposal.id)

    job_type = EnumCol(enum=BranchMergeProposalJobType, notNull=True)

    _json_data = Unicode('json_data')

    @property
    def metadata(self):
        return simplejson.loads(self._json_data)

    def __init__(self, branch_merge_proposal, job_type, metadata):
        """Constructor.

        :param branch_merge_proposal: The proposal this job relates to.
        :param job_type: The BranchMergeProposalJobType of this job.
        :param metadata: The type-specific variables, as a JSON-compatible
            dict.
        """
        Storm.__init__(self)
        json_data = simplejson.dumps(metadata)
        self.job = Job()
        self.branch_merge_proposal = branch_merge_proposal
        self.job_type = job_type
        # XXX AaronBentley 2009-01-29 bug=322819: This should be a bytestring,
        # but the DB representation is unicode.
        self._json_data = json_data.decode('utf-8')

    def sync(self):
        store = Store.of(self)
        store.flush()
        store.autoreload(self)

    def destroySelf(self):
        Store.of(self).remove(self)

    @classmethod
    def selectBy(klass, **kwargs):
        """Return selected instances of this class.

        At least one pair of keyword arguments must be supplied.
        foo=bar is interpreted as 'select all instances of
        BranchMergeProposalJob whose property "foo" is equal to "bar"'.
        """
        assert len(kwargs) > 0
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(klass, **kwargs)

    @classmethod
    def get(klass, key):
        """Return the instance of this class whose key is supplied.

        :raises: SQLObjectNotFound
        """
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        instance = store.get(klass, key)
        if instance is None:
            raise SQLObjectNotFound(
                'No occurrence of %s has key %s' % (klass.__name__, key))
        return instance


class BranchMergeProposalJobDerived(BaseRunnableJob):

    """Intermediate class for deriving from BranchMergeProposalJob."""
    delegates(IBranchMergeProposalJob)

    def __init__(self, job):
        self.context = job

    @classmethod
    def create(cls, bmp):
        """See `IMergeProposalCreationJob`."""
        job = BranchMergeProposalJob(
            bmp, cls.class_job_type, {})
        return cls(job)

    @classmethod
    def get(cls, job_id):
        """Get a job by id.

        :return: the BranchMergeProposalJob with the specified id, as the
            current BranchMergeProposalJobDereived subclass.
        :raises: SQLObjectNotFound if there is no job with the specified id,
            or its job_type does not match the desired subclass.
        """
        job = BranchMergeProposalJob.get(job_id)
        if job.job_type != cls.class_job_type:
            raise SQLObjectNotFound(
                'No object found with id %d and type %s' % (job_id,
                cls.class_job_type.title))
        return cls(job)

    @classmethod
    def iterReady(klass):
        """Iterate through all ready BranchMergeProposalJobs."""
        from lp.code.model.branch import Branch
        store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
        jobs = store.find(
            (BranchMergeProposalJob),
            And(BranchMergeProposalJob.job_type == klass.class_job_type,
                BranchMergeProposalJob.job == Job.id,
                Job.id.is_in(Job.ready_jobs),
                BranchMergeProposalJob.branch_merge_proposal
                    == BranchMergeProposal.id,
                BranchMergeProposal.source_branch == Branch.id,
                # A proposal isn't considered ready if it has no revisions,
                # or if it is hosted but pending a mirror.
                Branch.revision_count > 0,
                Or(Branch.next_mirror_time == None,
                   Branch.branch_type != BranchType.HOSTED)
                ))
        return (klass(job) for job in jobs)

    def getOopsVars(self):
        """See `IRunnableJob`."""
        vars =  BaseRunnableJob.getOopsVars(self)
        bmp = self.context.branch_merge_proposal
        vars.extend([
            ('branchmergeproposal_job_id', self.context.id),
            ('branchmergeproposal_job_type', self.context.job_type.title),
            ('source_branch', bmp.source_branch.unique_name),
            ('target_branch', bmp.target_branch.unique_name)])
        return vars


class MergeProposalCreatedJob(BranchMergeProposalJobDerived):
    """See `IMergeProposalCreatedJob`."""

    implements(IMergeProposalCreatedJob)

    classProvides(IMergeProposalCreatedJobSource)

    class_job_type = BranchMergeProposalJobType.MERGE_PROPOSAL_CREATED

    def run(self, _create_preview=True):
        """See `IMergeProposalCreatedJob`."""
        # _create_preview can be set False for testing purposes.
        if _create_preview:
            preview_diff = PreviewDiff.fromBranchMergeProposal(
                self.branch_merge_proposal)
            self.branch_merge_proposal.preview_diff = preview_diff
            transaction.commit()
        mailer = BMPMailer.forCreation(
            self.branch_merge_proposal, self.branch_merge_proposal.registrant)
        mailer.sendAll()

    @staticmethod
    def _findRevisions(bzr_source, bzr_target):
        """Return the revisions to use for a review diff."""
        source_revision = bzr_source.last_revision()
        target_revision = bzr_target.last_revision()
        graph = bzr_target.repository.get_graph(bzr_source.repository)
        lca = graph.find_unique_lca(source_revision, target_revision)
        return lca, source_revision

    def getOopsRecipients(self):
        return [self.branch_merge_proposal.registrant.preferredemail.email]

    def getOperationDescription(self):
        return ('notifying people about the proposal to merge %s into %s' %
            (self.branch_merge_proposal.source_branch.bzr_identity,
             self.branch_merge_proposal.target_branch.bzr_identity))


class UpdatePreviewDiffJob(BranchMergeProposalJobDerived):
    """A job to update the preview diff for a branch merge proposal.

    Provides class methods to create and retrieve such jobs.
    """

    implements(IRunnableJob)

    classProvides(IUpdatePreviewDiffJobSource)

    class_job_type = BranchMergeProposalJobType.UPDATE_PREVIEW_DIFF

    @staticmethod
    @contextlib.contextmanager
    def contextManager():
        """See `IUpdatePreviewDiffJobSource`."""
        errorlog.globalErrorUtility.configure('update_preview_diffs')
        server = get_scanner_server()
        server.start_server()
        yield
        server.stop_server()

    def run(self):
        """See `IRunnableJob`."""
        preview = PreviewDiff.fromBranchMergeProposal(
            self.branch_merge_proposal)
        self.branch_merge_proposal.preview_diff = preview


class CreateMergeProposalJob(BaseRunnableJob):
    """See `ICreateMergeProposalJob` and `ICreateMergeProposalJobSource`."""

    classProvides(ICreateMergeProposalJobSource)

    delegates(IMessageJob)

    class_action = MessageJobAction.CREATE_MERGE_PROPOSAL

    implements(ICreateMergeProposalJob)

    def __init__(self, context):
        """Create an instance of CreateMergeProposalJob.

        :param context: a MessageJob.
        """
        self.context = context

    def __eq__(self, other):
        return (self.__class__ == other.__class__ and
                self.context == other.context)

    @classmethod
    def create(klass, message_bytes):
        """See `ICreateMergeProposalJobSource`."""
        context = MessageJob(
            message_bytes, MessageJobAction.CREATE_MERGE_PROPOSAL)
        return klass(context)

    @classmethod
    def iterReady(klass):
        """Iterate through all ready BranchMergeProposalJobs."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
        jobs = store.find(
            (MessageJob),
            And(MessageJob.action == klass.class_action,
                MessageJob.job == Job.id,
                Job.id.is_in(Job.ready_jobs)))
        return (klass(job) for job in jobs)

    def run(self):
        """See `ICreateMergeProposalJob`."""
        # Avoid circular import
        from lp.code.mail.codehandler import CodeHandler
        url = self.context.message_bytes.getURL()
        with errorlog.globalErrorUtility.oopsMessage('Mail url: %r' % url):
            message = self.getMessage()
            # Since the message was checked as signed before it was saved in
            # the Librarian, just create the principal from the sender and set
            # up the interaction.
            name, email_addr = parseaddr(message['From'])
            authutil = getUtility(IPlacelessAuthUtility)
            principal = authutil.getPrincipalByLogin(email_addr)
            if principal is None:
                raise AssertionError('No principal found for %s' % email_addr)
            setupInteraction(principal, email_addr)

            server = get_multi_server(write_hosted=True)
            server.start_server()
            try:
                return CodeHandler().processMergeProposal(message)
            finally:
                server.stop_server()

    def getOopsRecipients(self):
        message = self.getMessage()
        from_ = message['From']
        if from_ is None:
            return []
        return [from_]

    def getOperationDescription(self):
        message = self.getMessage()
        return ('creating a merge proposal from message with subject %s' %
                message['Subject'])


class CodeReviewCommentEmailJob(BranchMergeProposalJobDerived):
    """A job to send a code review comment.

    Provides class methods to create and retrieve such jobs.
    """

    implements(ICodeReviewCommentEmailJob)

    classProvides(ICodeReviewCommentEmailJobSource)

    class_job_type = BranchMergeProposalJobType.CODE_REVIEW_COMMENT_EMAIL

    def run(self):
        """See `IRunnableJob`."""
        mailer = CodeReviewCommentMailer.forCreation(self.code_review_comment)
        mailer.sendAll()

    @classmethod
    def create(cls, code_review_comment):
        """See `ICodeReviewCommentEmailJobSource`."""
        metadata = cls.getMetadata(code_review_comment)
        bmp = code_review_comment.branch_merge_proposal
        job = BranchMergeProposalJob(bmp, cls.class_job_type, metadata)
        return cls(job)

    @staticmethod
    def getMetadata(code_review_comment):
        return {'code_review_comment': code_review_comment.id}

    @property
    def code_review_comment(self):
        """Get the code review comment."""
        return self.branch_merge_proposal.getComment(
            self.metadata['code_review_comment'])

    def getOopsVars(self):
        """See `IRunnableJob`."""
        vars =  BranchMergeProposalJobDerived.getOopsVars(self)
        vars.extend([
            ('code_review_comment', self.metadata['code_review_comment']),
            ])
        return vars

    def getErrorRecipients(self):
        """Return a list of email-ids to notify about user errors."""
        commenter = self.code_review_comment.message.owner
        return [commenter.preferredemail]


class ReviewRequestedEmailJob(BranchMergeProposalJobDerived):
    """Send email to the reviewer telling them to review the proposal.

    Provides class methods to create and retrieve such jobs.
    """

    implements(IReviewRequestedEmailJob)

    classProvides(IReviewRequestedEmailJobSource)

    class_job_type = BranchMergeProposalJobType.REVIEW_REQUEST_EMAIL

    def run(self):
        """See `IRunnableJob`."""
        reason = RecipientReason.forReviewer(
            self.branch_merge_proposal, True, self.reviewer)
        mailer = BMPMailer.forReviewRequest(
            reason, self.branch_merge_proposal, self.requester)
        mailer.sendAll()

    @classmethod
    def create(cls, review_request):
        """See `IReviewRequestedEmailJobSource`."""
        metadata = cls.getMetadata(review_request)
        bmp = review_request.branch_merge_proposal
        job = BranchMergeProposalJob(bmp, cls.class_job_type, metadata)
        return cls(job)

    @staticmethod
    def getMetadata(review_request):
        return {
            'reviewer': review_request.reviewer.name,
            'requester': review_request.registrant.name,
            }

    @property
    def reviewer(self):
        """The person or team who has been asked to review."""
        return getUtility(IPersonSet).getByName(self.metadata['reviewer'])

    @property
    def requester(self):
        """The person who requested the review to be done."""
        return getUtility(IPersonSet).getByName(self.metadata['requester'])

    def getOopsVars(self):
        """See `IRunnableJob`."""
        vars =  BranchMergeProposalJobDerived.getOopsVars(self)
        vars.extend([
            ('reviewer', self.metadata['reviewer']),
            ('requester', self.metadata['requester']),
            ])
        return vars

    def getErrorRecipients(self):
        """Return a list of email-ids to notify about user errors."""
        recipients = []
        if self.requester is not None:
            recipients.append(self.requester.preferredemail)
        return recipients


class MergeProposalUpdatedEmailJob(BranchMergeProposalJobDerived):
    """Send email to the subscribers informing them of updated fields.

    When attributes of the merge proposal are edited, we inform the
    subscribers.
    """

    implements(IMergeProposalUpdatedEmailJob)

    classProvides(IMergeProposalUpdatedEmailJobSource)

    class_job_type = BranchMergeProposalJobType.MERGE_PROPOSAL_UPDATED

    def run(self):
        """See `IRunnableJob`."""
        mailer = BMPMailer.forModification(
            self.branch_merge_proposal, self.delta_text, self.editor)
        mailer.sendAll()

    @classmethod
    def create(cls, merge_proposal, delta_text, editor):
        """See `IReviewRequestedEmailJobSource`."""
        metadata = cls.getMetadata(delta_text, editor)
        job = BranchMergeProposalJob(
            merge_proposal, cls.class_job_type, metadata)
        return cls(job)

    @staticmethod
    def getMetadata(delta_text, editor):
        metadata = {'delta_text': delta_text}
        if editor is not None:
            metadata['editor'] = editor.name;
        return metadata

    @property
    def editor(self):
        """The person who updated the merge proposal."""
        editor_name = self.metadata.get('editor')
        if editor_name is None:
            return None
        else:
            return getUtility(IPersonSet).getByName(editor_name)

    @property
    def delta_text(self):
        """The changes that were made to the merge proposal."""
        return self.metadata['delta_text']

    def getOopsVars(self):
        """See `IRunnableJob`."""
        vars =  BranchMergeProposalJobDerived.getOopsVars(self)
        vars.extend([
            ('editor', self.metadata.get('editor', '(not set)')),
            ('delta_text', self.metadata['delta_text']),
            ])
        return vars

    def getErrorRecipients(self):
        """Return a list of email-ids to notify about user errors."""
        recipients = []
        if self.editor is not None:
            recipients.append(self.editor.preferredemail)
        return recipients
