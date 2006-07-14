# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Launchpad XMLRPC faults."""

__metaclass__ = type
__all__ = [
    'NoSuchProduct',
    'NoSuchPerson',
    'NoSuchBranch',
    'NoSuchBug',
    'BranchAlreadyRegistered',
    ]

import xmlrpclib


class LaunchpadFault(xmlrpclib.Fault):
    """Base class for a Launchpad XMLRPC fault.

    Subclasses should define a unique error_code and a msg_template,
    which will be interpolated with the given keyword arguments.
    """

    def __new__(cls, *args, **kw):
        """Workaround for bug 52033: all faults must be plain Fault objects."""
        obj = super(LaunchpadFault, cls).__new__(cls, *args, **kw)
        obj.__init__(*args, **kw)
        return xmlrpclib.Fault(obj.faultCode, obj.faultString)

    error_code = None
    msg_template = None

    def __init__(self, **kw):
        assert self.error_code is not None, (
            "Subclasses must define error_code.")
        assert self.msg_template is not None, (
            "Subclasses must define msg_template.")
        msg = self.msg_template % kw
        xmlrpclib.Fault.__init__(self, self.error_code, msg)


class NoSuchProduct(LaunchpadFault):
    """There's no such product registered in Launchpad."""

    error_code = 10
    msg_template = "No such product: %(product_name)s"

    def __init__(self, product_name):
        LaunchpadFault.__init__(self, product_name=product_name)


class NoSuchPerson(LaunchpadFault):
    """There's no Person with the specified email registered in Launchpad."""

    error_code = 20
    msg_template = (
        "No such email is registered in Launchpad: %(email_address)s")

    def __init__(self, email_address):
        LaunchpadFault.__init__(self, email_address=email_address)


class NoSuchBranch(LaunchpadFault):
    """There's no Branch with the specified URL registered in Launchpad."""

    error_code = 30
    msg_template = "No such branch: %(branch_url)s"

    def __init__(self, branch_url):
        LaunchpadFault.__init__(self, branch_url=branch_url)


class NoSuchBug(LaunchpadFault):
    """There's no Bug with the specified id registered in Launchpad."""

    error_code = 40
    msg_template = "No such bug: %(bug_id)s"

    def __init__(self, bug_id):
        LaunchpadFault.__init__(self, bug_id=bug_id)


class BranchAlreadyRegistered(LaunchpadFault):
    """A branch with the same URL is already registered in Launchpad."""

    error_code = 50
    msg_template = "%(branch_url)s is already registered."

    def __init__(self, branch_url):
        LaunchpadFault.__init__(self, branch_url=branch_url)
