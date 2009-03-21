# Copyright 2006-2009 Canonical Ltd., all rights reserved.
# pylint: disable-msg=W0401

"""XMLRPC views and APIs on Launchpad objects."""

from xmlrpclib import Fault

from twisted.python.util import mergeFunctionMetadata

from canonical.launchpad.xmlrpc.application import *
from canonical.launchpad.xmlrpc.authserver import *
from canonical.launchpad.xmlrpc.branch import *
from canonical.launchpad.xmlrpc.bug import *
from canonical.launchpad.xmlrpc.codeimportscheduler import *
from canonical.launchpad.xmlrpc.mailinglist import *


def return_fault(function):
    """Catch any Faults raised by 'function' and return them instead."""

    def decorated(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Fault, fault:
            return fault

    return mergeFunctionMetadata(function, decorated)
