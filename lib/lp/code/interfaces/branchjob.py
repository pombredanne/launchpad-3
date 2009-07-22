# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""BranchJob interfaces."""


__metaclass__ = type


__all__ = [
    'IBranchJob',
    'IBranchDiffJob',
    'IBranchDiffJobSource',
    'IBranchUpgradeJob',
    'IRevisionMailJob',
    'IRevisionMailJobSource',
    'IRevisionsAddedJobSource',
    'IRosettaUploadJob',
    'IRosettaUploadJobSource',
    ]


from zope.interface import Attribute, Interface
from zope.schema import Bytes, Int, Object, Text, TextLine, Bool

from canonical.launchpad import _
from lp.code.interfaces.branch import IBranch
from lp.services.job.interfaces.job import IJob, IRunnableJob



class IBranchJob(Interface):
    """A job related to a branch."""

    branch = Object(
        title=_('Branch to use for this job.'), required=False,
        schema=IBranch)

    job = Object(schema=IJob, required=True)

    metadata = Attribute('A dict of data about the job.')

    def destroySelf():
        """Destroy this object."""


class IBranchDiffJob(Interface):
    """A job to create a static diff from a branch."""

    from_revision_spec = TextLine(title=_('The revision spec to diff from.'))

    to_revision_spec = TextLine(title=_('The revision spec to diff to.'))

    def run():
        """Acquire the static diff this job requires.

        :return: the generated StaticDiff.
        """


class IBranchDiffJobSource(Interface):

    def create(branch, from_revision_spec, to_revision_spec):
        """Construct a new object that implements IBranchDiffJob.

        :param branch: The database branch to diff.
        :param from_revision_spec: The revision spec to diff from.
        :param to_revision_spec: The revision spec to diff to.
        """


class IBranchUpgradeJob(Interface):
    """A job to upgrade branches with out-of-date formats."""

    def run():
        """Upgrade the branch to the format specified."""


class IBranchUpgradeJobSource(Interface):

    def create(branch):
        """Upgrade a branch to a more current format.

        :param branch: The database branch to upgrade.
        """


class IRevisionMailJob(IRunnableJob):
    """A Job to send email a revision change in a branch."""

    revno = Int(title=u'The revno to send mail about.')

    from_address = Bytes(title=u'The address to send mail from.')

    perform_diff = Text(title=u'Determine whether diff should be performed.')

    body = Text(title=u'The main text of the email to send.')

    subject = Text(title=u'The subject of the email to send.')


class IRevisionMailJobSource(Interface):
    """A utility to create and retrieve RevisionMailJobs."""

    def create(db_branch, revno, email_from, message, perform_diff, subject):
        """Create and return a new object that implements IRevisionMailJob."""

    def iterReady():
        """Iterate through ready IRevisionMailJobs."""


class IRevisionsAddedJob(IRunnableJob):
    """A Job to send emails about revisions added to a branch."""


class IRevisionsAddedJobSource(Interface):
    """A utility to create and retrieve RevisionMailJobs."""

    def create(branch, last_scanned_id, last_revision_id, from_address):
        """Create and return a new object that implements IRevisionMailJob."""

    def iterReady():
        """Iterate through ready IRevisionsAddedJobSource."""


class IRosettaUploadJob(Interface):
    """A job to upload translation files to Rosetta."""

    from_revision_id = TextLine(
        title=_('The revision id to compare against.'))

    force_translations_upload = Bool(
        title=_('Force an upload of translation files.'),
        description=_('Flag to override the settings in the product '
                      'series and upload all translation files.'))

    def run():
        """Extract translation files from the branch passed in by the factory
        (see IRosettaUploadJobSource) and put them into the translations
        import queue.
        """


class IRosettaUploadJobSource(Interface):

    def create(branch, from_revision_id, force_translations_upload):
        """Construct a new object that implements IRosettaUploadJob.

        :param branch: The database branch to exract files from.
        :param from_revision_id: The revision id to compare against.
        :param force_translations_upload: Flag to override the settings in the
            product series and upload all translation files.
        """

    def iterReady():
        """Iterate through ready IRosettaUploadJobs."""


    def findUnfinishedJobs(branch):
        """Find any `IRosettaUploadJob`s for `branch` that haven't run yet.

        Returns ready jobs, but also ones in any other state except
        "complete" or "failed."
        """


class IReclaimBranchSpaceJob(Interface):
    """A job to delete a branch from disk after its been deleted from the db.
    """

    branch_id = Int(
        title=_('The id of the now-deleted branch.'))

    def run():
        """Delete the branch from the filesystem."""


class IReclaimBranchSpaceJobSource(Interface):

    def create(branch_id):
        """Construct a new object that implements IReclaimBranchSpaceJob.

        :param branch_id: The id of the branch to remove from disk.
        """

    def iterReady():
        """Iterate through ready IReclaimBranchSpaceJobs."""

