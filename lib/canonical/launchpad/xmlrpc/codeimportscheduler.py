# Copyright 2007 Canonical Ltd.  All rights reserved.

"""The code import scheduler XML-RPC API."""

__metaclass__ = type
__all__ = [
    'CodeImportSchedulerAPI',
    ]


from canonical.launchpad.interfaces import (
    ICodeImportJobSet, ICodeImportScheduler)
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
