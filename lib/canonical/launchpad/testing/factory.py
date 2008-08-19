# Copyright 2007-2008 Canonical Ltd.  All rights reserved.

"""Testing infrastructure for the Launchpad application.

This module should not have any actual tests.
"""

__metaclass__ = type
__all__ = [
    'LaunchpadObjectFactory',
    'ObjectFactory',
    'time_counter',
    ]

from datetime import datetime, timedelta
from email.Utils import make_msgid, formatdate
from StringIO import StringIO

import pytz
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.codehosting.codeimport.worker import CodeImportSourceDetails
from canonical.librarian.interfaces import ILibrarianClient
from canonical.launchpad.interfaces import (
    AccountStatus,
    BranchMergeProposalStatus,
    BranchSubscriptionNotificationLevel,
    BranchType,
    CodeImportMachineState,
    CodeImportResultStatus,
    CodeImportReviewStatus,
    CodeReviewNotificationLevel,
    CreateBugParams,
    DistroSeriesStatus,
    EmailAddressStatus,
    IBranchSet,
    IBugSet,
    IBugWatchSet,
    ICodeImportJobWorkflow,
    ICodeImportMachineSet,
    ICodeImportEventSet,
    ICodeImportResultSet,
    ICodeImportSet,
    ICountrySet,
    IDistributionSet,
    IDistroSeriesSet,
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
from canonical.launchpad.interfaces.bugtask import IBugTaskSet
from canonical.launchpad.interfaces.distribution import IDistribution
from canonical.launchpad.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage)
from canonical.launchpad.interfaces.distroseries import IDistroSeries
from canonical.launchpad.interfaces.product import IProduct
from canonical.launchpad.interfaces.productseries import IProductSeries
from canonical.launchpad.interfaces.sourcepackage import ISourcePackage
from canonical.launchpad.ftests import syncUpdate
from canonical.launchpad.database import Message, MessageChunk
from canonical.launchpad.mail.signedmessage import SignedMessage


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


class ObjectFactory:
    """Factory methods for creating useful Python objects."""

    def __init__(self):
        # Initialise the unique identifier.
        self._integer = 0

    def getUniqueEmailAddress(self):
        return "%s@example.com" % self.getUniqueString('email')

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

    def getUniqueURL(self, scheme=None, host=None):
        """Return a URL unique to this run of the test case."""
        if scheme is None:
            scheme = 'http'
        if host is None:
            host = "%s.domain.com" % self.getUniqueString('domain')
        return '%s://%s/%s' % (scheme, host, self.getUniqueString('path'))


# NOTE:
#
# The LaunchpadObjectFactory is driven purely by use.  The version here
# is by no means complete for Launchpad objects.  If you need to create
# anonymous objects for your tests then add methods to the factory.
#
class LaunchpadObjectFactory(ObjectFactory):
    """Factory methods for creating Launchpad objects.

    All the factory methods should be callable with no parameters.
    When this is done, the returned object should have unique references
    for any other required objects.
    """

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
            email = self.getUniqueEmailAddress()
        if name is None:
            name = self.getUniqueString('person-name')
        if password is None:
            password = self.getUniqueString('password')
        # By default, make the email address preferred.
        if (email_address_status is None
                or email_address_status == EmailAddressStatus.VALIDATED):
            email_address_status = EmailAddressStatus.PREFERRED
        # Set the password to test in order to allow people that have
        # been created this way can be logged in.
        person, email = getUtility(IPersonSet).createPersonAndEmail(
            email, rationale=PersonCreationRationale.UNKNOWN, name=name,
            password=password, displayname=displayname)

        # To make the person someone valid in Launchpad, validate the
        # email.
        if email_address_status == EmailAddressStatus.PREFERRED:
            person.validateAndEnsurePreferredEmail(email)
            removeSecurityProxy(person.account).status = AccountStatus.ACTIVE
        # Make the account ACTIVE if we have a preferred email address now.
        if (person.preferredemail is not None and
            person.preferredemail.status == EmailAddressStatus.PREFERRED):
            removeSecurityProxy(person.account).status = AccountStatus.ACTIVE
        removeSecurityProxy(email).status = email_address_status
        syncUpdate(email)
        return person

    def makeTeam(self, owner, displayname=None, email=None, name=None,
                 subscription_policy=TeamSubscriptionPolicy.OPEN):
        """Create and return a new, arbitrary Team.

        :param owner: The IPerson to use as the team's owner.
        :param displayname: The team's display name.  If not given we'll use
            the auto-generated name.
        :param email: The email address to use as the team's contact address.
        :param subscription_policy: The subscription policy of the team.
        """
        if name is None:
            name = self.getUniqueString('team-name')
        if displayname is None:
            displayname = name
        team = getUtility(IPersonSet).newTeam(
            owner, name, displayname, subscriptionpolicy=subscription_policy)
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

    def makeProduct(self, name=None, project=None, displayname=None,
                    licenses=None, owner=None, registrant=None,
                    title=None, summary=None):
        """Create and return a new, arbitrary Product."""
        if owner is None:
            owner = self.makePerson()
        if name is None:
            name = self.getUniqueString('product-name')
        if displayname is None:
            if name is None:
                displayname = self.getUniqueString('displayname')
            else:
                displayname = name.capitalize()
        if licenses is None:
            licenses = [License.GNU_GPL_V2]
        if title is None:
            title = self.getUniqueString('title')
        if summary is None:
            summary = self.getUniqueString('summary')
        return getUtility(IProductSet).createProduct(
            owner,
            name,
            displayname,
            title,
            summary,
            self.getUniqueString('description'),
            licenses=licenses,
            project=project,
            registrant=registrant)

    def makeProductSeries(self, product=None, name=None, owner=None,
                          summary=None):
        """Create and return a new ProductSeries."""
        if product is None:
            product = self.makeProduct()
        if owner is None:
            owner = self.makePerson()
        if name is None:
            name = self.getUniqueString()
        if summary is None:
            summary = self.getUniqueString()
        return product.newSeries(owner=owner, name=name, summary=summary)

    def makeProject(self, name=None, displayname=None, title=None,
                    homepageurl=None, summary=None, owner=None,
                    description=None):
        """Create and return a new, arbitrary Project."""
        if owner is None:
            owner = self.makePerson()
        if name is None:
            name = self.getUniqueString('project-name')
        if displayname is None:
            displayname = self.getUniqueString('displayname')
        if summary is None:
            summary = self.getUniqueString('summary')
        if description is None:
            description = self.getUniqueString('description')
        if title is None:
            title = self.getUniqueString('title')
        return getUtility(IProjectSet).new(
            name=name,
            displayname=displayname,
            title=title,
            homepageurl=homepageurl,
            summary=summary,
            description=description,
            owner=owner)

    def makeBranch(self, branch_type=None, owner=None, name=None,
                   product=None, url=None, registrant=None,
                   explicit_junk=False, private=False,
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
        branch = getUtility(IBranchSet).new(
            branch_type, name, registrant, owner, product, url,
            **optional_branch_args)
        if private:
            removeSecurityProxy(branch).private = True
        return branch

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
        person = self.makePerson(displayname=person_displayname)
        return branch.subscribe(person,
            BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.NOEMAIL)

    def makeRevision(self, author=None, revision_date=None, parent_ids=None,
                     rev_id=None, log_body=None):
        """Create a single `Revision`."""
        if author is None:
            author = self.getUniqueString('author')
        if revision_date is None:
            revision_date = datetime.now(pytz.UTC)
        if parent_ids is None:
            parent_ids = []
        if rev_id is None:
            rev_id = self.getUniqueString('revision-id')
        if log_body is None:
            log_body = self.getUniqueString('log-body')
        return getUtility(IRevisionSet).new(
            revision_id=rev_id, log_body=log_body,
            revision_date=revision_date, revision_author=author,
            parent_ids=parent_ids, properties={})

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

    def makeBug(self, product=None, owner=None, bug_watch_url=None,
                private=False):
        """Create and return a new, arbitrary Bug.

        The bug returned uses default values where possible. See
        `IBugSet.new` for more information.

        :param product: If the product is not set, one is created
            and this is used as the primary bug target.
        :param owner: The reporter of the bug. If not set, one is created.
        :param bug_watch_url: If specified, create a bug watch pointing
            to this URL.
        """
        if product is None:
            product = self.makeProduct()
        if owner is None:
            owner = self.makePerson()
        title = self.getUniqueString()
        create_bug_params = CreateBugParams(
            owner, title, comment=self.getUniqueString(), private=private)
        create_bug_params.setBugTarget(product=product)
        bug = getUtility(IBugSet).createBug(create_bug_params)
        if bug_watch_url is not None:
            # fromText() creates a bug watch associated with the bug.
            getUtility(IBugWatchSet).fromText(bug_watch_url, bug, owner)
        return bug

    def makeBugTask(self, bug=None, target=None):
        """Create and return a bug task.

        If the bug is already targeted to the given target, the existing
        bug task is returned.

        :param bug: The `IBug` the bug tasks should be part of. If None,
            one will be created.
        :param target: The `IBugTarget`, to which the bug will be
            targeted to.
        """
        if bug is None:
            bug = self.makeBug()
        if target is None:
            target = self.makeProduct()
        existing_bugtask = bug.getBugTask(target)
        if existing_bugtask is not None:
            return existing_bugtask
        owner = self.makePerson()

        if IProduct.providedBy(target):
            target_params = {'product': target}
        elif IProductSeries.providedBy(target):
            # We can't have a series task without a distribution task.
            self.makeBugTask(bug, target.product)
            target_params = {'productseries': target}
        elif IDistribution.providedBy(target):
            target_params = {'distribution': target}
        elif IDistributionSourcePackage.providedBy(target):
            target_params = {
                'distribution': target.distribution,
                'sourcepackagename': target.sourcepackagename,
                }
        elif IDistroSeries.providedBy(target):
            # We can't have a series task without a distribution task.
            self.makeBugTask(bug, target.distribution)
            target_params = {'distroseries': target}
        elif ISourcePackage.providedBy(target):
            distribution_package = target.distribution.getSourcePackage(
                target.sourcepackagename)
            # We can't have a series task without a distribution task.
            self.makeBugTask(bug, distribution_package)
            target_params = {
                'distroseries': target.distroseries,
                'sourcepackagename': target.sourcepackagename,
                }
        else:
            raise AssertionError('Unknown IBugTarget: %r' % target)

        return getUtility(IBugTaskSet).createTask(
            bug=bug, owner=owner, **target_params)

    def makeBugAttachment(self, bug=None, owner=None, data=None,
                          comment=None, filename=None, content_type=None):
        """Create and return a new bug attachment.

        :param bug: An `IBug` or a bug ID or name, or None, in which
            case a new bug is created.
        :param owner: An `IPerson`, or None, in which case a new
            person is created.
        :param data: A file-like object or a string, or None, in which
            case a unique string will be used.
        :param comment: An `IMessage` or a string, or None, in which
            case a new message will be generated.
        :param filename: A string, or None, in which case a unique
            string will be used.
        :param content_type: The MIME-type of this file.
        :return: An `IBugAttachment`.
        """
        if bug is None:
            bug = self.makeBug()
        elif isinstance(bug, (int, long, basestring)):
            bug = getUtility(IBugSet).getByNameOrID(str(bug))
        if owner is None:
            owner = self.makePerson()
        if data is None:
            data = self.getUniqueString()
        if comment is None:
            comment = self.getUniqueString()
        if filename is None:
            filename = self.getUniqueString()
        return bug.addAttachment(
            owner, data, comment, filename, content_type=content_type)

    def makeSignedMessage(self, msgid=None, body=None, subject=None):
        mail = SignedMessage()
        mail['From'] = self.getUniqueEmailAddress()
        if subject is None:
            subject = self.getUniqueString('subject')
        mail['Subject'] = subject
        if msgid is None:
            msgid = make_msgid('launchpad')
        if body is None:
            body = self.getUniqueString('body')
        mail['Message-Id'] = msgid
        mail['Date'] = formatdate()
        mail.set_payload(body)
        mail.parsed_string = mail.as_string()
        return mail

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
                       cvs_module=None, product=None, branch_name=None):
        """Create and return a new, arbitrary code import.

        The code import will be an import from a Subversion repository located
        at `url`, or an arbitrary unique url if the parameter is not supplied.
        """
        if svn_branch_url is cvs_root is cvs_module is None:
            svn_branch_url = self.getUniqueURL()

        if product is None:
            product = self.makeProduct()
        if branch_name is None:
            branch_name = self.getUniqueString('name')
        # The registrant gets emailed, so needs a preferred email.
        registrant = self.makePerson()

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

    def makeCodeReviewComment(self, sender=None, subject=None, body=None,
                              vote=None, vote_tag=None, parent=None):
        if sender is None:
            sender = self.makePerson()
        if subject is None:
            subject = self.getUniqueString('subject')
        if body is None:
            body = self.getUniqueString('content')
        if parent:
            merge_proposal = parent.branch_merge_proposal
        else:
            merge_proposal = self.makeBranchMergeProposal(registrant=sender)
        return merge_proposal.createComment(
            sender, subject, body, vote, vote_tag, parent)

    def makeMessage(self, subject=None, content=None, parent=None,
                    owner=None):
        if subject is None:
            subject = self.getUniqueString()
        if content is None:
            content = self.getUniqueString()
        if owner is None:
            owner = self.makePerson()
        rfc822msgid = make_msgid("launchpad")
        message = Message(rfc822msgid=rfc822msgid, subject=subject,
            owner=owner, parent=parent)
        MessageChunk(message=message, sequence=1, content=content)
        return message

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
        if import_branch is not None:
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

    def makeDistribution(self, name=None, displayname=None):
        """Make a new distribution."""
        if name is None:
            name = self.getUniqueString()
        if displayname is None:
            displayname = self.getUniqueString()
        title = self.getUniqueString()
        description = self.getUniqueString()
        summary = self.getUniqueString()
        domainname = self.getUniqueString()
        owner = self.makePerson()
        members = self.makeTeam(owner)
        return getUtility(IDistributionSet).new(
            name, displayname, title, description, summary, domainname,
            members, owner)

    def makeDistroRelease(self, distribution=None, version=None,
                          status=DistroSeriesStatus.DEVELOPMENT,
                          parent_series=None, name=None):
        """Make a new distro release."""
        if distribution is None:
            distribution = self.makeDistribution()
        if name is None:
            name = self.getUniqueString()

        return getUtility(IDistroSeriesSet).new(
            distribution=distribution,
            version="%s.0" % self.getUniqueInteger(),
            name=name,
            displayname=self.getUniqueString(),
            title=self.getUniqueString(), summary=self.getUniqueString(),
            description=self.getUniqueString(),
            parent_series=parent_series, owner=distribution.owner)
