# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Testing infrastructure for the Launchpad application.

This module should not have any actual tests.
"""

__metaclass__ = type
__all__ = [
    'LaunchpadObjectFactory',
    ]

from zope.component import getUtility
from canonical.launchpad.interfaces import (
    BranchType, CreateBugParams, IBranchSet, IBugSet, IPersonSet, IProductSet,
    License, PersonCreationRationale, UnknownBranchTypeError)


# NOTE:
#
# The LaunchpadObjectFactory is driven purely by use.  The version here
# is by no means complete for Launchpad objects.  If you need to create
# anonymous objects for your tests then add methods to the factory.
#
# All factory methods should be callable with no parameters.  If you
# add a keyword argument to a method, please be considerate of the other
# users of the factory and make it behave at least as good as it was
# before.


class LaunchpadObjectFactory:
    """Factory methods for creating Launchpad objects.

    All the factory methods should be callable with no parameters.
    When this is done, the returned object should have unique references
    for any other required objects.
    """

    def __init__(self):
        # Initialise the unique identifier.
        self._integer = 0

    def getUniqueInteger(self):
        """Return an integer unique to this factory instance."""
        self._integer += 1
        return self._integer

    def getUniqueString(self, prefix=None):
        """Return a string unique to this factory instance.

        The string returned will always be a valid name that can be used in
        Launchpad URLs.

        :param prefix: Used as a prefix for the unique string. If unspecified,
            defaults to 'generic-string'.
        """
        if prefix is None:
            prefix = "generic-string"
        string = "%s%s" % (prefix, self.getUniqueInteger())
        return string.replace('_', '-').lower()

    def getUniqueURL(self):
        """Return a URL unique to this run of the test case."""
        return 'http://%s.example.com/%s' % (
            self.getUniqueString('domain'), self.getUniqueString('path'))

    def makePerson(self, email=None, name=None):
        """Create and return a new, arbitrary Person."""
        if email is None:
            email = self.getUniqueString('email')
        if name is None:
            name = self.getUniqueString('person-name')
        return getUtility(IPersonSet).createPersonAndEmail(
            email, rationale=PersonCreationRationale.UNKNOWN, name=name)[0]

    def makeProduct(self, name=None):
        """Create and return a new, arbitrary Product."""
        owner = self.makePerson()
        if name is None:
            name = self.getUniqueString('product-name')
        return getUtility(IProductSet).createProduct(
            owner, name,
            self.getUniqueString('displayname'),
            self.getUniqueString('title'),
            self.getUniqueString('summary'),
            self.getUniqueString('description'),
            licenses=[License.GPL])

    def makeBranch(self, branch_type=None, owner=None, name=None,
                   product=None, url=None, **optional_branch_args):
        """Create and return a new, arbitrary Branch of the given type.

        Any parameters for IBranchSet.new can be specified to override the
        default ones.
        """
        if branch_type is None:
            branch_type = BranchType.HOSTED
        if owner is None:
            owner = self.makePerson()
        if name is None:
            name = self.getUniqueString('branch')
        if product is None:
            product = self.makeProduct()

        if branch_type in (BranchType.HOSTED, BranchType.IMPORTED):
            url = None
        elif (branch_type in (BranchType.MIRRORED, BranchType.REMOTE)
              and url is None):
            url = self.getUniqueURL()
        else:
            raise UnknownBranchTypeError(
                'Unrecognized branch type: %r' % (branch_type,))
        return getUtility(IBranchSet).new(
            branch_type, name, owner, owner, product, url,
            **optional_branch_args)

    def makeBug(self):
        """Create and return a new, arbitrary Bug.

        The bug returned uses default values where possible. See
        `IBugSet.new` for more information.
        """
        owner = self.makePerson()
        title = self.getUniqueString()
        create_bug_params = CreateBugParams(
            owner, title, comment=self.getUniqueString())
        create_bug_params.setBugTarget(product=self.makeProduct())
        return getUtility(IBugSet).createBug(create_bug_params)
