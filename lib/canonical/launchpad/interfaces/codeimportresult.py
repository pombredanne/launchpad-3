# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Interface classes for CodeImportResults, i.e. completed code import jobs."""

__metaclass__ = type
__all__ = [
    'CodeImportResultStatus', 'ICodeImportResult', 'ICodeImportResultSet']

from canonical.launchpad import _
from canonical.launchpad.interfaces.codeimport import ICodeImport
from canonical.launchpad.interfaces.codeimportmachine import ICodeImportMachine
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias
from canonical.launchpad.interfaces.person import IPerson
from canonical.lazr import (
    DBEnumeratedType, DBItem)

from zope.interface import Interface
from zope.schema import Choice, Datetime, Int, Object, Text


class CodeImportResultStatus(DBEnumeratedType):
    """Values for ICodeImportResult.status.

    How did a code import job complete? Was it successful, did it fail
    when trying to checkout or update the source tree, in the
    conversion step, or in one of the internal house-keeping steps?
    """

    SUCCESS = DBItem(100, """Success

    Import job completed successfully.
    """)

    FAILURE = DBItem(200, """Failure

    Import job failed.
    """)

    INTERNAL_FAILURE = DBItem(210, """Internal Failure

    An internal error occurred. This is a problem with Launchpad.
    """)

    CHECKOUT_FAILURE = DBItem(220, """Source Checkout Failed

    Unable to checkout from the foreign version control system. The
    import details are probably incorrect or the remote server is down.
    """)

    IMPORT_FAILURE = DBItem(230, """Bazaar Import Failed

    The initial import failed to complete. It may be a bug in
    Launchpad's conversion software or a problem with the remote
    repository.
    """)

    UPDATE_FAILURE = DBItem(240, """Source Update Failed

    Unable to update the foreign version control system tree. This is
    probably a problem with the remote repository.
    """)

    SYNC_FAILURE = DBItem(250, """Bazaar Update Failed

    An update to the existing Bazaar import failed to complete. It may
    be a bug in Launchpad's conversion software or a problem with the
    remote repository.
    """)

    RECLAIMED = DBItem(310, """Job reclaimed

    The job apparently crashed and was automatically marked as complete to
    allow further jobs to run for this code import.
    """)

    KILLED = DBItem(320, """Job killed

    A user action caused this job to be killed before it completed. It could
    have been an explicit request to kill the job, or the deletion of a
    CodeImport which had a running job.
    """)


class ICodeImportResult(Interface):
    """A completed code import job."""

    id = Int(readonly=True, required=True)
    date_created = Datetime(readonly=True, required=True)

    code_import = Object(
        schema=ICodeImport, readonly=True, required=True,
        description=_("The code import for which the job was run."))

    machine = Object(
        schema=ICodeImportMachine, readonly=True, required=True,
        description=_("The machine the job ran on."))

    requesting_user = Object(
        schema=IPerson, readonly=True, required=False,
        description=_("The user that requested the import, if any."))

    log_excerpt = Text(
        readonly=True, required=False,
        description=_("The last few lines of the partial log, in case it "
                      "is set."))

    log_file = Object(
        schema=ILibraryFileAlias, readonly=True, required=False,
        description=_("A partial log of the job for users to see. It is "
                      "normally only recorded if the job failed in a step "
                      "that interacts with the remote repository. If a job "
                      "was successful, or failed in a houskeeping step, the "
                      "log file would not contain information useful to the "
                      "user."))

    status = Choice(
        vocabulary=CodeImportResultStatus, readonly=True, required=True,
        description=_("How the job ended. Success, some kind of failure, or "
                      "some kind of interruption before completion."))

    date_started = Datetime(
        readonly=True, required=True,
        description=_("When the job started to run (date_created is when it "
                      "finished)."))


class ICodeImportResultSet(Interface):
    """The set of all CodeImportResults."""
