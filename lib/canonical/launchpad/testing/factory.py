# Copyright 2007-2008 Canonical Ltd.  All rights reserved.

"""Testing infrastructure for the Launchpad application.

This module should not have any actual tests.
"""

__metaclass__ = type
__all__ = [
    'LaunchpadObjectFactory',
    'time_counter',
    ]

from datetime import datetime, timedelta
from StringIO import StringIO
import pytz

from zope.component import getUtility
from canonical.codehosting.codeimport.worker import CodeImportSourceDetails
from canonical.librarian.interfaces import ILibrarianClient
from canonical.launchpad.interfaces import (
    BranchMergeProposalStatus,
    BranchSubscriptionNotificationLevel,
    BranchType,
    CodeImportMachineState,
    CodeImportResultStatus,
    CodeImportReviewStatus,
    CodeReviewNotificationLevel,
    CreateBugParams,
    EmailAddressStatus,
    IBranchSet,
    IBugSet,
    ICodeImportJobWorkflow,
    ICodeImportMachineSet,
    ICodeImportEventSet,
    ICodeImportResultSet,
    ICodeImportSet,
    ICountrySet,
    IEmailAddressSet,
    ILibraryFileAliasSet,
    IPersonSet,
    IProductSet,
    IProjectSet,
    IRevisionSet,
    IShippingRequestSet,
    ISpecificationSet,
    IStandardShipItRequestSet,
    ITranslationGroupSet,
    License,
    PersonCreationRationale,
    RevisionControlSystems,
    ShipItFlavour,
    ShippingRequestStatus,
    SpecificationDefinitionStatus,
    TeamSubscriptionPolicy,
    UnknownBranchTypeError,
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

    def makePerson(self, email=None, name=None, password=None,
                   email_address_status=None, displayname=None):
        """Create and return a new, arbitrary Person.

        :param email: The email address for the new person.
        :param name: The name for the new person.
        :param password: The password for the person.
            This password can be used in setupBrowser in combination
            with the email address to create a browser for this new
            person.
        :param email_address_status: If specified, the status of the email
            address is set to the email_address_status.
        :param displayname: The display name to use for the person.
        """
        if email is None:
            email = "%s@example.com" % self.getUniqueString('email')
        if name is None:
            name = self.getUniqueString('person-name')
        if password is None:
            password = self.getUniqueString('password')
        else:
            # If a password was specified, validate the email address,
            # unless told otherwise.
            if email_address_status is None:
                email_address_status = EmailAddressStatus.VALIDATED
        # Set the password to test in order to allow people that have
        # been created this way can be logged in.
        person, email = getUtility(IPersonSet).createPersonAndEmail(
            email, rationale=PersonCreationRationale.UNKNOWN, name=name,
            password=password, displayname=displayname)
        # To make the person someone valid in Launchpad, validate the
        # email.
        if email_address_status == EmailAddressStatus.VALIDATED:
            person.validateAndEnsurePreferredEmail(email)
        elif email_address_status is not None:
            email.status = email_address_status
            email.syncUpdate()
        else:
            # Leave the email as NEW.
            pass
        return person

    def makeTeam(self, owner, displayname=None, email=None):
        """Create and return a new, arbitrary Team.

        The subscription policy of this new team will be OPEN.

        :param owner: The IPerson to use as the team's owner.
        :param displayname: The team's display name.  If not given we'll use
            the auto-generated name.
        :param email: The email address to use as the team's contact address.
        """
        name = self.getUniqueString('team-name')
        if displayname is None:
            displayname = name
        team = getUtility(IPersonSet).newTeam(
            owner, name, displayname,
            subscriptionpolicy=TeamSubscriptionPolicy.OPEN)
        if email is not None:
            team.setContactAddress(
                getUtility(IEmailAddressSet).new(email, team))
        return team

    def makeTranslationGroup(
        self, owner, name=None, title=None, summary=None):
        """Create a new, arbitrary `TranslationGroup`."""
        if name is None:
            name = self.getUniqueString("translationgroup")
        if title is None:
            title = self.getUniqueString("title")
        if summary is None:
            summary = self.getUniqueString("summary")
        return getUtility(ITranslationGroupSet).new(
            name, title, summary, owner)

    def makeProduct(self, name=None, project=None, displayname=None):
        """Create and return a new, arbitrary Product."""
        owner = self.makePerson()
        if name is None:
            name = self.getUniqueString('product-name')
        if displayname is None:
            displayname = self.getUniqueString('displayname')
        return getUtility(IProductSet).createProduct(
            owner,
            name,
            displayname,
            self.getUniqueString('title'),
            self.getUniqueString('summary'),
            self.getUniqueString('description'),
            licenses=[License.GNU_GPL_V2], project=project)

    def makeProject(self, name=None, displayname=None):
        """Create and return a new, arbitrary Project."""
        owner = self.makePerson()
        if name is None:
            name = self.getUniqueString('project-name')
        if displayname is None:
            displayname = self.getUniqueString('displayname')
        return getUtility(IProjectSet).new(
            name,
            displayname,
            self.getUniqueString('title'),
            None,
            self.getUniqueString('summary'),
            self.getUniqueString('description'),
            owner)

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
        elif branch_type in (BranchType.MIRRORED, BranchType.REMOTE):
            if url is None:
                url = self.getUniqueURL()
        else:
            raise UnknownBranchTypeError(
                'Unrecognized branch type: %r' % (branch_type,))
        return getUtility(IBranchSet).new(
            branch_type, name, registrant, owner, product, url,
            **optional_branch_args)

    def makeBranchMergeProposal(self, target_branch=None, registrant=None,
                                set_state=None, dependent_branch=None):
        """Create a proposal to merge based on anonymous branches."""
        product = None
        if dependent_branch is not None:
            product = dependent_branch.product
        if target_branch is None:
            target_branch = self.makeBranch(product=product)
        product = target_branch.product
        if registrant is None:
            registrant = self.makePerson()
        source_branch = self.makeBranch(product=product)
        proposal = source_branch.addLandingTarget(
            registrant, target_branch, dependent_branch=dependent_branch)

        if (set_state is None or
            set_state == BranchMergeProposalStatus.WORK_IN_PROGRESS):
            # The initial state is work in progress, so do nothing.
            pass
        elif set_state == BranchMergeProposalStatus.NEEDS_REVIEW:
            proposal.requestReview()
        elif set_state == BranchMergeProposalStatus.CODE_APPROVED:
            proposal.approveBranch(
                proposal.target_branch.owner, 'some_revision')
        elif set_state == BranchMergeProposalStatus.REJECTED:
            proposal.rejectBranch(
                proposal.target_branch.owner, 'some_revision')
        elif set_state == BranchMergeProposalStatus.MERGED:
            proposal.markAsMerged()
        elif set_state == BranchMergeProposalStatus.MERGE_FAILED:
            proposal.mergeFailed(proposal.target_branch.owner)
        elif set_state == BranchMergeProposalStatus.QUEUED:
            proposal.commit_message = self.getUniqueString('commit message')
            proposal.enqueue(
                proposal.target_branch.owner, 'some_revision')
        elif set_state == BranchMergeProposalStatus.SUPERSEDED:
            proposal.resubmit(proposal.registrant)
        else:
            raise AssertionError('Unknown status: %s' % set_state)

        return proposal

    def makeBranchSubscription(self, branch_title=None,
                               person_displayname=None):
        """Create a BranchSubscription.

        :param branch_title: The title to use for the created Branch
        :param person_displayname: The displayname for the created Person
        """
        branch = self.makeBranch(title=branch_title)
        person = self.makePerson(displayname=person_displayname,
            email_address_status=EmailAddressStatus.VALIDATED)
        return branch.subscribe(person,
            BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.NOEMAIL)

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
        for index in range(count):
            revision = revision_set.new(
                revision_id = self.getUniqueString('revision-id'),
                log_body=self.getUniqueString('log-body'),
                revision_date=date_generator.next(),
                revision_author=author,
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
            product = self.makeProduct()
        owner = self.makePerson()
        title = self.getUniqueString()
        create_bug_params = CreateBugParams(
            owner, title, comment=self.getUniqueString())
        create_bug_params.setBugTarget(product=product)
        return getUtility(IBugSet).createBug(create_bug_params)

    def makeSpecification(self, product=None):
        """Create and return a new, arbitrary Blueprint.

        :param product: The product to make the blueprint on.  If one is
            not specified, an arbitrary product is created.
        """
        if product is None:
            product = self.makeProduct()
        return getUtility(ISpecificationSet).new(
            name=self.getUniqueString('name'),
            title=self.getUniqueString('title'),
            specurl=None,
            summary=self.getUniqueString('summary'),
            definition_status=SpecificationDefinitionStatus.NEW,
            owner=self.makePerson(),
            product=product)

    def makeCodeImport(self, svn_branch_url=None, cvs_root=None,
                       cvs_module=None):
        """Create and return a new, arbitrary code import.

        The code import will be an import from a Subversion repository located
        at `url`, or an arbitrary unique url if the parameter is not supplied.
        """
        if svn_branch_url is cvs_root is cvs_module is None:
            svn_branch_url = self.getUniqueURL()

        product = self.makeProduct()
        branch_name = self.getUniqueString('name')
        # The registrant gets emailed, so needs a preferred email.
        registrant = self.makePerson(
            email_address_status=EmailAddressStatus.VALIDATED)

        code_import_set = getUtility(ICodeImportSet)
        if svn_branch_url is not None:
            return code_import_set.new(
                registrant, product, branch_name,
                rcs_type=RevisionControlSystems.SVN,
                svn_branch_url=svn_branch_url)
        else:
            return code_import_set.new(
                registrant, product, branch_name,
                rcs_type=RevisionControlSystems.CVS,
                cvs_root=cvs_root, cvs_module=cvs_module)

    def makeCodeImportEvent(self):
        """Create and return a CodeImportEvent."""
        code_import = self.makeCodeImport()
        person = self.makePerson()
        code_import_event_set = getUtility(ICodeImportEventSet)
        return code_import_event_set.newCreate(code_import, person)

    def makeCodeImportJob(self, code_import=None):
        """Create and return a new code import job for the given import.

        This implies setting the import's review_status to REVIEWED.
        """
        if code_import is None:
            code_import = self.makeCodeImport()
        code_import.updateFromData(
            {'review_status': CodeImportReviewStatus.REVIEWED},
            code_import.registrant)
        workflow = getUtility(ICodeImportJobWorkflow)
        return workflow.newJob(code_import)

    def makeCodeImportMachine(self, set_online=False, hostname=None):
        """Return a new CodeImportMachine.

        The machine will be in the OFFLINE state."""
        if hostname is None:
            hostname = self.getUniqueString('machine-')
        if set_online:
            state = CodeImportMachineState.ONLINE
        else:
            state = CodeImportMachineState.OFFLINE
        machine = getUtility(ICodeImportMachineSet).new(hostname, state)
        return machine

    def makeCodeImportResult(self, code_import=None, result_status=None,
                             date_started=None, date_finished=None,
                             log_excerpt=None, log_alias=None, machine=None):
        """Create and return a new CodeImportResult."""
        if code_import is None:
            code_import = self.makeCodeImport()
        if machine is None:
            machine = self.makeCodeImportMachine()
        requesting_user = None
        if log_excerpt is None:
            log_excerpt = self.getUniqueString()
        if result_status is None:
            result_status = CodeImportResultStatus.FAILURE
        if date_finished is None:
            # If a date_started is specified, then base the finish time
            # on that.
            if date_started is None:
                date_finished = time_counter().next()
            else:
                date_finished = date_started + timedelta(hours=4)
        if date_started is None:
            date_started = date_finished - timedelta(hours=4)
        if log_alias is None:
            log_alias = self.makeLibraryFileAlias()
        return getUtility(ICodeImportResultSet).new(
            code_import, machine, requesting_user, log_excerpt, log_alias,
            result_status, date_started, date_finished)

    def makeCodeImportSourceDetails(self, branch_id=None, rcstype=None,
                                    svn_branch_url=None, cvs_root=None,
                                    cvs_module=None,
                                    source_product_series_id=0):
        # XXX: MichaelHudson 2008-05-19 bug=231819: The
        # source_product_series_id attribute is to do with the new system
        # looking in legacy locations for foreign trees and can be deleted
        # when the new system has been running for a while.
        if branch_id is None:
            branch_id = self.getUniqueInteger()
        if rcstype is None:
            rcstype = 'svn'
        if rcstype == 'svn':
            assert cvs_root is cvs_module is None
            if svn_branch_url is None:
                svn_branch_url = self.getUniqueURL()
        elif rcstype == 'cvs':
            assert svn_branch_url is None
            if cvs_root is None:
                cvs_root = self.getUniqueString()
            if cvs_module is None:
                cvs_module = self.getUniqueString()
        else:
            raise AssertionError("Unknown rcstype %r." % rcstype)
        return CodeImportSourceDetails(
            branch_id, rcstype, svn_branch_url, cvs_root, cvs_module,
            source_product_series_id)

    def makeSeries(self, user_branch=None, import_branch=None,
                   name=None, product=None):
        """Create a new, arbitrary ProductSeries.

        :param user_branch: If supplied, the branch to set as
            ProductSeries.user_branch.
        :param import_branch: If supplied, the branch to set as
            ProductSeries.import_branch.
        :param product: If supplied, the name of the series.
        :param product: If supplied, the series is created for this product.
            Otherwise, a new product is created.
        """
        if product is None:
            product = self.makeProduct()
        if name is None:
            name = self.getUniqueString()
        series = product.newSeries(
            product.owner, name, self.getUniqueString(), user_branch)
        series.import_branch = import_branch
        syncUpdate(series)
        return series

    def makeShipItRequest(self, flavour=ShipItFlavour.UBUNTU):
        """Create a `ShipItRequest` associated with a newly created person.

        The request's status will be approved and it will contain an arbitrary
        number of CDs of the given flavour.
        """
        brazil = getUtility(ICountrySet)['BR']
        city = 'Sao Carlos'
        addressline = 'Antonio Rodrigues Cajado 1506'
        name = 'Guilherme Salgado'
        phone = '+551635015218'
        person = self.makePerson()
        request = getUtility(IShippingRequestSet).new(
            person, name, brazil, city, addressline, phone)
        # We don't want to login() as the person used to create the request,
        # so we remove the security proxy for changing the status.
        from zope.security.proxy import removeSecurityProxy
        removeSecurityProxy(request).status = ShippingRequestStatus.APPROVED
        template = getUtility(IStandardShipItRequestSet).getByFlavour(
            flavour)[0]
        request.setQuantities({flavour: template.quantities})
        return request

    def makeLibraryFileAlias(self, log_data=None):
        """Make a library file, and return the alias."""
        if log_data is None:
            log_data = self.getUniqueString()
        filename = self.getUniqueString('filename')
        log_alias_id = getUtility(ILibrarianClient).addFile(
            filename, len(log_data), StringIO(log_data), 'text/plain')
        return getUtility(ILibraryFileAliasSet)[log_alias_id]
