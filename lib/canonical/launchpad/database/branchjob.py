# Copyright 2004-2005, 2009 Canonical Ltd.  All rights reserved.
__all__ = [
    'BranchJob',
    'RevisionsAddedJob',
    'RevisionMailJob',
    'RosettaUploadJob',
]

from StringIO import StringIO

from bzrlib.log import log_formatter, show_log
from bzrlib.revision import NULL_REVISION
from bzrlib.revisionspec import RevisionInfo, RevisionSpec
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
from lazr.enum import DBEnumeratedType, DBItem
from lazr.delegates import delegates
import simplejson
from sqlobject import ForeignKey, StringCol
from storm.expr import And
import transaction
from zope.component import getUtility
from zope.interface import classProvides, implements

from canonical.codehosting import iter_list_chunks
from canonical.launchpad.database.branch import Branch
from canonical.launchpad.database.diff import StaticDiff
from canonical.launchpad.database.job import Job
from canonical.launchpad.database.productseries import ProductSeries
from canonical.launchpad.database.translationbranchapprover import (
    TranslationBranchApprover)
from canonical.launchpad.interfaces import (
    BranchSubscriptionDiffSize, BranchSubscriptionNotificationLevel)
from canonical.launchpad.interfaces.branchjob import (
    IBranchDiffJob, IBranchDiffJobSource, IBranchJob, IRevisionMailJob,
    IRevisionMailJobSource, IRosettaUploadJob, IRosettaUploadJobSource)
from canonical.launchpad.interfaces.translations import (
    TranslationsBranchImportMode)
from canonical.launchpad.interfaces.translationimportqueue import (
    ITranslationImportQueue)
from canonical.launchpad.mailout.branch import BranchMailer
from canonical.launchpad.translationformat.translation_import import (
    TranslationImporter)
from canonical.launchpad.webapp.interfaces import (
        IStoreSelector, MAIN_STORE, MASTER_FLAVOR)

# Use at most the first 100 characters of the commit message.
SUBJECT_COMMIT_MESSAGE_LENGTH = 100

class BranchJobType(DBEnumeratedType):
    """Values that ICodeImportJob.state can take."""

    STATIC_DIFF = DBItem(0, """
        Static Diff

        This job runs against a branch to produce a diff that cannot change.
        """)

    REVISION_MAIL = DBItem(1, """
        Revision Mail

        This job runs against a branch to send emails about revisions.
        """)

    REVISIONS_ADDED_MAIL = DBItem(2, """
        Revisions Added Mail

        This job runs against a branch to send emails about added revisions.
        """)

    ROSETTA_UPLOAD = DBItem(3, """
        Rosetta Upload

        This job runs against a branch to upload translation files to rosetta.
        """)


class BranchJob(SQLBase):
    """Base class for jobs related to branches."""

    implements(IBranchJob)

    _table = 'BranchJob'

    job = ForeignKey(foreignKey='Job', notNull=True)

    branch = ForeignKey(foreignKey='Branch', notNull=True)

    job_type = EnumCol(enum=BranchJobType, notNull=True)

    _json_data = StringCol(dbName='json_data')

    @property
    def metadata(self):
        return simplejson.loads(self._json_data)

    def __init__(self, branch, job_type, metadata):
        """Constructor.

        :param branch: The database branch this job relates to.
        :param job_type: The BranchJobType of this job.
        :param metadata: The type-specific variables, as a JSON-compatible
            dict.
        """
        json_data = simplejson.dumps(metadata)
        SQLBase.__init__(
            self, job=Job(), branch=branch, job_type=job_type,
            _json_data=json_data)

    def destroySelf(self):
        """See `IBranchJob`."""
        SQLBase.destroySelf(self)
        self.job.destroySelf()


class BranchJobDerived(object):

    delegates(IBranchJob)

    def __init__(self, branch_job):
        self.context = branch_job

    # XXX: henninge 2009-02-20 bug=331919: These two standard operators
    # should be implemented by delegates().
    def __eq__(self, other):
        return (self.__class__ == other.__class__ and
                self.context == other.context)

    def __ne__(self, other):
        return not (self == other)

    @classmethod
    def iterReady(klass):
        """See `IRevisionMailJobSource`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
        jobs = store.find(
            (BranchJob),
            And(BranchJob.job_type == klass.class_job_type,
                BranchJob.job == Job.id,
                Job.id.is_in(Job.ready_jobs)))
        return (klass(job) for job in jobs)


class BranchDiffJob(BranchJobDerived):
    """A Job that calculates the a diff related to a Branch."""

    implements(IBranchDiffJob)

    classProvides(IBranchDiffJobSource)
    @classmethod
    def create(klass, branch, from_revision_spec, to_revision_spec):
        """See `IBranchDiffJobSource`."""
        metadata = klass.getMetadata(from_revision_spec, to_revision_spec)
        branch_job = BranchJob(branch, BranchJobType.STATIC_DIFF, metadata)
        return klass(branch_job)

    @staticmethod
    def getMetadata(from_revision_spec, to_revision_spec):
        return {
            'from_revision_spec': from_revision_spec,
            'to_revision_spec': to_revision_spec,
        }

    @property
    def from_revision_spec(self):
        return self.metadata['from_revision_spec']

    @property
    def to_revision_spec(self):
        return self.metadata['to_revision_spec']

    def _get_revision_id(self, bzr_branch, spec_string):
        spec = RevisionSpec.from_string(spec_string)
        return spec.as_revision_id(bzr_branch)

    def run(self):
        """See IBranchDiffJob."""
        bzr_branch = self.branch.getBzrBranch()
        from_revision_id = self._get_revision_id(
            bzr_branch, self.from_revision_spec)
        to_revision_id = self._get_revision_id(
            bzr_branch, self.to_revision_spec)
        static_diff = StaticDiff.acquire(
            from_revision_id, to_revision_id, bzr_branch.repository)
        return static_diff


class RevisionMailJob(BranchDiffJob):
    """A Job that calculates the a diff related to a Branch."""

    implements(IRevisionMailJob)

    classProvides(IRevisionMailJobSource)

    class_job_type = BranchJobType.REVISION_MAIL

    @classmethod
    def create(
        klass, branch, revno, from_address, body, perform_diff, subject):
        """See `IRevisionMailJobSource`."""
        metadata = {
            'revno': revno,
            'from_address': from_address,
            'body': body,
            'perform_diff': perform_diff,
            'subject': subject,
        }
        if isinstance(revno, int) and revno > 0:
            from_revision_spec = str(revno - 1)
            to_revision_spec = str(revno)
        else:
            from_revision_spec = None
            to_revision_spec = None
        metadata.update(BranchDiffJob.getMetadata(from_revision_spec,
                        to_revision_spec))
        branch_job = BranchJob(branch, BranchJobType.REVISION_MAIL, metadata)
        return klass(branch_job)

    @property
    def revno(self):
        revno = self.metadata['revno']
        if isinstance(revno, int):
            revno = long(revno)
        return revno

    @property
    def from_address(self):
        return str(self.metadata['from_address'])

    @property
    def perform_diff(self):
        return self.metadata['perform_diff']

    @property
    def body(self):
        return self.metadata['body']

    @property
    def subject(self):
        return self.metadata['subject']

    def getMailer(self):
        """Return a BranchMailer for this job."""
        if self.perform_diff and self.to_revision_spec is not None:
            diff = BranchDiffJob.run(self)
            transaction.commit()
            diff_text = diff.diff.text
        else:
            diff_text = None
        return BranchMailer.forRevision(
            self.branch, self.revno, self.from_address, self.body,
            diff_text, self.subject)

    def run(self):
        """See `IRevisionMailJob`."""
        self.getMailer().sendAll()


class RevisionsAddedJob(BranchJobDerived):
    """A job for sending emails about added revisions."""

    class_job_type = BranchJobType.REVISIONS_ADDED_MAIL

    @classmethod
    def create(klass, branch, last_scanned_id, last_revision_id,
               from_address):
        metadata = {'last_scanned_id': last_scanned_id,
                    'last_revision_id': last_revision_id,
                    'from_address': from_address}
        branch_job = BranchJob(branch, klass.class_job_type, metadata)
        return RevisionsAddedJob(branch_job)

    def __init__(self, context):
        super(RevisionsAddedJob, self).__init__(context)
        self._bzr_branch = None

    @property
    def bzr_branch(self):
        if self._bzr_branch is None:
            self._bzr_branch = self.branch.getBzrBranch()
        return self._bzr_branch

    @property
    def last_scanned_id(self):
        return self.metadata['last_scanned_id']

    @property
    def last_revision_id(self):
        return self.metadata['last_revision_id']

    @property
    def from_address(self):
        return self.metadata['from_address']

    def iterAddedMainline(self):
        """Iterate through revisions added to the mainline."""
        graph = self.bzr_branch.repository.get_graph()
        added_revisions = graph.find_difference(
            self.last_scanned_id, self.last_revision_id)[1]
        branch_revisions = self.branch.getMainlineBranchRevisions(
            added_revisions)
        for branch_revisions_chunk in iter_list_chunks(
            list(branch_revisions), 1000):
            revision_ids = [branch_revision.revision.revision_id
                for branch_revision in branch_revisions_chunk]
            revisions = self.bzr_branch.repository.get_revisions(revision_ids)
            for revision, branch_revision in zip(
                revisions, branch_revisions_chunk):
                if (self.bzr_branch.get_rev_id(branch_revision.sequence) !=
                    branch_revision.revision.revision_id):
                    continue
                yield revision, branch_revision.sequence

    def generateDiffs(self):
        """Determine whether to generate diffs."""
        for subscription in self.branch.subscriptions:
            if (subscription.max_diff_lines !=
                BranchSubscriptionDiffSize.NODIFF):
                return True
        else:
            return False

    def run(self):
        """Send all the emails about all the added revisions."""
        diff_levels = (BranchSubscriptionNotificationLevel.DIFFSONLY,
                       BranchSubscriptionNotificationLevel.FULL)
        subscriptions = self.branch.getSubscriptionsByLevel(diff_levels)
        if not subscriptions:
            return

        self.bzr_branch.lock_read()
        try:
            for revision, revno in self.iterAddedMainline():
                assert revno is not None
                mailer = self.getMailerForRevision(
                    revision, revno, self.generateDiffs())
                mailer.sendAll()
        finally:
            self.bzr_branch.unlock()

    def getMailerForRevision(self, revision, revno, generate_diff):
        """Return a BranchMailer for a revision.

        :param revision: A bzr revision.
        :param revno: The revno of the revision in this branch.
        :param generate_diffs: If true, generate a diff for the revision.
        """
        message = self.getRevisionMessage(revision.revision_id, revno)
        # Use the first (non blank) line of the commit message
        # as part of the subject, limiting it to 100 characters
        # if it is longer.
        message_lines = [
            line.strip() for line in revision.message.split('\n')
            if len(line.strip()) > 0]
        if len(message_lines) == 0:
            first_line = 'no commit message given'
        else:
            first_line = message_lines[0]
            if len(first_line) > SUBJECT_COMMIT_MESSAGE_LENGTH:
                offset = SUBJECT_COMMIT_MESSAGE_LENGTH - 3
                first_line = first_line[:offset] + '...'
        subject = '[Branch %s] Rev %s: %s' % (
            self.branch.unique_name, revno, first_line)
        if generate_diff:
            if len(revision.parent_ids) > 0:
                parent_id = revision.parent_ids[0]
            else:
                parent_id = NULL_REVISION
            diff = StaticDiff.acquire(parent_id, revision.revision_id,
                                      self.bzr_branch.repository)
            transaction.commit()
            diff_text = diff.diff.text
        else:
            diff_text = None
        return BranchMailer.forRevision(
            self.branch, revno, self.from_address, message, diff_text,
            subject)

    def getRevisionMessage(self, revision_id, revno):
        """Return the log message for a revision.

        :param revision_id: The revision-id of the revision.
        :param revno: The revno of the revision in the branch.
        :return: The log message entered for this revision.
        """
        info = RevisionInfo(self.bzr_branch, revno, revision_id)
        outf = StringIO()
        lf = log_formatter('long', to_file=outf)
        show_log(self.bzr_branch,
                 lf,
                 start_revision=info,
                 end_revision=info,
                 verbose=True)
        return outf.getvalue()


class RosettaUploadJob(BranchJobDerived):
    """A Job that uploads translation files to Rosetta."""

    implements(IRosettaUploadJob)

    classProvides(IRosettaUploadJobSource)

    class_job_type = BranchJobType.ROSETTA_UPLOAD

    def __init__(self, branch_job):
        super(RosettaUploadJob, self).__init__(branch_job)

        self.pot_file_names = []
        self.pot_changed_files = []
        self.po_file_names = []
        self.po_changed_files = []

    @staticmethod
    def getMetadata(from_revision_id):
        return {
            'from_revision_id': from_revision_id,
        }

    @property
    def from_revision_id(self):
        return self.metadata['from_revision_id']

    @classmethod
    def create(klass, branch, from_revision_id):
        """See `IRosettaUploadJobSource`."""
        if branch is None:
            return None
        store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
        productseries = store.find(
            (ProductSeries),
            ProductSeries.branch == branch,
            ProductSeries.translations_autoimport_mode !=
               TranslationsBranchImportMode.NO_IMPORT).any()
        if productseries is not None:
            metadata = klass.getMetadata(from_revision_id)
            branch_job = BranchJob(
                branch, BranchJobType.ROSETTA_UPLOAD, metadata)
            return klass(branch_job)
        else:
            return None

    def _iter_lists(self, productseries=None):
        """Produce the file lists and the uploader person
        as needed for the given productseries or all if productseries is
        None.
        """
        if productseries == None:
            yield (self.pot_file_names, self.pot_changed_files)
            yield (self.po_file_names, self.po_changed_files)
        else:
            if productseries.translations_autoimport_mode in (
                TranslationsBranchImportMode.IMPORT_TEMPLATES,):
                yield (self.pot_file_names,
                       self.pot_changed_files,
                       self._uploader_person_pot(productseries))
            # Handling for other modes will go here.

    @property
    def file_names(self):
        """A contatenation of all filenames."""
        return self.pot_file_names + self.po_file_names

    def _init_translation_file_lists(self):
        """Initialize the member variables that hold the information about
        the relevant files.

        The information is collected from the branch tree and stored in the
        following member variables:
        * file_names is a dictionary of two lists ('pot', 'po') of file names
          that are POT or PO files respectively. This includes all files,
          changed or unchanged.
        * changed_files is a dictionary of two lists ('pot', 'po') of tuples
          of (file_name, file_content) of all changed files that are POT or
          PO files respectively.
        """

        bzrbranch = self.branch.getBzrBranch()
        from_tree = bzrbranch.repository.revision_tree(
            self.from_revision_id)
        to_tree = bzrbranch.repository.revision_tree(
            self.branch.last_scanned_id)

        importer = TranslationImporter()

        to_tree.lock_read()
        try:
            for dir, files in to_tree.walkdirs():
                for afile in files:
                    file_path, file_name, file_type = afile[:3]
                    if file_type != 'file':
                        continue
                    if importer.isTemplateName(file_name):
                        append_to = self.pot_file_names
                    elif importer.isTranslationName(file_name):
                        append_to = self.po_file_names
                    else:
                        continue
                    append_to.append(file_path)
            from_tree.lock_read()
            try:
                for file_names, changed_files in self._iter_lists():
                    for changed_file in to_tree.iter_changes(
                            from_tree, specific_files=file_names):
                        file_id, (from_path, to_path) = changed_file[:2]
                        changed_files.append((
                            to_path, to_tree.get_file_text(file_id)))
            finally:
                from_tree.unlock()
        finally:
            to_tree.unlock()

    def _uploader_person_pot(self, series):
        """Determine which person is the uploader for a pot file."""
        # Default uploader is the driver or owner of the series.
        uploader = series.driver
        if uploader is None:
            uploader = series.owner
        return uploader

    def _uploader_person_po(self, series):
        """Determine which person is the uploader for a po file."""
        # For po files, try to determine the author of the latest push.
        uploader = self.branch.getTipRevision().revision_author.person
        if uploader is None:
            uploader = self._uploader_person_pot(series)
        return uploader

    def run(self):
        """See `IRosettaUploadJob`."""
        # This is not called upon job creation because the branch would
        # neither have been mirrored nor scanned then.
        self._init_translation_file_lists()
        # Get the product series that are connected to this branch and
        # that want to upload translations.
        store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
        productseries = store.find(
            (ProductSeries),
            ProductSeries.branch == self.branch,
            ProductSeries.translations_autoimport_mode !=
               TranslationsBranchImportMode.NO_IMPORT)
        translation_import_queue = getUtility(ITranslationImportQueue)
        for series in productseries:
            approver = TranslationBranchApprover(self.file_names,
                                                 productseries=series)
            for iter_info in self._iter_lists(series):
                file_names, changed_files, uploader = iter_info
                for upload_file_name, upload_file_content in changed_files:
                    if len(upload_file_content) == 0:
                        continue # Skip empty files
                    entry = translation_import_queue.addOrUpdateEntry(
                        upload_file_name, upload_file_content,
                        True, uploader, productseries=series)
                    approver.approve(entry)

    @staticmethod
    def iterReady():
        """See `IRosettaUploadJobSource`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
        jobs = store.using(BranchJob, Job, Branch).find(
            (BranchJob),
            And(BranchJob.job_type == BranchJobType.ROSETTA_UPLOAD,
                BranchJob.job == Job.id,
                BranchJob.branch == Branch.id,
                Branch.last_mirrored_id == Branch.last_scanned_id,
                Job.id.is_in(Job.ready_jobs)))
        return (RosettaUploadJob(job) for job in jobs)

