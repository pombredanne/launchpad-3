# Copyright 2007 Canonical Ltd.  All rights reserved.

"""The code import scheduler XML-RPC API."""

__metaclass__ = type
__all__ = [
    'CodeImportSchedulerAPI',
    ]


from canonical.launchpad.interfaces import (
    ICodeImportJobSet, ICodeImportMachineSet, ICodeImportScheduler)
from canonical.launchpad.webapp import LaunchpadXMLRPCView
from canonical.launchpad.xmlrpc.faults import NoSuchCodeImportMachine

from zope.component import getUtility
from zope.interface import implements


class CodeImportSchedulerAPI(LaunchpadXMLRPCView):
    """See `ICodeImportScheduler`."""

    implements(ICodeImportScheduler)

    def getJobForMachine(self, hostname):
        """See `ICodeImportScheduler`."""
        machine = getUtility(ICodeImportMachineSet).getByHostname(hostname)
        if machine is None:
            raise NoSuchCodeImportMachine(hostname)
        job = getUtility(ICodeImportJobSet).getJobForMachine(machine)
        if job is not None:
            return job.id
        else:
            return 0
