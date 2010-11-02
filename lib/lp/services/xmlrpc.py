# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Generic code for XML-RPC in Launchpad."""

__metaclass__ = type
__all__ = [
    'LaunchpadFault',
    ]

import xmlrpclib


class LaunchpadFault(xmlrpclib.Fault):
    """Base class for a Launchpad XMLRPC fault.

    Subclasses should define a unique error_code and a msg_template,
    which will be interpolated with the given keyword arguments.
    """

    error_code = None
    msg_template = None

    def __init__(self, **kw):
        assert self.error_code is not None, (
            "Subclasses must define error_code.")
        assert self.msg_template is not None, (
            "Subclasses must define msg_template.")
        msg = self.msg_template % kw
        xmlrpclib.Fault.__init__(self, self.error_code, msg)

    def __eq__(self, other):
        if not isinstance(other, LaunchpadFault):
            return False
        return (
            self.faultCode == other.faultCode
            and self.faultString == other.faultString)

    def __ne__(self, other):
        return not (self == other)
