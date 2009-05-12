# Copyright 2008, 2009 Canonical Ltd.  All rights reserved.
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
from canonical.launchpad.interfaces.job import IJob



class IBranchJob(Interface):
    """A job related to a branch."""

    branch = Object(
        title=_('Branch to use for this diff'), required=True,
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

    to_format = TextLine(title=_('The format to upgrade the branch to.'))

    def run():
        """Upgrade the branch to the format specified."""


class IBranchUpgradeJobSource(Interface):

    def create(branch, to_format):
        """Upgrade a branch to a more current format.

        :param branch: The database branch to upgrade.
        :param to_format: The format to upgrade the branch to.
        """


class IRevisionMailJob(Interface):
    """A Job to send email a revision change in a branch."""

    revno = Int(title=u'The revno to send mail about.')

    from_address = Bytes(title=u'The address to send mail from.')

    perform_diff = Text(title=u'Determine whether diff should be performed.')

    body = Text(title=u'The main text of the email to send.')

    subject = Text(title=u'The subject of the email to send.')

    def run():
        """Send the mail as specified by this job."""


class IRevisionMailJobSource(Interface):
    """A utility to create and retrieve RevisionMailJobs."""

    def create(db_branch, revno, email_from, message, perform_diff, subject):
        """Create and return a new object that implements IRevisionMailJob."""

    def iterReady():
        """Iterate through ready IRevisionMailJobs."""


class IRevisionsAddedJob(Interface):
    """A Job to send emails about revisions added to a branch."""

    def run():
        """Send the mails as specified by this job."""


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

