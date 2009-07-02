# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Generic XML-RPC helpers."""

__metaclass__ = type
__all__ = [
    'return_fault',
    ]

from xmlrpclib import Fault

from twisted.python.util import mergeFunctionMetadata

def return_fault(function):
    """Catch any Faults raised by 'function' and return them instead."""

    def decorated(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Fault, fault:
            return fault

    return mergeFunctionMetadata(function, decorated)
