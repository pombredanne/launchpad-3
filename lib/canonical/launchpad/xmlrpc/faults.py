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
    """Base class for a Launchpad XMLRPC fault."""

    error_code = None

    def __init__(self, msg):
        assert self.error_code is not None, "Subclasses must define error_code."
        xmlrpclib.Fault.__init__(self, self.error_code, msg)


class NoSuchProduct(LaunchpadFault):
    """There's no such product registered in Launchpad."""

    error_code = 10

    def __init__(self, product_name):
        LaunchpadFault.__init__(self, "No such product: %s." % product_name)


class NoSuchPerson(LaunchpadFault):
    """There's no Person with the specified email registered in Launchpad."""

    error_code = 20

    def __init__(self, email_address):
        LaunchpadFault.__init__(
            self,
            "No such email is registered in Launchpad: %s." % email_address)


class NoSuchBranch(LaunchpadFault):
    """There's no Branch with the specified URL registered in Launchpad."""

    error_code = 30

    def __init__(self, branch_url):
        LaunchpadFault.__init__(self, "No such branch: %s" % branch_url)


class NoSuchBug(LaunchpadFault):
    """There's no Bug with the specified id registered in Launchpad."""

    error_code = 40

    def __init__(self, bug_id):
        LaunchpadFault.__init__(self, "No such bug: %s" % bug_id)


class BranchAlreadyRegistered(LaunchpadFault):
    """A branch with the same URL is already registered in Launchpad."""

    error_code = 50

    def __init__(self, branch_url):
        LaunchpadFault.__init__(self, "%s is already registered." % branch_url)
