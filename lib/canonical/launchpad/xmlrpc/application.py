# Copyright 2006 Canonical Ltd., all rights reserved.
"""XMLRPC API to the application roots."""

__metaclass__ = type
__all__ = ['ISelfTest', 'SelfTest']

from zope.interface import Interface, implements
import xmlrpclib

from canonical.launchpad.webapp import LaunchpadXMLRPCView


class ISelfTest(Interface):
    """XMLRPC external interface for testing the XMLRPC external interface."""

    def make_fault():
        """Returns an xmlrpc fault."""

    def concatenate(string1, string2):
        """Return the concatenation of the two given strings."""


class SelfTest(LaunchpadXMLRPCView):

    implements(ISelfTest)

    def make_fault(self):
        """Returns an xmlrpc fault."""
        return xmlrpclib.Fault(666, "Yoghurt and spanners.")

    def concatenate(self, string1, string2):
        """Return the concatenation of the two given strings."""
        return u'%s %s' % (string1, string2)

