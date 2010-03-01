# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The code import scheduler XML-RPC API."""

__metaclass__ = type
__all__ = [
    'CodeImportSchedulerAPI',
    ]

from zope.component import getUtility
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces import ILibraryFileAliasSet
from canonical.launchpad.webapp import canonical_url, LaunchpadXMLRPCView
from canonical.launchpad.xmlrpc.faults import NoSuchCodeImportJob
from canonical.launchpad.xmlrpc.helpers import return_fault

from lp.code.interfaces.codeimportjob import (
    ICodeImportJobSet, ICodeImportJobWorkflow)
from lp.code.interfaces.codeimportscheduler import ICodeImportScheduler
from lp.codehosting.codeimport.worker import CodeImportSourceDetails


class CodeImportSchedulerAPI(LaunchpadXMLRPCView):
    """See `ICodeImportScheduler`."""

    implements(ICodeImportScheduler)

    def getJobForMachine(self, hostname, worker_limit):
        """See `ICodeImportScheduler`."""
        job = getUtility(ICodeImportJobSet).getJobForMachine(
            hostname, worker_limit)
        if job is not None:
            return job.id
        else:
            return 0

    def _getJob(self, job_id):
        job_set = removeSecurityProxy(getUtility(ICodeImportJobSet))
        job = removeSecurityProxy(job_set.getById(job_id))
        if job is None:
            raise NoSuchCodeImportJob()
        return job

    @return_fault
    def getImportDataForJobID(self, job_id):
        """See `ICodeImportScheduler`."""
        job = self._getJob(job_id)
        arguments = CodeImportSourceDetails.fromCodeImport(
            job.code_import).asArguments()
        branch = job.code_import.branch
        branch_url = canonical_url(branch)
        log_file_name = '%s.log' % branch.unique_name[1:].replace('/', '-')
        return (arguments, branch_url, log_file_name)

    @return_fault
    def updateHeartbeat(self, job_id, log_tail):
        """See `ICodeImportScheduler`."""
        job = self._getJob(job_id)
        workflow = removeSecurityProxy(getUtility(ICodeImportJobWorkflow))
        workflow.updateHeartbeat(job, log_tail)
        return 0

    @return_fault
    def finishJobID(self, job_id, status, log_file_alias_id):
        """See `ICodeImportScheduler`."""
        job = self._getJob(job_id)
        workflow = removeSecurityProxy(getUtility(ICodeImportJobWorkflow))
        if log_file_alias_id:
            library_file_alias_set = getUtility(ILibraryFileAliasSet)
            log_file_alias = library_file_alias_set[log_file_alias_id]
        else:
            log_file_alias = None
        workflow.finishJob(job, status, log_file_alias)
