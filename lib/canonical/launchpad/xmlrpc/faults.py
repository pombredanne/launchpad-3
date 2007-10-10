# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

"""Launchpad XMLRPC faults."""

# Note: When you add a fault to this file, be sure to add it to configure.zcml
# in this directory.

__metaclass__ = type

__all__ = [
    'BadStatus',
    'BranchAlreadyRegistered',
    'BranchCreationForbidden',
    'BranchUniqueNameConflict',
    'FileBugGotProductAndDistro',
    'FileBugMissingProductOrDistribution',
    'InvalidBranchUrl',
    'NoSuchBranch',
    'NoBranchForSeries',
    'NoSuchBug',
    'NoSuchDistribution',
    'NoSuchPackage',
    'NoSuchPerson',
    'NoSuchProduct',
    'NoSuchTeamMailingList',
    'RequiredParameterMissing',
    'UnexpectedStatusReport',
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
        'Invalid %(type)s: No user with the email address '
        '"%(email_address)s" was found')

    def __init__(self, email_address, type="user"):
        LaunchpadFault.__init__(self, type=type, email_address=email_address)


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
        "distribution in which the bug exists.")


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


class BranchCreationForbidden(LaunchpadFault):
    """The user was not permitted to create a branch."""

    error_code = 110
    msg_template = (
        "You are not allowed to create a branch for project: "
        "%(parameter_name)s")

    def __init__(self, parameter_name):
        LaunchpadFault.__init__(self, parameter_name=parameter_name)


class InvalidBranchUrl(LaunchpadFault):
    """The provided branch URL is not valid."""

    error_code = 120
    msg_template = "Invalid URL: %(branch_url)s\n%(message)s"

    def __init__(self, branch_url, message):
        LaunchpadFault.__init__(self, branch_url=branch_url, message=message)


class BranchUniqueNameConflict(LaunchpadFault):
    """There is already a branch with this unique name."""

    error_code = 130
    msg_template = "Unique name already in use: %(unique_name)s"

    def __init__(self, unique_name):
        LaunchpadFault.__init__(self, unique_name=unique_name)

class NoSuchTeamMailingList(LaunchpadFault):
    """There is no such team mailing list with the given name."""

    error_code = 140
    msg_template = 'No such team mailing list: %(team_name)s'

    def __init__(self, team_name):
        LaunchpadFault.__init__(self, team_name=team_name)


class UnexpectedStatusReport(LaunchpadFault):
    """A team mailing list received an unexpected status report.

    In other words, the mailing list was not in a state that was awaiting such
    a status report.
    """

    error_code = 150
    msg_template = ('Unexpected status report "%(status)s" '
                    'for team: %(team_name)s')

    def __init__(self, team_name, status):
        LaunchpadFault.__init__(self, team_name=team_name, status=status)


class BadStatus(LaunchpadFault):
    """A bad status string was received."""

    error_code = 160
    msg_template = 'Bad status string "%(status)s" for team: %(team_name)s'

    def __init__(self, team_name, status):
        LaunchpadFault.__init__(self, team_name=team_name, status=status)


class NoBranchForSeries(LaunchpadFault):
    """The series has no branch registered with it."""

    error_code = 170
    msg_template = (
        'Series %(series_name)s on %(product_name)s has no branch associated '
        'with it.')

    def __init__(self, series):
        LaunchpadFault.__init__(
            self, series_name=series.name, product_name=series.product.name)


class NoSuchSeries(LaunchpadFault):
    """There is no such series on a particular project."""

    error_code = 180
    msg_template = (
        'Project %(product_name)s has no series called "%(series_name)s"')

    def __init__(self, series_name, product):
        LaunchpadFault.__init__(
            self, series_name=series_name, product_name=product.name)


class InvalidBranchIdentifier(LaunchpadFault):
    """The branch identifier wasn't even remotely correct."""

    error_code = 190
    msg_template = (
        'Invalid branch identifier: %(branch_path)r')

    def __init__(self, branch_path):
        LaunchpadFault.__init__(self, branch_path=branch_path)
