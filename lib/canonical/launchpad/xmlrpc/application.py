# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""XML-RPC API to the application roots."""

__metaclass__ = type

__all__ = [
    'IRosettaSelfTest',
    'ISelfTest',
    'PrivateApplication',
    'RosettaSelfTest',
    'SelfTest',
    ]

import xmlrpclib

from zope.component import getUtility
from zope.interface import (
    implements,
    Interface,
    )

from canonical.launchpad.interfaces.launchpad import (
    IAuthServerApplication,
    IPrivateApplication,
    IPrivateMaloneApplication,
    )
from canonical.launchpad.webapp import LaunchpadXMLRPCView
from canonical.launchpad.webapp.interfaces import ILaunchBag
from lp.code.interfaces.codehosting import ICodehostingApplication
from lp.code.interfaces.codeimportscheduler import (
    ICodeImportSchedulerApplication,
    )
from lp.registry.interfaces.mailinglist import IMailingListApplication
from lp.registry.interfaces.person import ISoftwareCenterAgentApplication
from lp.services.features.xmlrpc import IFeatureFlagApplication


# NOTE: If you add a traversal here, you should update
# the regular expression in utilities/page-performance-report.ini
class PrivateApplication:
    implements(IPrivateApplication)

    @property
    def mailinglists(self):
        """See `IPrivateApplication`."""
        return getUtility(IMailingListApplication)

    @property
    def authserver(self):
        """See `IPrivateApplication`."""
        return getUtility(IAuthServerApplication)

    @property
    def codehosting(self):
        """See `IPrivateApplication`."""
        return getUtility(ICodehostingApplication)

    @property
    def codeimportscheduler(self):
        """See `IPrivateApplication`."""
        return getUtility(ICodeImportSchedulerApplication)

    @property
    def bugs(self):
        """See `IPrivateApplication`."""
        return getUtility(IPrivateMaloneApplication)

    @property
    def softwarecenteragent(self):
        """See `IPrivateApplication`."""
        return getUtility(ISoftwareCenterAgentApplication)

    @property
    def featureflags(self):
        """See `IPrivateApplication`."""
        return getUtility(IFeatureFlagApplication)


class ISelfTest(Interface):
    """XMLRPC external interface for testing the XMLRPC external interface."""

    def make_fault():
        """Returns an xmlrpc fault."""

    def concatenate(string1, string2):
        """Return the concatenation of the two given strings."""

    def hello():
        """Return a greeting to the one calling the method."""

    def raise_exception():
        """Raise an exception."""


class SelfTest(LaunchpadXMLRPCView):

    implements(ISelfTest)

    def make_fault(self):
        """Returns an xmlrpc fault."""
        return xmlrpclib.Fault(666, "Yoghurt and spanners.")

    def concatenate(self, string1, string2):
        """Return the concatenation of the two given strings."""
        return u'%s %s' % (string1, string2)

    def hello(self):
        """Return a greeting to the logged in user."""
        caller = getUtility(ILaunchBag).user
        if caller is not None:
            caller_name = caller.displayname
        else:
            caller_name = "Anonymous"
        return "Hello %s." % caller_name

    def raise_exception(self):
        raise RuntimeError("selftest exception")


class IRosettaSelfTest(Interface):

    def run_test():
        return "OK"


class RosettaSelfTest(LaunchpadXMLRPCView):

    implements(IRosettaSelfTest)

    def run_test(self):
        return "OK"

