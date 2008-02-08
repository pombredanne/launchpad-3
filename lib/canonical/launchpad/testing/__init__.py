 # Copyright 2007 Canonical Ltd.  All rights reserved.

"""Testing infrastructure for the Launchpad application.

This module should not have any actual tests.
"""

__metaclass__ = type
__all__ = [
    'LaunchpadObjectFactory',
    'time_counter',
    ]

from datetime import datetime, timedelta
import pytz

from zope.component import getUtility
from canonical.launchpad.interfaces import (
    BranchSubscriptionNotificationLevel,
    BranchType,
    CreateBugParams,
    IBranchSet,
    IBugSet,
    ICodeImportSet,
    ILaunchpadCelebrities,
    IPersonSet,
    IProductSet,
    IRevisionSet,
    ISpecificationSet,
    License,
    PersonCreationRationale,
    UnknownBranchTypeError,
    RevisionControlSystems,
    SpecificationDefinitionStatus,
    )
from canonical.launchpad.ftests import syncUpdate


def time_counter(origin=None, delta=timedelta(seconds=5)):
    """A generator for yielding datetime values.

    Each time the generator yields a value, the origin is incremented
    by the delta.

    >>> now = time_counter(datetime(2007, 12, 1), timedelta(days=1))
    >>> now.next()
    datetime.datetime(2007, 12, 1, 0, 0)
    >>> now.next()
    datetime.datetime(2007, 12, 2, 0, 0)
    >>> now.next()
    datetime.datetime(2007, 12, 3, 0, 0)
    """
    if origin is None:
        origin = datetime.now(pytz.UTC)
    now = origin
    while True:
        yield now
        now += delta


# NOTE:
#
# The LaunchpadObjectFactory is driven purely by use.  The version here
# is by no means complete for Launchpad objects.  If you need to create
# anonymous objects for your tests then add methods to the factory.
#
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

    def makeBranchSubscription(self):
        """Create a BranchSubscription."""
        branch = self.makeBranch()
        return branch.subscribe(self.makePerson(),
            BranchSubscriptionNotificationLevel.NOEMAIL, None)

    def makeRevisionsForBranch(self, branch, count=5, author=None,
                               date_generator=None):
        """Add `count` revisions to the revision history of `branch`.

        :param branch: The branch to add the revisions to.
        :param count: The number of revisions to add.
        :param author: A string for the author name.
        :param date_generator: A `time_counter` instance, defaults to starting
                               from 1-Jan-2007 if not set.
        """
        if date_generator is None:
            date_generator = time_counter(
                datetime(2007, 1, 1, tzinfo=pytz.UTC),
                delta=timedelta(days=1))
        sequence = branch.revision_count
        parent = branch.getTipRevision()
        if parent is None:
            parent_ids = []
        else:
            parent_ids = [parent.revision_id]

        revision_set = getUtility(IRevisionSet)
        if author is None:
            author = self.getUniqueString('author')
        # All revisions are owned by the admin user.  Don't ask.
        admin_user = getUtility(ILaunchpadCelebrities).admin
        for index in range(count):
            revision = revision_set.new(
                revision_id = self.getUniqueString('revision-id'),
                log_body=self.getUniqueString('log-body'),
                revision_date=date_generator.next(),
                revision_author=author,
                owner=admin_user,
                parent_ids=parent_ids,
                properties={})
            sequence += 1
            branch.createBranchRevision(sequence, revision)
            parent = revision
            parent_ids = [parent.revision_id]
        branch.updateScannedDetails(parent.revision_id, sequence)

    def makeBug(self, branch=None):
        """Create and return a new, arbitrary Bug.

        The bug returned uses default values where possible. See
        `IBugSet.new` for more information.

        :param branch: if supplied, this branch will be linked to the bug.
        """
        owner = self.makePerson()
        title = self.getUniqueString()
        create_bug_params = CreateBugParams(
            owner, title, comment=self.getUniqueString())
        create_bug_params.setBugTarget(product=self.makeProduct())
        bug = getUtility(IBugSet).createBug(create_bug_params)
        if branch is not None:
            bug.addBranch(branch, branch.owner)
        return bug

    def makeSpec(self, branch=None):
        """Create a new, arbitrary Specification.

        :param branch: if supplied, this will be linked to the spec.
        """
        spec = getUtility(ISpecificationSet).new(
            self.getUniqueString(),
            self.getUniqueString(),
            self.getUniqueURL(),
            self.getUniqueString(),
            SpecificationDefinitionStatus.APPROVED,
            self.makePerson(),
            product=self.makeProduct(),
            )
        if branch is not None:
            spec.linkBranch(branch, branch.owner)
        return spec

    def makeSeries(self, user_branch=None, import_branch=None):
        """Create a new, arbitrary ProductSeries.

        :param user_branch: If supplied, the branch to set as
            ProductSeries.user_branch.
        :param import_branch: If supplied, the branch to set as
            ProductSeries.import_branch.
        """
        product = self.makeProduct()
        series = product.newSeries(product.owner, self.getUniqueString(),
            self.getUniqueString(), user_branch)
        series.import_branch = import_branch
        syncUpdate(series)
        return series

    def makeCodeImport(self):
        """Create a new, arbitrary CodeImport."""
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
        branch = self.makeBranch(owner=vcs_imports)
        import_set = getUtility(ICodeImportSet)
        url = self.getUniqueURL()
        return import_set.new(
            branch.owner, branch, RevisionControlSystems.SVN, url)
