# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Support for XML-RPC stuff with Twisted."""

__metaclass__ = type
__all__ = [
    'trap_fault',
    ]

from twisted.web.xmlrpc import Fault


def trap_fault(failure, *fault_classes):
    """Trap a fault, based on fault code.

    :param failure: A Twisted L{Failure}.
    :param *fault_codes: `LaunchpadFault` subclasses.
    :raise Failure: if 'failure' is not a Fault failure, or if the fault code
        does not match the given codes.
    :return: The Fault if it matches one of the codes.
    """
    failure.trap(Fault)
    fault = failure.value
    if fault.faultCode in [cls.error_code for cls in fault_classes]:
        return fault
    raise failure
