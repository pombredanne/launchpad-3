# Copyright 2007 Canonical Ltd.  All rights reserved.

"""The code import scheduler XML-RPC API."""

__metaclass__ = type
__all__ = [
    'CodeImportSchedulerAPI',
    ]


from canonical.launchpad.webapp import LaunchpadXMLRPCView
from canonical.launchpad.interfaces import ICodeImportScheduler

from zope.interface import implements


class CodeImportSchedulerAPI(LaunchpadXMLRPCView):
    """See `ICodeImportScheduler`."""

    implements(ICodeImportScheduler)

    def getJobForMachine(self, hostname):
        """See `ICodeImportScheduler`.

        Currently hard coded to return 4 until more of the code import
        machinery is implemented.
        """
        return 4
