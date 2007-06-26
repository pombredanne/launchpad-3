# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Launchpad XMLRPC faults."""

__metaclass__ = type
__all__ = [
    'BranchAlreadyRegistered',
    'FileBugGotProductAndDistro',
    'FileBugMissingProductOrDistribution',
    'InvalidEntitlementType'
    'NoSuchDistribution',
    'NoSuchPackage',
    'NoSuchProduct',
    'NoSuchPerson',
    'NoSuchPersonOrTeam',
    'NoSuchBranch',
    'NoSuchBug',
    'RequiredParameterMissing',
    ]

import xmlrpclib

from canonical.lp.dbschema import BugTaskStatus

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
        'Invalid %(type)s: No user with the email address '
        '"%(email_address)s" was found')

    def __init__(self, email_address, type="user"):
        LaunchpadFault.__init__(self, type=type, email_address=email_address)


class NoSuchPersonOrTeam(LaunchpadFault):
    """There's no Person or Team with the specified name in Launchpad."""

    error_code = 20
    msg_template = (
        'Invalid Person or Team: No person or team with the name '
        '"%(name)s" was found')

    def __init__(self, name):
        LaunchpadFault.__init__(self, name=name)


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


class FileBugMissingProductOrDistribution(LaunchpadFault):
    """No product or distribution specified when filing a bug."""

    error_code = 60
    msg_template = (
        "Required arguments missing. You must specify either a product or "
        "distrubtion in which the bug exists.")


class FileBugGotProductAndDistro(LaunchpadFault):
    """A distribution and product were specified when filing a bug.

    Only one is allowed.
    """

    error_code = 70
    msg_template = (
        "Too many arguments. You may specify either a product or a "
        "distribution, but not both.")


class NoSuchDistribution(LaunchpadFault):
    """There's no such distribution registered in Launchpad."""

    error_code = 80
    msg_template = "No such distribution: %(distro_name)s"

    def __init__(self, distro_name):
        LaunchpadFault.__init__(self, distro_name=distro_name)


class NoSuchPackage(LaunchpadFault):
    """There's no source or binary package with the name provided."""

    error_code = 90
    msg_template = "No such package: %(package_name)s"

    def __init__(self, package_name):
        LaunchpadFault.__init__(self, package_name=package_name)


class RequiredParameterMissing(LaunchpadFault):
    """A required parameter was not provided."""

    error_code = 100
    msg_template = "Required parameter missing: %(parameter_name)s"

    def __init__(self, parameter_name):
        LaunchpadFault.__init__(self, parameter_name=parameter_name)

class InvalidEntitlementState(LaunchpadFault):
    """Raised if the entitlement state is not valid."""

    error_code = 110
    msg_template = "The entitlement state is invalid: %(entitlement_state)d"

    def __init__(self, entitlement_state):
        LaunchpadFault.__init__(self, entitlement_state=entitlement_state)

class InvalidEntitlementType(LaunchpadFault):
    """Raised if the entitlement type is not valid."""

    error_code = 120
    msg_template = "The entitlement type is invalid: %(entitlement_type)d"

    def __init__(self, entitlement_type):
        LaunchpadFault.__init__(self, entitlement_type=entitlement_type)
