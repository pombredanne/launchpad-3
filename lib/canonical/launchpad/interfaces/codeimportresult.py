# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interface classes for CodeImportResult, i.e. completed code import jobs."""

__metaclass__ = type
__all__ = [
    'CodeImportResultStatus', 'ICodeImportResult', 'ICodeImportResultSet']

from zope.interface import Attribute, Interface
from zope.schema import Choice, Datetime, Int, Object, Text

from canonical.launchpad import _
from canonical.launchpad.interfaces.codeimport import ICodeImport
from canonical.launchpad.interfaces.codeimportmachine import \
     ICodeImportMachine
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias
from canonical.launchpad.interfaces.person import IPerson
from canonical.lazr import (
    DBEnumeratedType, DBItem)


class CodeImportResultStatus(DBEnumeratedType):
    """Values for ICodeImportResult.status.

    How did a code import job complete? Was it successful, did it fail
    when trying to checkout or update the source tree, in the
    conversion step, or in one of the internal house-keeping steps?
    """

    SUCCESS = DBItem(100, """
        Success

        Import job completed successfully.
        """)

    FAILURE = DBItem(200, """
        Failure

        Import job failed.
        """)

    INTERNAL_FAILURE = DBItem(210, """
        Internal Failure

        An internal error occurred. This is a problem with Launchpad.
        """)

    CHECKOUT_FAILURE = DBItem(220, """
        Source Checkout Failed

        Unable to checkout from the foreign version control
        system. The import details are probably incorrect or the
        remote server is down.
        """)

    IMPORT_FAILURE = DBItem(230, """
        Bazaar Import Failed

        The initial import failed to complete. It may be a bug in
        Launchpad's conversion software or a problem with the remote
        repository.
        """)

    UPDATE_FAILURE = DBItem(240, """
        Source Update Failed

        Unable to update the foreign version control system tree. This
        is probably a problem with the remote repository.
        """)

    SYNC_FAILURE = DBItem(250, """
        Bazaar Update Failed

        An update to the existing Bazaar import failed to complete. It
        may be a bug in Launchpad's conversion software or a problem
        with the remote repository.
        """)

    RECLAIMED = DBItem(310, """
        Job reclaimed

        The job apparently crashed and was automatically marked as
        complete to allow further jobs to run for this code import.
        """)

    KILLED = DBItem(320, """
        Job killed

        A user action caused this job to be killed before it
        completed. It could have been an explicit request to kill the
        job, or the deletion of a CodeImport which had a running job.
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

    date_job_started = Datetime(
        readonly=True, required=True,
        description=_("When the job started running."))

    date_job_finished = Datetime(
        readonly=True, required=True,
        description=_("When the job stopped running."))

    job_duration = Attribute("How long did the job take to run.")


class ICodeImportResultSet(Interface):
    """The set of all CodeImportResults."""

    def new(code_import, machine, requesting_user, log_excerpt, log_file,
            status, date_job_started, date_job_finished=None):
        """Create a CodeImportResult with the given details.

        The date the job finished is assumed to be now and so is not
        passed in as a parameter.

        :param code_import: The code import for which the job was run.
        :param machine: The machine the job ran on.
        :param requesting_user: The user that requested the import, if any.
            If None, this means that the job was executed because it was
            automatically scheduled.
        :param log_excerpt: The last few lines of the log.
        :param log_file: A link to the log in the librarian.
        :param status: A status code from CodeImportResultStatus.
        :param date_job_started: The date the job started.
        :param date_job_finished: The date the job finished, defaults to now.
        """
