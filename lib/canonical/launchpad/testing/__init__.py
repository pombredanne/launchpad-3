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
    BranchType,
    CodeImportReviewStatus,
    CreateBugParams,
    EmailAddressStatus,
    IBranchSet,
    IBugSet,
    ICodeImportJobWorkflow,
    ICodeImportSet,
    ILaunchpadCelebrities,
    IPersonSet,
    IProductSet,
    IRevisionSet,
    ISpecificationSet,
    License,
    PersonCreationRationale,
    RevisionControlSystems,
    SpecificationDefinitionStatus,
    UnknownBranchTypeError,
    )


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

    def makePerson(self, email=None, name=None, password=None,
                   email_address_status=None):
        """Create and return a new, arbitrary Person.

        :param email: The email address for the new person.
        :param name: The name for the new person.
        :param password: The password for the person.
            This password can be used in setupBrowser in combination
            with the email address to create a browser for this new
            person.
        :param email_address_status: If specified, the status of the email
            address is set to the email_address_status.
        """
        if email is None:
            email = self.getUniqueString('email')
        if name is None:
            name = self.getUniqueString('person-name')
        if password is None:
            password = self.getUniqueString('password')
        # Set the password to test in order to allow people that have
        # been created this way can be logged in.
        person, email = getUtility(IPersonSet).createPersonAndEmail(
            email, rationale=PersonCreationRationale.UNKNOWN, name=name,
            password=password)
        # To make the person someone valid in Launchpad, validate the
        # email.
        if (email_address_status is None or
            email_address_status == EmailAddressStatus.VALIDATED):
            person.validateAndEnsurePreferredEmail(email)
        else:
            email.status = email_address_status
            email.syncUpdate()
        return person

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
                   product=None, url=None, registrant=None,
                   explicit_junk=False,
                   **optional_branch_args):
        """Create and return a new, arbitrary Branch of the given type.

        Any parameters for IBranchSet.new can be specified to override the
        default ones.

        :param explicit_junk: If set to True, a product is not created
            if the product parameter is None.
        """
        if branch_type is None:
            branch_type = BranchType.HOSTED
        if owner is None:
            owner = self.makePerson()
        if registrant is None:
            registrant = owner
        if name is None:
            name = self.getUniqueString('branch')
        if product is None and not explicit_junk:
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
            branch_type, name, registrant, owner, product, url,
            **optional_branch_args)

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

    def makeBug(self, product=None):
        """Create and return a new, arbitrary Bug.

        The bug returned uses default values where possible. See
        `IBugSet.new` for more information.

        :param product: If the product is not set, one is created
            and this is used as the primary bug target.
        """
        if product is None:
            product=self.makeProduct()
        owner = self.makePerson()
        title = self.getUniqueString()
        create_bug_params = CreateBugParams(
            owner, title, comment=self.getUniqueString())
        create_bug_params.setBugTarget(product=product)
        return getUtility(IBugSet).createBug(create_bug_params)

    def makeBlueprint(self, product=None):
        """Create and return a new, arbitrary Blueprint.

        :param product: The product to make the blueprint on.  If one is
            not specified, an arbitrary product is created.
        """
        if product is None:
            product=self.makeProduct()
        return getUtility(ISpecificationSet).new(
            name=self.getUniqueString('name'),
            title=self.getUniqueString('title'),
            specurl=None,
            summary=self.getUniqueString('summary'),
            definition_status=SpecificationDefinitionStatus.NEW,
            owner=self.makePerson(),
            product=product)

    def makeCodeImport(self, url=None):
        """Create and return a new, arbitrary code import.

        The code import will be an import from a Subversion repository located
        at `url`, or an arbitrary unique url if the parameter is not supplied.
        """
        if url is None:
            url = self.getUniqueURL()
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
        branch = self.makeBranch(
            BranchType.IMPORTED, owner=vcs_imports)
        registrant = self.makePerson()
        return getUtility(ICodeImportSet).new(
            registrant, branch, rcs_type=RevisionControlSystems.SVN,
            svn_branch_url=url)

    def makeCodeImportJob(self, code_import):
        """Create and return a new code import job for the given import.

        This implies setting the import's review_status to REVIEWED.
        """
        code_import.updateFromData(
            {'review_status': CodeImportReviewStatus.REVIEWED},
            code_import.registrant)
        workflow = getUtility(ICodeImportJobWorkflow)
        return workflow.newJob(code_import)
