# Copyright 2004-2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""Database classes including and related to Product."""

__metaclass__ = type
__all__ = [
    'Product',
    'ProductSet',
    'ProductWithLicenses',
    ]


import operator
import datetime
import calendar
import pytz
import sets
from sqlobject import (
    ForeignKey, StringCol, BoolCol, SQLMultipleJoin, SQLRelatedJoin,
    SQLObjectNotFound, AND)
from storm.expr import And
from storm.locals import Unicode
from storm.store import Store
from zope.interface import implements
from zope.component import getUtility

from canonical.cachedproperty import cachedproperty
from lazr.delegates import delegates
from canonical.lazr.utils import safe_hasattr
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import quote, SQLBase, sqlvalues
from canonical.launchpad.database.branch import BranchSet
from canonical.launchpad.database.branchvisibilitypolicy import (
    BranchVisibilityPolicyMixin)
from canonical.launchpad.database.bug import (
    BugSet, get_bug_tags, get_bug_tags_open_count)
from canonical.launchpad.database.bugtarget import (
    BugTargetBase, OfficialBugTagTargetMixin)
from canonical.launchpad.database.bugtask import BugTask
from canonical.launchpad.database.bugtracker import BugTracker
from canonical.launchpad.database.bugwatch import BugWatch
from canonical.launchpad.database.commercialsubscription import (
    CommercialSubscription)
from canonical.launchpad.database.customlanguagecode import CustomLanguageCode
from canonical.launchpad.database.distribution import Distribution
from canonical.launchpad.database.karma import KarmaContextMixin
from lp.answers.model.faq import FAQ, FAQSearch
from canonical.launchpad.database.mentoringoffer import MentoringOffer
from canonical.launchpad.database.milestone import (
    HasMilestonesMixin, Milestone)
from canonical.launchpad.validators.person import (
    validate_person_not_private_membership, validate_public_person)
from canonical.launchpad.database.announcement import MakesAnnouncements
from canonical.launchpad.database.packaging import Packaging
from canonical.launchpad.database.pillar import HasAliasMixin
from canonical.launchpad.database.productbounty import ProductBounty
from canonical.launchpad.database.productlicense import ProductLicense
from canonical.launchpad.database.productrelease import ProductRelease
from canonical.launchpad.database.productseries import ProductSeries
from lp.answers.model.question import (
    QuestionTargetSearch, QuestionTargetMixin)
from canonical.launchpad.database.specification import (
    HasSpecificationsMixin, Specification)
from canonical.launchpad.database.sprint import HasSprintsMixin
from canonical.launchpad.database.translationimportqueue import (
    HasTranslationImportsMixin)
from canonical.launchpad.database.structuralsubscription import (
    StructuralSubscriptionTargetMixin)
from canonical.launchpad.helpers import shortlist

from canonical.launchpad.interfaces.branch import (
    DEFAULT_BRANCH_STATUS_IN_LISTING)
from canonical.launchpad.interfaces.branchmergeproposal import (
    BranchMergeProposalStatus, IBranchMergeProposalGetter)
from canonical.launchpad.interfaces.bugsupervisor import IHasBugSupervisor
from canonical.launchpad.interfaces.launchpad import (
    IHasIcon, IHasLogo, IHasMugshot, ILaunchpadCelebrities, ILaunchpadUsage,
    NotFoundError)
from canonical.launchpad.interfaces.launchpadstatistic import (
    ILaunchpadStatisticSet)
from canonical.launchpad.interfaces.person import IPersonSet
from canonical.launchpad.interfaces.pillar import IPillarNameSet
from canonical.launchpad.interfaces.product import (
    IProduct, IProductSet, License, LicenseStatus)
from canonical.launchpad.interfaces.structuralsubscription import (
    IStructuralSubscriptionTarget)
from canonical.launchpad.interfaces.specification import (
    SpecificationDefinitionStatus, SpecificationFilter,
    SpecificationImplementationStatus, SpecificationSort)
from canonical.launchpad.interfaces.translationgroup import (
    TranslationPermission)
from canonical.launchpad.webapp.interfaces import (
        IStoreSelector, DEFAULT_FLAVOR, MAIN_STORE)


from lp.answers.interfaces.faqtarget import IFAQTarget
from lp.answers.interfaces.questioncollection import (
    QUESTION_STATUS_DEFAULT_SEARCH)
from lp.answers.interfaces.questiontarget import IQuestionTarget


def get_license_status(license_approved, license_reviewed, licenses):
    """Decide the license status for an `IProduct`.

    :return: A LicenseStatus enum value.
    """
    # A project can only be marked 'license_approved' if it is
    # OTHER_OPEN_SOURCE.  So, if it is 'license_approved' we return
    # OPEN_SOURCE, which means one of our admins has determined it is good
    # enough for us for the project to freely use Launchpad.
    if license_approved:
        return LicenseStatus.OPEN_SOURCE
    if len(licenses) == 0:
        # We don't know what the license is.
        return LicenseStatus.UNSPECIFIED
    elif License.OTHER_PROPRIETARY in licenses:
        # Notice the difference between the License and LicenseStatus.
        return LicenseStatus.PROPRIETARY
    elif License.OTHER_OPEN_SOURCE in licenses:
        if license_reviewed:
            # The OTHER_OPEN_SOURCE license was not manually approved
            # by setting license_approved to true.
            return LicenseStatus.PROPRIETARY
        else:
            # The OTHER_OPEN_SOURCE is pending review.
            return LicenseStatus.UNREVIEWED
    else:
        # The project has at least one license and does not have
        # OTHER_PROPRIETARY or OTHER_OPEN_SOURCE as a license.
        return LicenseStatus.OPEN_SOURCE


class ProductWithLicenses:
    """Caches `Product.licenses`."""

    delegates(IProduct, 'product')

    def __init__(self, product, licenses):
        self.product = product
        self._licenses = licenses

    @property
    def licenses(self):
        """See `IProduct`."""
        return self._licenses

    @property
    def license_status(self):
        """See `IProduct`.

        Normally, the `Product.license_status` property would use
        `Product.licenses`, which is not cached, instead of
        `ProductWithLicenses.licenses`, which is cached.
        """
        return get_license_status(
            self.license_approved, self.license_reviewed, self.licenses)


class Product(SQLBase, BugTargetBase, MakesAnnouncements,
              HasSpecificationsMixin, HasSprintsMixin,
              KarmaContextMixin, BranchVisibilityPolicyMixin,
              QuestionTargetMixin, HasTranslationImportsMixin,
              HasAliasMixin, StructuralSubscriptionTargetMixin,
              HasMilestonesMixin, OfficialBugTagTargetMixin):

    """A Product."""

    implements(
        IFAQTarget, IHasBugSupervisor, IHasIcon, IHasLogo,
        IHasMugshot, ILaunchpadUsage, IProduct, IQuestionTarget,
        IStructuralSubscriptionTarget)

    _table = 'Product'

    project = ForeignKey(
        foreignKey="Project", dbName="project", notNull=False, default=None)
    owner = ForeignKey(
        foreignKey="Person",
        storm_validator=validate_public_person, dbName="owner", notNull=True)
    registrant = ForeignKey(
        foreignKey="Person",
        storm_validator=validate_public_person, dbName="registrant",
        notNull=True)
    bug_supervisor = ForeignKey(
        dbName='bug_supervisor', foreignKey='Person',
        storm_validator=validate_person_not_private_membership, notNull=False,
        default=None)
    security_contact = ForeignKey(
        dbName='security_contact', foreignKey='Person',
        storm_validator=validate_public_person, notNull=False,
        default=None)
    driver = ForeignKey(
        dbName="driver", foreignKey="Person",
        storm_validator=validate_public_person, notNull=False, default=None)
    name = StringCol(
        dbName='name', notNull=True, alternateID=True, unique=True)
    displayname = StringCol(dbName='displayname', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    summary = StringCol(dbName='summary', notNull=True)
    description = StringCol(notNull=False, default=None)
    datecreated = UtcDateTimeCol(
        dbName='datecreated', notNull=True, default=UTC_NOW)
    homepageurl = StringCol(dbName='homepageurl', notNull=False, default=None)
    homepage_content = StringCol(default=None)
    icon = ForeignKey(
        dbName='icon', foreignKey='LibraryFileAlias', default=None)
    logo = ForeignKey(
        dbName='logo', foreignKey='LibraryFileAlias', default=None)
    mugshot = ForeignKey(
        dbName='mugshot', foreignKey='LibraryFileAlias', default=None)
    screenshotsurl = StringCol(
        dbName='screenshotsurl', notNull=False, default=None)
    wikiurl =  StringCol(dbName='wikiurl', notNull=False, default=None)
    programminglang = StringCol(
        dbName='programminglang', notNull=False, default=None)
    downloadurl = StringCol(dbName='downloadurl', notNull=False, default=None)
    lastdoap = StringCol(dbName='lastdoap', notNull=False, default=None)
    translationgroup = ForeignKey(
        dbName='translationgroup', foreignKey='TranslationGroup',
        notNull=False, default=None)
    translationpermission = EnumCol(
        dbName='translationpermission', notNull=True,
        schema=TranslationPermission, default=TranslationPermission.OPEN)
    bugtracker = ForeignKey(
        foreignKey="BugTracker", dbName="bugtracker", notNull=False,
        default=None)
    official_answers = BoolCol(
        dbName='official_answers', notNull=True, default=False)
    official_blueprints = BoolCol(
        dbName='official_blueprints', notNull=True, default=False)
    official_codehosting = BoolCol(
        dbName='official_codehosting', notNull=True, default=False)
    official_malone = BoolCol(
        dbName='official_malone', notNull=True, default=False)
    official_rosetta = BoolCol(
        dbName='official_rosetta', notNull=True, default=False)
    remote_product = Unicode(
        name='remote_product', allow_none=True, default=None)

    def _getMilestoneCondition(self):
        """See `HasMilestonesMixin`."""
        return (Milestone.product == self)

    @property
    def official_anything(self):
        return True in (self.official_malone, self.official_rosetta,
                        self.official_blueprints, self.official_answers,
                        self.official_codehosting)

    enable_bug_expiration = BoolCol(dbName='enable_bug_expiration',
        notNull=True, default=False)
    active = BoolCol(dbName='active', notNull=True, default=True)
    license_reviewed = BoolCol(dbName='reviewed', notNull=True, default=False)
    reviewer_whiteboard = StringCol(notNull=False, default=None)
    private_bugs = BoolCol(
        dbName='private_bugs', notNull=True, default=False)
    autoupdate = BoolCol(dbName='autoupdate', notNull=True, default=False)
    freshmeatproject = StringCol(notNull=False, default=None)
    sourceforgeproject = StringCol(notNull=False, default=None)
    # While the interface defines this field as required, we need to
    # allow it to be NULL so we can create new product records before
    # the corresponding series records.
    development_focus = ForeignKey(
        foreignKey="ProductSeries", dbName="development_focus", notNull=False,
        default=None)
    bug_reporting_guidelines = StringCol(default=None)
    _cached_licenses = None

    def _validate_license_info(self, attr, value):
        if not self._SO_creating and value != self.license_info:
            # Clear the license_reviewed and license_approved flags
            # if the license changes.
            self._resetLicenseReview()
        return value

    license_info = StringCol(dbName='license_info', default=None,
                             storm_validator=_validate_license_info)

    def _validate_license_approved(self, attr, value):
        """Ensure license approved is only applied to the correct licenses."""
        # XXX: BradCrittenden 2008-07-16 Is the check for _SO_creating still
        # needed for storm?
        if not self._SO_creating:
            licenses = self.licenses
            if value:
                assert (
                    License.OTHER_OPEN_SOURCE in licenses and
                    License.OTHER_PROPRIETARY not in licenses), (
                    "Only licenses of 'Other/Open Source' and not "
                    "'Other/Proprietary' may be marked as license_approved.")
                # Approving a license implies it has been reviewed.  Force
                # `license_reviewed` to be True.
                self.license_reviewed = True
        return value

    license_approved = BoolCol(dbName='license_approved',
                               notNull=True, default=False,
                               storm_validator=_validate_license_approved)

    @cachedproperty('_commercial_subscription_cached')
    def commercial_subscription(self):
        return CommercialSubscription.selectOneBy(product=self)

    def redeemSubscriptionVoucher(self, voucher, registrant, purchaser,
                                  subscription_months, whiteboard=None,
                                  current_datetime=None):
        """See `IProduct`."""

        def add_months(start, num_months):
            """Given a start date find the new date `num_months` later.

            If the start date day is the last day of the month and the new
            month does not have that many days, then the new date will be the
            last day of the new month.  February is handled correctly too,
            including leap years, where th 28th-31st maps to the 28th or
            29th.
            """
            # The months are 1-indexed but the divmod calculation will only
            # work if it is 0-indexed.  Subtract 1 from the months and then
            # add it back to the new_month later.
            years, new_month = divmod(start.month - 1 + num_months, 12)
            new_month += 1
            new_year = start.year + years
            # If the day is not valid for the new month, make it the last day
            # of that month, e.g. 20080131 + 1 month = 20080229.
            weekday, days_in_month = calendar.monthrange(new_year, new_month)
            new_day = min(days_in_month, start.day)
            new_date = start.replace(year=new_year,
                                     month=new_month,
                                     day=new_day)
            return new_date

        if current_datetime is None:
            current_datetime = datetime.datetime.now(pytz.timezone('UTC'))

        if self.commercial_subscription is None:
            date_starts = current_datetime
            date_expires = add_months(date_starts, subscription_months)
            subscription = CommercialSubscription(
                product=self,
                date_starts=date_starts,
                date_expires=date_expires,
                registrant=registrant,
                purchaser=purchaser,
                sales_system_id=voucher,
                whiteboard=whiteboard)
            self._commercial_subscription_cached = subscription
        else:
            if current_datetime <= self.commercial_subscription.date_expires:
                # Extend current subscription.
                self.commercial_subscription.date_expires = (
                    add_months(self.commercial_subscription.date_expires,
                               subscription_months))
            else:
                # Start the new subscription now and extend for the new
                # period.
                self.commercial_subscription.date_starts = current_datetime
                self.commercial_subscription.date_expires = (
                    add_months(current_datetime, subscription_months))
            self.commercial_subscription.sales_system_id = voucher
            self.commercial_subscription.registrant = registrant
            self.commercial_subscription.purchaser = purchaser

    @property
    def qualifies_for_free_hosting(self):
        """See `IProduct`."""
        if self.license_approved:
            # The license was manually approved for free hosting.
            return True
        elif License.OTHER_PROPRIETARY in self.licenses:
            # Proprietary licenses need a subscription without
            # waiting for a review.
            return False
        elif (self.license_reviewed and
              (License.OTHER_OPEN_SOURCE in self.licenses or
               self.license_info not in ('', None))):
            # We only know that an unknown open source license
            # requires a subscription after we have reviewed it
            # when we have not set license_approved to True.
            return False
        elif len(self.licenses) == 0:
            # The owner needs to choose a license.
            return False
        else:
            # The project has only valid open source license(s).
            return True

    @property
    def commercial_subscription_is_due(self):
        """See `IProduct`.

        If True, display subscription warning to project owner.
        """
        if self.qualifies_for_free_hosting:
            return False
        elif (self.commercial_subscription is None
              or not self.commercial_subscription.is_active):
            # The project doesn't have an active subscription.
            return True
        else:
            warning_date = (self.commercial_subscription.date_expires
                            - datetime.timedelta(30))
            now = datetime.datetime.now(pytz.timezone('UTC'))
            if now > warning_date:
                # The subscription is close to being expired.
                return True
            else:
                # The subscription is good.
                return False

    @property
    def is_permitted(self):
        """See `IProduct`.

        If False, disable many tasks on this project.
        """
        if self.qualifies_for_free_hosting:
            # The project qualifies for free hosting.
            return True
        elif self.commercial_subscription is None:
            return False
        else:
            return self.commercial_subscription.is_active

    @property
    def license_status(self):
        """See `IProduct`.

        :return: A LicenseStatus enum value.
        """
        return get_license_status(
            self.license_approved, self.license_reviewed, self.licenses)

    def _resetLicenseReview(self):
        """When the license is modified, it must be reviewed again."""
        self.license_reviewed = False
        self.license_approved = False

    def __storm_invalidated__(self):
        """Clear cached non-storm attributes when the transaction ends."""
        self._cached_licenses = None
        if safe_hasattr(self, '_commercial_subscription_cached'):
            del self._commercial_subscription_cached

    def _getLicenses(self):
        """Get the licenses as a tuple."""
        if self._cached_licenses is None:
            product_licenses = ProductLicense.selectBy(
                product=self, orderBy='license')
            self._cached_licenses = tuple(
                product_license.license
                for product_license in product_licenses)
        return self._cached_licenses

    def _setLicenses(self, licenses, reset_license_reviewed=True):
        """Set the licenses from a tuple of license enums.

        The licenses parameter must not be an empty tuple.
        """
        licenses = set(licenses)
        old_licenses = set(self.licenses)
        if licenses == old_licenses:
            return
        # Clear the license_reviewed and license_approved flags
        # if the license changes.
        # ProductSet.createProduct() passes in reset_license_reviewed=False
        # to avoid changing the value when a Launchpad Admin sets
        # license_reviewed & licenses at the same time.
        if reset_license_reviewed:
            self._resetLicenseReview()
        # $product/+edit doesn't require a license if a license hasn't
        # already been set, but updateContextFromData() updates all the
        # fields, so we have to avoid this assertion when the attribute
        # isn't actually being changed.
        assert len(licenses) != 0, "licenses argument must not be empty"
        for license in licenses:
            if license not in License:
                raise AssertionError("%s is not a License" % license)

        for license in old_licenses.difference(licenses):
            product_license = ProductLicense.selectOneBy(product=self,
                                                         license=license)
            product_license.destroySelf()

        for license in licenses.difference(old_licenses):
            ProductLicense(product=self, license=license)
        self._cached_licenses = tuple(sorted(licenses))

    licenses = property(_getLicenses, _setLicenses)

    def _getBugTaskContextWhereClause(self):
        """See BugTargetBase."""
        return "BugTask.product = %d" % self.id

    def getExternalBugTracker(self):
        """See `IHasExternalBugTracker`."""
        if self.official_malone:
            return None
        elif self.bugtracker is not None:
            return self.bugtracker
        elif self.project is not None:
            return self.project.bugtracker
        else:
            return None

    def _customizeSearchParams(self, search_params):
        """Customize `search_params` for this product.."""
        search_params.setProduct(self)

    def getUsedBugTags(self):
        """See `IBugTarget`."""
        return get_bug_tags("BugTask.product = %s" % sqlvalues(self))

    def getUsedBugTagsWithOpenCounts(self, user):
        """See `IBugTarget`."""
        return get_bug_tags_open_count(BugTask.product == self, user)

    branches = SQLMultipleJoin('Branch', joinColumn='product',
        orderBy='id')
    serieses = SQLMultipleJoin('ProductSeries', joinColumn='product',
        orderBy='name')

    @property
    def name_with_project(self):
        """See lib.canonical.launchpad.interfaces.IProduct"""
        if self.project and self.project.name != self.name:
            return self.project.name + ": " + self.name
        return self.name

    @property
    def releases(self):
        return ProductRelease.select(
            AND(ProductRelease.q.productseriesID == ProductSeries.q.id,
                ProductSeries.q.productID == self.id),
            clauseTables=['ProductSeries'],
            orderBy=['version']
            )

    @property
    def drivers(self):
        """See `IProduct`."""
        drivers = set()
        drivers.add(self.driver)
        if self.project is not None:
            drivers.add(self.project.driver)
        drivers.discard(None)
        if len(drivers) == 0:
            if self.project is not None:
                drivers.add(self.project.owner)
            else:
                drivers.add(self.owner)
        return sorted(drivers, key=lambda driver: driver.browsername)

    bounties = SQLRelatedJoin(
        'Bounty', joinColumn='product', otherColumn='bounty',
        intermediateTable='ProductBounty')

    @property
    def sourcepackages(self):
        from canonical.launchpad.database.sourcepackage import SourcePackage
        clause = """ProductSeries.id=Packaging.productseries AND
                    ProductSeries.product = %s
                    """ % sqlvalues(self.id)
        clauseTables = ['ProductSeries']
        ret = Packaging.select(clause, clauseTables,
            prejoins=["sourcepackagename", "distroseries.distribution"])
        sps = [SourcePackage(sourcepackagename=r.sourcepackagename,
                             distroseries=r.distroseries) for r in ret]
        return sorted(sps, key=lambda x:
            (x.sourcepackagename.name, x.distroseries.name,
             x.distroseries.distribution.name))

    @property
    def distrosourcepackages(self):
        from canonical.launchpad.database.distributionsourcepackage \
            import DistributionSourcePackage
        clause = """ProductSeries.id=Packaging.productseries AND
                    ProductSeries.product = %s
                    """ % sqlvalues(self.id)
        clauseTables = ['ProductSeries']
        ret = Packaging.select(clause, clauseTables,
            prejoins=["sourcepackagename", "distroseries.distribution"])
        distros = set()
        dsps = []
        for packaging in ret:
            distro = packaging.distroseries.distribution
            if distro in distros:
                continue
            distros.add(distro)
            dsps.append(DistributionSourcePackage(
                sourcepackagename=packaging.sourcepackagename,
                distribution=distro))
        return sorted(dsps, key=lambda x:
            (x.sourcepackagename.name, x.distribution.name))

    @property
    def bugtargetdisplayname(self):
        """See IBugTarget."""
        return self.displayname

    @property
    def bugtargetname(self):
        """See `IBugTarget`."""
        return self.name

    def getLatestBranches(self, quantity=5, visible_by_user=None):
        """See `IProduct`."""
        return shortlist(
            BranchSet().getLatestBranchesForProduct(
                self, quantity, visible_by_user))

    def getPackage(self, distroseries):
        """See `IProduct`."""
        if isinstance(distroseries, Distribution):
            distroseries = distroseries.currentrelease
        for pkg in self.sourcepackages:
            if pkg.distroseries == distroseries:
                return pkg
        else:
            raise NotFoundError(distroseries)

    def getMilestone(self, name):
        """See `IProduct`."""
        return Milestone.selectOne("""
            product = %s AND
            name = %s
            """ % sqlvalues(self.id, name))

    def createBug(self, bug_params):
        """See `IBugTarget`."""
        bug_params.setBugTarget(product=self)
        return BugSet().createBug(bug_params)

    def _getBugTaskContextClause(self):
        """See BugTargetBase."""
        return 'BugTask.product = %s' % sqlvalues(self)

    def searchQuestions(self, search_text=None,
                        status=QUESTION_STATUS_DEFAULT_SEARCH,
                        language=None, sort=None, owner=None,
                        needs_attention_from=None, unsupported=False):
        """See `IQuestionCollection`."""
        if unsupported:
            unsupported_target = self
        else:
            unsupported_target = None

        return QuestionTargetSearch(
            product=self,
            search_text=search_text, status=status,
            language=language, sort=sort, owner=owner,
            needs_attention_from=needs_attention_from,
            unsupported_target=unsupported_target).getResults()

    def getTargetTypes(self):
        """See `QuestionTargetMixin`.

        Defines product as self.
        """
        return {'product': self}

    def newFAQ(self, owner, title, content, keywords=None, date_created=None):
        """See `IFAQTarget`."""
        return FAQ.new(
            owner=owner, title=title, content=content, keywords=keywords,
            date_created=date_created, product=self)

    def findSimilarFAQs(self, summary):
        """See `IFAQTarget`."""
        return FAQ.findSimilar(summary, product=self)

    def getFAQ(self, id):
        """See `IFAQCollection`."""
        return FAQ.getForTarget(id, self)

    def searchFAQs(self, search_text=None, owner=None, sort=None):
        """See `IFAQCollection`."""
        return FAQSearch(
            search_text=search_text, owner=owner, sort=sort,
            product=self).getResults()

    @property
    def translatable_packages(self):
        """See `IProduct`."""
        packages = set(package for package in self.sourcepackages
                       if len(package.getCurrentTranslationTemplates()) > 0)
        # Sort packages by distroseries.name and package.name
        return sorted(packages, key=lambda p: (p.distroseries.name, p.name))

    @property
    def translatable_series(self):
        """See `IProduct`."""
        translatable_product_series = set(
            product_series for product_series in self.serieses
            if len(product_series.getCurrentTranslationTemplates()) > 0)
        return sorted(
            translatable_product_series,
            key=operator.attrgetter('datecreated'))

    @property
    def obsolete_translatable_series(self):
        """See `IProduct`."""
        obsolete_product_series = set(
            product_series for product_series in self.serieses
            if len(product_series.getObsoleteTranslationTemplates()) > 0)
        return sorted(obsolete_product_series, key=lambda s: s.datecreated)

    @property
    def primary_translatable(self):
        """See `IProduct`."""
        packages = self.translatable_packages
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        targetseries = ubuntu.currentseries
        product_series = self.translatable_series

        # First, go with development focus branch
        if product_series and self.development_focus in product_series:
            return self.development_focus
        # Next, go with the latest product series that has templates:
        if product_series:
            return product_series[-1]
        # Otherwise, look for an Ubuntu package in the current distroseries:
        for package in packages:
            if package.distroseries == targetseries:
                return package
        # now let's make do with any ubuntu package
        for package in packages:
            if package.distribution == ubuntu:
                return package
        # or just any package
        if len(packages) > 0:
            return packages[0]
        # capitulate
        return None

    @property
    def mentoring_offers(self):
        """See `IProduct`"""
        via_specs = MentoringOffer.select("""
            Specification.product = %s AND
            Specification.id = MentoringOffer.specification
            """ % sqlvalues(self.id) + """ AND NOT
            (""" + Specification.completeness_clause +")",
            clauseTables=['Specification'],
            distinct=True)
        via_bugs = MentoringOffer.select("""
            BugTask.product = %s AND
            BugTask.bug = MentoringOffer.bug AND
            BugTask.bug = Bug.id AND
            Bug.private IS FALSE
            """ % sqlvalues(self.id) + """ AND NOT (
            """ + BugTask.completeness_clause + ")",
            clauseTables=['BugTask', 'Bug'],
            distinct=True)
        return via_specs.union(via_bugs, orderBy=['-date_created', '-id'])

    @property
    def translationgroups(self):
        tg = []
        if self.translationgroup:
            tg.append(self.translationgroup)
        if self.project:
            if self.project.translationgroup:
                if self.project.translationgroup not in tg:
                    tg.append(self.project.translationgroup)

    @property
    def aggregatetranslationpermission(self):
        perms = [self.translationpermission]
        if self.project:
            perms.append(self.project.translationpermission)
        # XXX Carlos Perello Marin 2005-06-02:
        # Reviewer please describe a better way to explicitly order
        # the enums. The spec describes the order, and the values make
        # it work, and there is space left for new values so we can
        # ensure a consistent sort order in future, but there should be
        # a better way.
        return max(perms)

    @property
    def has_any_specifications(self):
        """See `IHasSpecifications`."""
        return self.all_specifications.count()

    @property
    def all_specifications(self):
        return self.specifications(filter=[SpecificationFilter.ALL])

    @property
    def valid_specifications(self):
        return self.specifications(filter=[SpecificationFilter.VALID])

    def specifications(self, sort=None, quantity=None, filter=None,
                       prejoin_people=True):
        """See `IHasSpecifications`."""

        # Make a new list of the filter, so that we do not mutate what we
        # were passed as a filter
        if not filter:
            # filter could be None or [] then we decide the default
            # which for a product is to show incomplete specs
            filter = [SpecificationFilter.INCOMPLETE]

        # now look at the filter and fill in the unsaid bits

        # defaults for completeness: if nothing is said about completeness
        # then we want to show INCOMPLETE
        completeness = False
        for option in [
            SpecificationFilter.COMPLETE,
            SpecificationFilter.INCOMPLETE]:
            if option in filter:
                completeness = True
        if completeness is False:
            filter.append(SpecificationFilter.INCOMPLETE)

        # defaults for acceptance: in this case we have nothing to do
        # because specs are not accepted/declined against a distro

        # defaults for informationalness: we don't have to do anything
        # because the default if nothing is said is ANY

        # sort by priority descending, by default
        if sort is None or sort == SpecificationSort.PRIORITY:
            order = (
                ['-priority', 'Specification.definition_status',
                 'Specification.name'])
        elif sort == SpecificationSort.DATE:
            order = ['-Specification.datecreated', 'Specification.id']

        # figure out what set of specifications we are interested in. for
        # products, we need to be able to filter on the basis of:
        #
        #  - completeness.
        #  - informational.
        #
        base = 'Specification.product = %s' % self.id
        query = base
        # look for informational specs
        if SpecificationFilter.INFORMATIONAL in filter:
            query += (' AND Specification.implementation_status = %s' %
              quote(SpecificationImplementationStatus.INFORMATIONAL))

        # filter based on completion. see the implementation of
        # Specification.is_complete() for more details
        completeness =  Specification.completeness_clause

        if SpecificationFilter.COMPLETE in filter:
            query += ' AND ( %s ) ' % completeness
        elif SpecificationFilter.INCOMPLETE in filter:
            query += ' AND NOT ( %s ) ' % completeness

        # Filter for validity. If we want valid specs only then we should
        # exclude all OBSOLETE or SUPERSEDED specs
        if SpecificationFilter.VALID in filter:
            query += (' AND Specification.definition_status NOT IN '
                '( %s, %s ) ' % sqlvalues(
                    SpecificationDefinitionStatus.OBSOLETE,
                    SpecificationDefinitionStatus.SUPERSEDED))

        # ALL is the trump card
        if SpecificationFilter.ALL in filter:
            query = base

        # Filter for specification text
        for constraint in filter:
            if isinstance(constraint, basestring):
                # a string in the filter is a text search filter
                query += ' AND Specification.fti @@ ftq(%s) ' % quote(
                    constraint)

        results = Specification.select(query, orderBy=order, limit=quantity)
        if prejoin_people:
            results = results.prejoin(['assignee', 'approver', 'drafter'])
        return results

    def getSpecification(self, name):
        """See `ISpecificationTarget`."""
        return Specification.selectOneBy(product=self, name=name)

    def getSeries(self, name):
        """See `IProduct`."""
        return ProductSeries.selectOneBy(product=self, name=name)

    def newSeries(self, owner, name, summary, branch=None):
        # XXX: jamesh 2008-04-11
        # Set the ID of the new ProductSeries to avoid flush order
        # loops in ProductSet.createProduct()
        return ProductSeries(productID=self.id, owner=owner, name=name,
                             summary=summary, user_branch=branch)

    def getRelease(self, version):
        return ProductRelease.selectOne("""
            ProductRelease.productseries = ProductSeries.id AND
            ProductSeries.product = %s AND
            ProductRelease.version = %s
            """ % sqlvalues(self.id, version),
            clauseTables=['ProductSeries'])

    def packagedInDistros(self):
        distros = Distribution.select(
            "Packaging.productseries = ProductSeries.id AND "
            "ProductSeries.product = %s AND "
            "Packaging.distroseries = DistroSeries.id AND "
            "DistroSeries.distribution = Distribution.id"
            "" % sqlvalues(self.id),
            clauseTables=['Packaging', 'ProductSeries', 'DistroSeries'],
            orderBy='name',
            distinct=True
            )
        return distros

    def ensureRelatedBounty(self, bounty):
        """See `IProduct`."""
        for curr_bounty in self.bounties:
            if bounty.id == curr_bounty.id:
                return None
        ProductBounty(product=self, bounty=bounty)
        return None

    def setBugSupervisor(self, bug_supervisor, user):
        """See `IHasBugSupervisor`."""
        self.bug_supervisor = bug_supervisor
        if bug_supervisor is not None:
            subscription = self.addBugSubscription(bug_supervisor, user)

    def getCustomLanguageCode(self, language_code):
        """See `IProduct`."""
        return CustomLanguageCode.selectOneBy(
            product=self, language_code=language_code)

    def getMergeProposals(self, status=None, visible_by_user=None):
        """See `IProduct`."""
        if status is None:
            status = (
                BranchMergeProposalStatus.CODE_APPROVED,
                BranchMergeProposalStatus.NEEDS_REVIEW,
                BranchMergeProposalStatus.WORK_IN_PROGRESS)

        return getUtility(IBranchMergeProposalGetter).getProposalsForContext(
            self, status, visible_by_user=visible_by_user)


    def userCanEdit(self, user):
        """See `IProduct`."""
        if user is None:
            return False
        celebs = getUtility(ILaunchpadCelebrities)
        return (
            user.inTeam(celebs.registry_experts) or
            user.inTeam(celebs.admin) or
            user.inTeam(self.owner))

    def getLinkedBugWatches(self):
        """See `IProduct`."""
        store = Store.of(self)
        return store.find(
            BugWatch,
            And(self == BugTask.product,
                BugTask.bugwatch == BugWatch.id,
                BugWatch.bugtracker == self.getExternalBugTracker()))


class ProductSet:
    implements(IProductSet)

    def __init__(self):
        self.title = "Projects in Launchpad"

    def __getitem__(self, name):
        """See `IProductSet`."""
        product = self.getByName(name=name, ignore_inactive=True)
        if product is None:
            raise NotFoundError(name)
        return product

    def __iter__(self):
        """See `IProductSet`."""
        return iter(self.all_active)

    @property
    def people(self):
        return getUtility(IPersonSet)

    def latest(self, quantity=5):
        if quantity is None:
            return self.all_active
        else:
            return self.all_active[:quantity]

    @property
    def all_active(self):
        results = Product.selectBy(
            active=True, orderBy="-Product.datecreated")
        # The main product listings include owner, so we prejoin it.
        return results.prejoin(["owner"])

    def get(self, productid):
        """See `IProductSet`."""
        try:
            return Product.get(productid)
        except SQLObjectNotFound:
            raise NotFoundError("Product with ID %s does not exist" %
                                str(productid))

    def getByName(self, name, ignore_inactive=False):
        """See `IProductSet`."""
        pillar = getUtility(IPillarNameSet).getByName(name, ignore_inactive)
        if not IProduct.providedBy(pillar):
            return None
        return pillar

    def getProductsWithBranches(self, num_products=None):
        """See `IProductSet`."""
        results = Product.select('''
            Product.id in (
                select distinct(product) from Branch
                where lifecycle_status in %s)
            and Product.active
            ''' % sqlvalues(DEFAULT_BRANCH_STATUS_IN_LISTING),
            orderBy='name')
        if num_products is not None:
            results = results.limit(num_products)
        return results

    def createProduct(self, owner, name, displayname, title, summary,
                      description=None, project=None, homepageurl=None,
                      screenshotsurl=None, wikiurl=None,
                      downloadurl=None, freshmeatproject=None,
                      sourceforgeproject=None, programminglang=None,
                      license_reviewed=False, mugshot=None, logo=None,
                      icon=None, licenses=None, license_info=None,
                      registrant=None):
        """See `IProductSet`."""
        if registrant is None:
            registrant = owner
        if licenses is None:
            licenses = sets.Set()
        product = Product(
            owner=owner, registrant=registrant, name=name,
            displayname=displayname, title=title, project=project,
            summary=summary, description=description, homepageurl=homepageurl,
            screenshotsurl=screenshotsurl, wikiurl=wikiurl,
            downloadurl=downloadurl, freshmeatproject=freshmeatproject,
            sourceforgeproject=sourceforgeproject,
            programminglang=programminglang,
            license_reviewed=license_reviewed,
            icon=icon, logo=logo, mugshot=mugshot, license_info=license_info)

        if len(licenses) > 0:
            product._setLicenses(licenses, reset_license_reviewed=False)

        # Create a default trunk series and set it as the development focus
        trunk = product.newSeries(
            owner, 'trunk',
            ('The "trunk" series represents the primary line of development '
             'rather than a stable release branch. This is sometimes also '
             'called MAIN or HEAD.'))
        product.development_focus = trunk

        return product

    def forReview(self, search_text=None, active=None,
                  license_reviewed=None, licenses=None,
                  license_info_is_empty=None,
                  has_zero_licenses=None,
                  created_after=None, created_before=None,
                  subscription_expires_after=None,
                  subscription_expires_before=None,
                  subscription_modified_after=None,
                  subscription_modified_before=None):
        """See canonical.launchpad.interfaces.product.IProductSet."""

        conditions = []

        if license_reviewed is not None:
            conditions.append('Product.reviewed = %s'
                              % sqlvalues(license_reviewed))

        if active is not None:
            conditions.append('Product.active = %s' % sqlvalues(active))

        if search_text is not None and search_text.strip() != '':
            conditions.append('Product.fti @@ ftq(%s)'
                              % sqlvalues(search_text))

        if created_after is not None:
            conditions.append('Product.datecreated >= %s'
                              % sqlvalues(created_after))
        if created_before is not None:
            conditions.append('Product.datecreated <= %s'
                              % sqlvalues(created_before))

        needs_join = False
        if subscription_expires_after is not None:
            conditions.append('CommercialSubscription.date_expires >= %s'
                              % sqlvalues(subscription_expires_after))
            needs_join = True
        if subscription_expires_before is not None:
            conditions.append('CommercialSubscription.date_expires <= %s'
                              % sqlvalues(subscription_expires_before))
            needs_join = True

        if subscription_modified_after is not None:
            conditions.append(
                'CommercialSubscription.date_last_modified >= %s'
                % sqlvalues(subscription_modified_after))
            needs_join = True
        if subscription_modified_before is not None:
            conditions.append(
                'CommercialSubscription.date_last_modified <= %s'
                % sqlvalues(subscription_modified_before))
            needs_join = True

        clause_tables = []
        if needs_join:
            conditions.append(
                'CommercialSubscription.product = Product.id')
            clause_tables.append('CommercialSubscription')

        or_conditions = []
        if license_info_is_empty is True:
            # Match products whose license_info doesn't contain
            # any non-space characters.
            or_conditions.append("Product.license_info IS NULL")
            or_conditions.append(r"Product.license_info ~ E'^\\s*$'")
        elif license_info_is_empty is False:
            # license_info contains something besides spaces.
            or_conditions.append(r"Product.license_info ~ E'[^\\s]'")
        elif license_info_is_empty is None:
            # Don't restrict result if license_info_is_empty is None.
            pass
        else:
            raise AssertionError('license_info_is_empty invalid: %r'
                                 % license_info_is_empty)

        has_license_subquery = '''%s (
            SELECT 1
            FROM ProductLicense
            WHERE ProductLicense.product = Product.id
            LIMIT 1
            )
            '''
        if has_zero_licenses is True:
            # The subquery finds zero rows.
            or_conditions.append(has_license_subquery % 'NOT EXISTS')
        elif has_zero_licenses is False:
            # The subquery finds at least one row.
            or_conditions.append(has_license_subquery % 'EXISTS')
        elif has_zero_licenses is None:
            # Don't restrict results if has_zero_licenses is None.
            pass
        else:
            raise AssertionError('has_zero_licenses is invalid: %r'
                                 % has_zero_licenses)

        if licenses is not None and len(licenses) > 0:
            or_conditions.append('''EXISTS (
                SELECT 1
                FROM ProductLicense
                WHERE ProductLicense.product = Product.id
                    AND license IN %s
                LIMIT 1
                )
                ''' % sqlvalues(tuple(licenses)))

        if len(or_conditions) != 0:
            conditions.append('(%s)' % '\nOR '.join(or_conditions))

        conditions_string = '\nAND '.join(conditions)
        result = Product.select(
            conditions_string, clauseTables=clause_tables,
            orderBy=['displayname', 'name'], distinct=True)
        return result

    def search(self, text=None, soyuz=None,
               rosetta=None, malone=None,
               bazaar=None,
               show_inactive=False):
        """See canonical.launchpad.interfaces.product.IProductSet."""
        # XXX: kiko 2006-03-22: The soyuz argument is unused.
        clauseTables = set()
        clauseTables.add('Product')
        queries = []
        if text:
            queries.append("Product.fti @@ ftq(%s) " % sqlvalues(text))
        if rosetta:
            clauseTables.add('POTemplate')
            clauseTables.add('ProductRelease')
            clauseTables.add('ProductSeries')
            queries.append("POTemplate.productrelease=ProductRelease.id")
            queries.append("ProductRelease.productseries=ProductSeries.id")
            queries.append("ProductSeries.product=product.id")
        if malone:
            clauseTables.add('BugTask')
            queries.append('BugTask.product=Product.id')
        if bazaar:
            clauseTables.add('ProductSeries')
            queries.append('(ProductSeries.import_branch IS NOT NULL OR '
                           'ProductSeries.user_branch IS NOT NULL)')
        if 'ProductSeries' in clauseTables:
            queries.append('ProductSeries.product=Product.id')
        if not show_inactive:
            queries.append('Product.active IS TRUE')
        query = " AND ".join(queries)
        return Product.select(query, distinct=True,
                              prejoins=["owner"],
                              clauseTables=clauseTables)

    def getTranslatables(self):
        """See `IProductSet`"""
        upstream = Product.select('''
            Product.active AND
            Product.id = ProductSeries.product AND
            POTemplate.productseries = ProductSeries.id AND
            Product.official_rosetta
            ''',
            clauseTables=['ProductSeries', 'POTemplate'],
            orderBy='Product.title',
            distinct=True)
        return upstream.prejoin(['owner'])

    def featuredTranslatables(self, maximumproducts=8):
        """See `IProductSet`"""
        return Product.select('''
            id IN (
                SELECT DISTINCT product_id AS id
                FROM (
                    SELECT Product.id AS product_id, random() AS place
                    FROM Product
                    JOIN ProductSeries ON
                        ProductSeries.Product = Product.id
                    JOIN POTemplate ON
                        POTemplate.productseries = ProductSeries.id
                    WHERE Product.active AND Product.official_rosetta
                    ORDER BY place
                ) AS randomized_products
                LIMIT %s
            )
            ''' % quote(maximumproducts),
            distinct=True,
            orderBy='Product.title')

    @cachedproperty
    def stats(self):
        return getUtility(ILaunchpadStatisticSet)

    def count_all(self):
        return self.stats.value('active_products')

    def count_translatable(self):
        return self.stats.value('products_with_translations')

    def count_reviewed(self):
        return self.stats.value('reviewed_products')

    def count_buggy(self):
        return self.stats.value('projects_with_bugs')

    def count_featureful(self):
        return self.stats.value('products_with_blueprints')

    def count_answered(self):
        return self.stats.value('products_with_questions')

    def count_codified(self):
        return self.stats.value('products_with_branches')

    def getProductsWithNoneRemoteProduct(self, bugtracker_type=None):
        """See `IProductSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        conditions = [Product.remote_product == None]
        if bugtracker_type is not None:
            conditions.extend([
                Product.bugtracker == BugTracker.id,
                BugTracker.bugtrackertype == bugtracker_type,
                ])
        return store.find(Product, And(*conditions))

    def getSFLinkedProductsWithNoneRemoteProduct(self):
        """See `IProductSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        conditions = And(
            Product.remote_product == None,
            Product.sourceforgeproject != None)

        return store.find(Product, conditions)
