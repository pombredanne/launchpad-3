# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Job classes related to BranchMergeProposals are in here.

This includes both jobs for the proposals themselves, or jobs that are
creating proposals, or diffs relating to the proposals.
"""

__metaclass__ = type
__all__ = [
    'BranchMergeProposalJob',
    'CreateMergeProposalJob',
    'MergeProposalCreatedJob',
    ]

from email.Utils import parseaddr
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
from canonical.launchpad.webapp.interaction import setupInteraction
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR, IPlacelessAuthUtility, IStoreSelector, MAIN_STORE,
    MASTER_FLAVOR)
from lp.code.enums import BranchType
from lp.code.interfaces.branchmergeproposal import (
    IBranchMergeProposalJob, ICreateMergeProposalJob,
    ICreateMergeProposalJobSource, IMergeProposalCreatedJob)
from lp.code.mail.branchmergeproposal import BMPMailer
from lp.code.model.branchmergeproposal import BranchMergeProposal
from lp.code.model.diff import StaticDiff
from lp.codehosting.vfs import get_multi_server
from lp.services.job import job
from lp.services.job.model.job import Job


class BranchMergeProposalJobType(DBEnumeratedType):
    """Values that ICodeImportJob.state can take."""

    MERGE_PROPOSAL_CREATED = DBItem(0, """
        Merge proposal created

        This job generates the review diff for a BranchMergeProposal if
        needed, then sends mail to all interested parties.
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


class BranchMergeProposalJobDerived(job.Job):

    """Intermediate class for deriving from BranchMergeProposalJob."""
    delegates(IBranchMergeProposalJob)

    def __init__(self, job):
        self.context = job

    def __eq__(self, job):
        return (self.__class__ is job.__class__ and self.job == job.job)

    def __ne__(self, job):
        return not (self == job)

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
                BranchMergeProposal.source_branch == Branch.id,
                # A proposal isn't considered ready if it has no revisions,
                # or if it is hosted but pending a mirror.
                Branch.revision_count > 0,
                Or(Branch.next_mirror_time == None,
                   Branch.branch_type != BranchType.HOSTED)
                ))
        jobs.config(distinct=True)
        return (klass(job) for job in jobs)




class MergeProposalCreatedJob(BranchMergeProposalJobDerived):
    """See `IMergeProposalCreatedJob`."""

    implements(IMergeProposalCreatedJob)

    class_job_type = BranchMergeProposalJobType.MERGE_PROPOSAL_CREATED

    @classmethod
    def create(klass, bmp):
        """See `IMergeProposalCreationJob`."""
        job = BranchMergeProposalJob(
            bmp, klass.class_job_type, {})
        return klass(job)

    def run(self):
        """See `IMergeProposalCreatedJob`."""
        if self.branch_merge_proposal.review_diff is None:
            self.branch_merge_proposal.review_diff = self._makeReviewDiff()
            transaction.commit()
        mailer = BMPMailer.forCreation(
            self.branch_merge_proposal, self.branch_merge_proposal.registrant)
        mailer.sendAll()
        return self.branch_merge_proposal.review_diff

    def _makeReviewDiff(self):
        """Return a StaticDiff to be used as a review diff."""
        cleanups = []
        def get_branch(branch):
            bzr_branch = branch.getBzrBranch()
            bzr_branch.lock_read()
            cleanups.append(bzr_branch.unlock)
            return bzr_branch
        try:
            bzr_source = get_branch(self.branch_merge_proposal.source_branch)
            bzr_target = get_branch(self.branch_merge_proposal.target_branch)
            lca, source_revision = self._findRevisions(
                bzr_source, bzr_target)
            diff = StaticDiff.acquire(
                lca, source_revision, bzr_source.repository)
        finally:
            for cleanup in reversed(cleanups):
                cleanup()
        return diff

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


class CreateMergeProposalJob(job.Job):
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
        message = self.getMessage()
        # Since the message was checked as signed before it was saved in the
        # Librarian, just create the principle from the sender and setup the
        # interaction.
        name, email_addr = parseaddr(message['From'])
        authutil = getUtility(IPlacelessAuthUtility)
        principal = authutil.getPrincipalByLogin(email_addr)
        if principal is None:
            raise AssertionError('No principal found for %s' % email_addr)
        setupInteraction(principal, email_addr)

        server = get_multi_server(write_hosted=True)
        server.setUp()
        try:
            return CodeHandler().processMergeProposal(message)
        finally:
            server.tearDown()

    def getOopsRecipients(self):
        message = self.getMessage()
        return [message['From']]

    def getOperationDescription(self):
        message = self.getMessage()
        return ('creating a merge proposal from message with subject %s' %
                message['Subject'])
