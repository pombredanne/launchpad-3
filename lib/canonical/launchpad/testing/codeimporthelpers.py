# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Helpers for Code Import page tests."""

__metaclass__ = type
__all__ = [
    'get_import_for_branch_name',
    'make_finished_import',
    'make_running_import',
    ]


from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.database.codeimportjob import CodeImportJobWorkflow
from canonical.launchpad.ftests import sync
from canonical.launchpad.interfaces import (
    CodeImportJobState, CodeImportResultStatus, CodeImportReviewStatus,
    IBranchSet
    )
from canonical.launchpad.testing import LaunchpadObjectFactory


def get_import_for_branch_name(branch_unique_name):
    """Return the code import associated with the branch."""
    branch = getUtility(IBranchSet).getByUniqueName(branch_unique_name)
    if branch is not None:
        return branch.code_import
    else:
        return None


def make_running_import(code_import=None, machine=None, date_started=None,
                        factory=None):
    """Return a code import with a running job.

    :param code_import: The code import to create the job for.  If None, an
        anonymous CodeImport is created.
    :param machine: The `CodeImportMachine` to associate with the running
        job.  If None, an anonymous CodeImportMachine is created.
    :param date_started: If specified this overrides the UTC_NOW timestamp
        of the newly started job.
    :param factory: The LaunchpadObjectFactory to use for the creation of
        the objects.  If None, one is created.
    """
    if factory is None:
        factory = LaunchpadObjectFactory()
    if code_import is None:
        code_import = factory.makeCodeImport()
    if machine is None:
        machine = factory.makeCodeImportMachine(set_online=True)
    # The code import must be in a reviewed state.
    if code_import.review_status != CodeImportReviewStatus.REVIEWED:
        code_import.approve({}, code_import.registrant)

    CodeImportJobWorkflow().startJob(code_import.import_job, machine)

    assert code_import.import_job.state == CodeImportJobState.RUNNING

    if date_started is not None:
        # Override the job date_started.
        naked_job = removeSecurityProxy(code_import.import_job)
        naked_job.date_started = date_started

    return code_import


def make_finished_import(code_import=None, status=None, date_finished=None,
                         factory=None):
    """Return a code import with a new finished job.

    :param code_import: The code import to create the job for.  If None, an
        anonymous CodeImport is created.
    :param status: The result status.  If not specified it is set to
        SUCCESSFUL.
    :param date_finished: If specified this overrides the date_last_successful
        attribute of the code_import if the state is SUCCESSFUL.
    :param factory: The LaunchpadObjectFactory to use for the creation of
        the objects.  If None, one is created.
    """
    if factory is None:
        factory = LaunchpadObjectFactory()
    if code_import is None:
        code_import = factory.makeCodeImport()
    if status is None:
        status = CodeImportResultStatus.SUCCESS
    # The code import must be in a reviewed state.
    if code_import.review_status != CodeImportReviewStatus.REVIEWED:
        code_import.approve({}, code_import.registrant)

    # If the job isn't running, make it run.
    if code_import.import_job.state != CodeImportJobState.RUNNING:
        machine = factory.makeCodeImportMachine(set_online=True)
        CodeImportJobWorkflow().startJob(code_import.import_job, machine)
        sync(code_import.import_job)

    CodeImportJobWorkflow().finishJob(code_import.import_job, status, None)

    if date_finished is not None and status == CodeImportResultStatus.SUCCESS:
        # Override the code import date last successful.
        naked_import = removeSecurityProxy(code_import)
        naked_import.date_last_successful = date_finished

    return code_import
