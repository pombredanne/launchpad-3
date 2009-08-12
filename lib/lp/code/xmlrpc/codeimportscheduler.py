# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The code import scheduler XML-RPC API."""

__metaclass__ = type
__all__ = [
    'CodeImportSchedulerAPI',
    ]


from lp.code.interfaces.codeimportjob import ICodeImportJobSet
from lp.code.interfaces.codeimportscheduler import ICodeImportScheduler
from canonical.launchpad.webapp import LaunchpadXMLRPCView

from zope.component import getUtility
from zope.interface import implements


class CodeImportSchedulerAPI(LaunchpadXMLRPCView):
    """See `ICodeImportScheduler`."""

    implements(ICodeImportScheduler)

    def getJobForMachine(self, hostname):
        """See `ICodeImportScheduler`."""
        job = getUtility(ICodeImportJobSet).getJobForMachine(hostname)
        if job is not None:
            return job.id
        else:
            return 0
