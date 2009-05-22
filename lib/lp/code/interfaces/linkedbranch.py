# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0213

"""Interface for objects that have a linked branch.

A linked branch is a branch that's somehow officially related to an object. It
might be the main branch of a series, the trunk branch of a project, the
backports branch for a source package or something else.
"""

__metaclass__ = type
__all__ = [
    'CannotHaveLinkedBranch',
    'get_linked_branch',
    'ICanHasLinkedBranch',
    'NoLinkedBranch',
    ]

from zope.interface import Attribute, Interface


class ICanHasLinkedBranch(Interface):
    """Something that has a linked branch."""

    branch = Attribute("The linked branch.")


class CannotHaveLinkedBranch(Exception):
    """Raised when we try to get the linked branch for a thing that can't."""

    def __init__(self, component):
        self.component = component
        Exception.__init__(
            self, "%r cannot have linked branches." % (component,))


class NoLinkedBranch(Exception):
    """Raised when there's no linked branch for a thing."""

    def __init__(self, component):
        self.component = component
        Exception.__init__(self, "%r has no linked branch." % (component,))


def get_linked_branch(provided):
    """Get the linked branch for 'provided', whatever that is.

    :raise CannotHaveLinkedBranch: If 'provided' can never have a linked
        branch.
    :raise NoLinkedBranch: If 'provided' could have a linked branch, but
        doesn't.
    :return: The linked branch, an `IBranch`.
    """
    has_linked_branch = ICanHasLinkedBranch(provided)
    if has_linked_branch is None:
        raise CannotHaveLinkedBranch(provided)
    branch = has_linked_branch.branch
    if branch is None:
        raise NoLinkedBranch(provided)
    return branch
