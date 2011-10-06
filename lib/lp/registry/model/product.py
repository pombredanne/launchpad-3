# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
# pylint: disable-msg=E0611,W0212

"""Database classes including and related to Product."""

__metaclass__ = type
__all__ = [
    'Product',
    'ProductSet',
    'ProductWithLicenses',
    ]


import calendar
import datetime
import httplib
import operator

from lazr.delegates import delegates
from lazr.lifecycle.event import ObjectModifiedEvent
from lazr.lifecycle.snapshot import Snapshot
from lazr.restful.declarations import error_status
from lazr.restful.utils import safe_hasattr
import pytz
from sqlobject import (
    BoolCol,
    ForeignKey,
    SQLMultipleJoin,
    SQLObjectNotFound,
    StringCol,
    )
from storm.expr import (
    LeftJoin,
    NamedFunc,
    )
from storm.locals import (
    And,
    Desc,
    Int,
    Join,
    Not,
    Or,
    Select,
    SQL,
    Store,
    Unicode,
    )
from zope.component import getUtility
from zope.event import notify
from zope.interface import (
    implements,
    providedBy,
    )
from zope.security.proxy import removeSecurityProxy

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import (
    quote,
    SQLBase,
    sqlvalues,
    )
from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet,
    )
from canonical.launchpad.interfaces.launchpad import (
    IHasIcon,
    IHasLogo,
    IHasMugshot,
    )
from canonical.launchpad.interfaces.launchpadstatistic import (
    ILaunchpadStatisticSet,
    )
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from lp.answers.enums import QUESTION_STATUS_DEFAULT_SEARCH
from lp.answers.interfaces.faqtarget import IFAQTarget
from lp.answers.model.faq import (
    FAQ,
    FAQSearch,
    )
from lp.answers.model.question import (
    QuestionTargetMixin,
    QuestionTargetSearch,
    )
from lp.app.enums import (
    service_uses_launchpad,
    ServiceUsage,
    )
from lp.app.errors import NotFoundError
from lp.app.interfaces.launchpad import (
    ILaunchpadCelebrities,
    ILaunchpadUsage,
    IServiceUsage,
    )
from lp.blueprints.enums import (
    SpecificationDefinitionStatus,
    SpecificationFilter,
    SpecificationImplementationStatus,
    )
from lp.blueprints.model.specification import (
    HasSpecificationsMixin,
    Specification,
    )
from lp.blueprints.model.sprint import HasSprintsMixin
from lp.bugs.interfaces.bugsummary import IBugSummaryDimension
from lp.bugs.interfaces.bugsupervisor import IHasBugSupervisor
from lp.bugs.interfaces.bugtarget import IHasBugHeat
from lp.bugs.interfaces.bugtaskfilter import OrderedBugTask
from lp.bugs.model.bug import (
    BugSet,
    get_bug_tags,
    )
from lp.bugs.model.bugtarget import (
    BugTargetBase,
    HasBugHeatMixin,
    OfficialBugTagTargetMixin,
    )
from lp.bugs.model.bugtask import BugTask
from lp.bugs.model.bugtracker import BugTracker
from lp.bugs.model.bugwatch import BugWatch
from lp.bugs.model.structuralsubscription import (
    StructuralSubscriptionTargetMixin,
    )
from lp.code.enums import BranchType
from lp.code.interfaces.branch import DEFAULT_BRANCH_STATUS_IN_LISTING
from lp.code.model.branchvisibilitypolicy import BranchVisibilityPolicyMixin
from lp.code.model.hasbranches import (
    HasBranchesMixin,
    HasCodeImportsMixin,
    HasMergeProposalsMixin,
    )
from lp.code.model.sourcepackagerecipe import SourcePackageRecipe
from lp.code.model.sourcepackagerecipedata import SourcePackageRecipeData
from lp.registry.interfaces.person import (
    IPersonSet,
    validate_person,
    validate_public_person,
    )
from lp.registry.interfaces.pillar import IPillarNameSet
from lp.registry.interfaces.product import (
    IProduct,
    IProductSet,
    License,
    LicenseStatus,
    )
from lp.registry.model.announcement import MakesAnnouncements
from lp.registry.model.commercialsubscription import CommercialSubscription
from lp.registry.model.distribution import Distribution
from lp.registry.model.distroseries import DistroSeries
from lp.registry.model.hasdrivers import HasDriversMixin
from lp.registry.model.karma import KarmaContextMixin
from lp.registry.model.milestone import (
    HasMilestonesMixin,
    Milestone,
    )
from lp.registry.model.packaging import Packaging
from lp.registry.model.person import Person
from lp.registry.model.pillar import HasAliasMixin
from lp.registry.model.productlicense import ProductLicense
from lp.registry.model.productrelease import ProductRelease
from lp.registry.model.productseries import ProductSeries
from lp.registry.model.series import ACTIVE_STATUSES
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.services.database import bulk
from lp.services.propertycache import (
    cachedproperty,
    get_property_cache,
    )
from lp.translations.enums import TranslationPermission
from lp.translations.interfaces.customlanguagecode import (
    IHasCustomLanguageCodes,
    )
from lp.translations.model.customlanguagecode import (
    CustomLanguageCode,
    HasCustomLanguageCodesMixin,
    )
from lp.translations.model.hastranslationimports import (
    HasTranslationImportsMixin,
    )
from lp.translations.model.potemplate import POTemplate
from lp.translations.model.translationpolicy import TranslationPolicyMixin


def get_license_status(license_approved, project_reviewed, licenses):
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
        if project_reviewed:
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


class Array(NamedFunc):
    """Implements the postgres "array" function in Storm."""
    name = 'array'


class ProductWithLicenses:
    """Caches `Product.licenses`."""

    delegates(IProduct, 'product')

    def __init__(self, product, license_ids):
        """Initialize a `ProductWithLicenses`.

        :param product: the `Product` to wrap.
        :param license_ids: a sequence of numeric `License` ids.
        """
        self.product = product
        self._licenses = tuple([
            License.items[id] for id in sorted(license_ids)])

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
        naked_product = removeSecurityProxy(self.product)
        return get_license_status(
            naked_product.license_approved, naked_product.project_reviewed,
            self.licenses)

    @classmethod
    def composeLicensesColumn(cls, for_class=None):
        """Compose a Storm column specification for licenses.

        Use this to render a list of `Product` linkes without querying
        licenses for each one individually.

        It lets you prefetch the licensing information in the same
        query that fetches a `Product`.  Just add the column spec
        returned by this function to the query, and pass it to the
        `ProductWithLicenses` constructor:

        license_column = ProductWithLicenses.composeLicensesColumn()
        products_with_licenses = [
            ProductWithLicenses(product, licenses)
            for product, licenses in store.find(Product, license_column)
            ]

        :param for_class: Class to find licenses for.  Defaults to
            `Product`, but could also be a Storm `ClassAlias`.
        """
        if for_class is None:
            for_class = Product

        return Array(
            Select(
                columns=[ProductLicense.license],
                where=(ProductLicense.product == for_class.id),
                tables=[ProductLicense]))


@error_status(httplib.BAD_REQUEST)
class UnDeactivateable(Exception):
    """Raised when a project is requested to deactivate but can not."""

    def __init__(self, msg):
        super(UnDeactivateable, self).__init__(msg)


class Product(SQLBase, BugTargetBase, MakesAnnouncements,
              HasDriversMixin, HasSpecificationsMixin, HasSprintsMixin,
              KarmaContextMixin, BranchVisibilityPolicyMixin,
              QuestionTargetMixin, HasTranslationImportsMixin,
              HasAliasMixin, StructuralSubscriptionTargetMixin,
              HasMilestonesMixin, OfficialBugTagTargetMixin, HasBranchesMixin,
              HasCustomLanguageCodesMixin, HasMergeProposalsMixin,
              HasBugHeatMixin, HasCodeImportsMixin, TranslationPolicyMixin):
    """A Product."""

    implements(
        IBugSummaryDimension, IFAQTarget, IHasBugHeat, IHasBugSupervisor,
        IHasCustomLanguageCodes, IHasIcon, IHasLogo, IHasMugshot,
        ILaunchpadUsage, IProduct, IServiceUsage)

    _table = 'Product'

    project = ForeignKey(
        foreignKey="ProjectGroup", dbName="project", notNull=False,
        default=None)
    _owner = ForeignKey(
        dbName="owner", foreignKey="Person",
        storm_validator=validate_person,
        notNull=True)
    registrant = ForeignKey(
        dbName="registrant", foreignKey="Person",
        storm_validator=validate_public_person,
        notNull=True)
    bug_supervisor = ForeignKey(
        dbName='bug_supervisor', foreignKey='Person',
        storm_validator=validate_person,
        notNull=False,
        default=None)
    security_contact = ForeignKey(
        dbName='security_contact', foreignKey='Person',
        storm_validator=validate_public_person, notNull=False,
        default=None)
    driver = ForeignKey(
        dbName="driver", foreignKey="Person",
        storm_validator=validate_person,
        notNull=False, default=None)
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
    wikiurl = StringCol(dbName='wikiurl', notNull=False, default=None)
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
    translation_focus = ForeignKey(
        dbName='translation_focus', foreignKey='ProductSeries',
        notNull=False, default=None)
    bugtracker = ForeignKey(
        foreignKey="BugTracker", dbName="bugtracker", notNull=False,
        default=None)
    official_answers = BoolCol(
        dbName='official_answers', notNull=True, default=False)
    official_blueprints = BoolCol(
        dbName='official_blueprints', notNull=True, default=False)
    official_malone = BoolCol(
        dbName='official_malone', notNull=True, default=False)
    official_rosetta = BoolCol(
        dbName='official_rosetta', notNull=True, default=False)
    remote_product = Unicode(
        name='remote_product', allow_none=True, default=None)
    max_bug_heat = Int()
    date_next_suggest_packaging = UtcDateTimeCol(default=None)

    @property
    def pillar(self):
        """See `IBugTarget`."""
        return self

    @property
    def pillar_category(self):
        """See `IPillar`."""
        return "Project"

    @property
    def official_codehosting(self):
        # XXX Need to remove official_codehosting column from Product
        # table.
        return self.development_focus.branch is not None

    @property
    def official_anything(self):
        return True in (self.official_malone, self.official_rosetta,
                        self.official_blueprints, self.official_answers,
                        self.official_codehosting)

    _answers_usage = EnumCol(
        dbName="answers_usage", notNull=True,
        schema=ServiceUsage,
        default=ServiceUsage.UNKNOWN)
    _blueprints_usage = EnumCol(
        dbName="blueprints_usage", notNull=True,
        schema=ServiceUsage,
        default=ServiceUsage.UNKNOWN)
    _translations_usage = EnumCol(
        dbName="translations_usage", notNull=True,
        schema=ServiceUsage,
        default=ServiceUsage.UNKNOWN)

    @property
    def codehosting_usage(self):
        if self.development_focus.branch is None:
            return ServiceUsage.UNKNOWN
        elif self.development_focus.branch.branch_type == BranchType.HOSTED:
            return ServiceUsage.LAUNCHPAD
        elif self.development_focus.branch.branch_type in (
            BranchType.MIRRORED,
            BranchType.REMOTE,
            BranchType.IMPORTED):
            return ServiceUsage.EXTERNAL
        return ServiceUsage.NOT_APPLICABLE

    @property
    def bug_tracking_usage(self):
        if self.official_malone:
            return ServiceUsage.LAUNCHPAD
        elif self.bugtracker is None:
            return ServiceUsage.UNKNOWN
        else:
            return ServiceUsage.EXTERNAL

    @property
    def uses_launchpad(self):
        """Does this distribution actually use Launchpad?"""
        return ServiceUsage.LAUNCHPAD in (self.answers_usage,
                                          self.blueprints_usage,
                                          self.translations_usage,
                                          self.codehosting_usage,
                                          self.bug_tracking_usage)

    def _getMilestoneCondition(self):
        """See `HasMilestonesMixin`."""
        return (Milestone.product == self)

    enable_bug_expiration = BoolCol(dbName='enable_bug_expiration',
        notNull=True, default=False)
    project_reviewed = BoolCol(dbName='reviewed', notNull=True, default=False)
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
    bug_reported_acknowledgement = StringCol(default=None)
    enable_bugfiling_duplicate_search = BoolCol(notNull=True, default=True)

    def _validate_active(self, attr, value):
        # Validate deactivation.
        if self.active == True and value == False:
            if len(self.sourcepackages) > 0:
                raise UnDeactivateable(
                    'This project cannot be deactivated since it is '
                    'linked to source packages.')
        return value

    active = BoolCol(dbName='active', notNull=True, default=True,
                     storm_validator=_validate_active)

    def _validate_license_info(self, attr, value):
        if not self._SO_creating and value != self.license_info:
            # Clear the project_reviewed and license_approved flags
            # if the license changes.
            self._resetLicenseReview()
        return value

    license_info = StringCol(dbName='license_info', default=None,
                             storm_validator=_validate_license_info)

    def _validate_license_approved(self, attr, value):
        """Ensure license approved is only applied to the correct licenses."""
        if not self._SO_creating:
            licenses = list(self.licenses)
            if value:
                if (License.OTHER_PROPRIETARY in licenses
                    or [License.DONT_KNOW] == licenses):
                    raise ValueError(
                        "Projects without a license or have "
                        "'Other/Proprietary' may not be approved.")
                # Approving a license implies it has been reviewed.  Force
                # `project_reviewed` to be True.
                self.project_reviewed = True
        return value

    license_approved = BoolCol(dbName='license_approved',
                               notNull=True, default=False,
                               storm_validator=_validate_license_approved)

    @cachedproperty
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
            get_property_cache(self).commercial_subscription = subscription
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
        elif (self.project_reviewed and
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
            self.license_approved, self.project_reviewed, self.licenses)

    def _resetLicenseReview(self):
        """When the license is modified, it must be reviewed again."""
        self.project_reviewed = False
        self.license_approved = False

    def _get_answers_usage(self):
        if self._answers_usage != ServiceUsage.UNKNOWN:
            # If someone has set something with the enum, use it.
            return self._answers_usage
        elif self.official_answers:
            return ServiceUsage.LAUNCHPAD
        return self._answers_usage

    def _set_answers_usage(self, val):
        self._answers_usage = val
        if val == ServiceUsage.LAUNCHPAD:
            self.official_answers = True
        else:
            self.official_answers = False

    answers_usage = property(
        _get_answers_usage,
        _set_answers_usage,
        doc="Indicates if the product uses the answers service.")

    def _get_blueprints_usage(self):
        if self._blueprints_usage != ServiceUsage.UNKNOWN:
            # If someone has set something with the enum, use it.
            return self._blueprints_usage
        elif self.official_blueprints:
            return ServiceUsage.LAUNCHPAD
        return self._blueprints_usage

    def _set_blueprints_usage(self, val):
        self._blueprints_usage = val
        if val == ServiceUsage.LAUNCHPAD:
            self.official_blueprints = True
        else:
            self.official_blueprints = False

    blueprints_usage = property(
        _get_blueprints_usage,
        _set_blueprints_usage,
        doc="Indicates if the product uses the blueprints service.")

    def _get_translations_usage(self):
        if self._translations_usage != ServiceUsage.UNKNOWN:
            # If someone has set something with the enum, use it.
            return self._translations_usage
        elif self.official_rosetta:
            return ServiceUsage.LAUNCHPAD
        return self._translations_usage

    def _set_translations_usage(self, val):
        self._translations_usage = val
        if val == ServiceUsage.LAUNCHPAD:
            self.official_rosetta = True
        else:
            self.official_rosetta = False

    translations_usage = property(
        _get_translations_usage,
        _set_translations_usage,
        doc="Indicates if the product uses the translations service.")

    @cachedproperty
    def _cached_licenses(self):
        """Get the licenses as a tuple."""
        product_licenses = ProductLicense.selectBy(
            product=self, orderBy='license')
        return tuple(
            product_license.license
            for product_license in product_licenses)

    def _getLicenses(self):
        return self._cached_licenses

    def _setLicenses(self, licenses, reset_project_reviewed=True):
        """Set the licenses from a tuple of license enums.

        The licenses parameter must not be an empty tuple.
        """
        licenses = set(licenses)
        old_licenses = set(self.licenses)
        if licenses == old_licenses:
            return
        # Clear the project_reviewed and license_approved flags
        # if the license changes.
        # ProductSet.createProduct() passes in reset_project_reviewed=False
        # to avoid changing the value when a Launchpad Admin sets
        # project_reviewed & licenses at the same time.
        if reset_project_reviewed:
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
        get_property_cache(self)._cached_licenses = tuple(sorted(licenses))

    licenses = property(_getLicenses, _setLicenses)

    def _getOwner(self):
        """Get the owner."""
        return self._owner

    def _setOwner(self, new_owner):
        """Set the owner.

        Send an IObjectModifiedEvent to notify subscribers that the owner
        changed.
        """
        if self.owner is None:
            # This is being initialized.
            self._owner = new_owner
        elif self.owner != new_owner:
            old_product = Snapshot(self, providing=providedBy(self))
            self._owner = new_owner
            notify(ObjectModifiedEvent(
                self, object_before_modification=old_product,
                edited_fields=['_owner']))
        else:
            # The new owner is the same as the current owner.
            pass

    owner = property(_getOwner, _setOwner)

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

    series = SQLMultipleJoin('ProductSeries', joinColumn='product',
        orderBy='name')

    @property
    def active_or_packaged_series(self):
        store = Store.of(self)
        tables = [
            ProductSeries,
            LeftJoin(Packaging, Packaging.productseries == ProductSeries.id),
            ]
        result = store.using(*tables).find(
            ProductSeries,
            ProductSeries.product == self,
            Or(ProductSeries.status.is_in(ACTIVE_STATUSES),
               Packaging.id != None))
        result = result.order_by(Desc(ProductSeries.name))
        result.config(distinct=True)
        return result

    @property
    def packagings(self):
        store = Store.of(self)
        result = store.find(
            (Packaging, DistroSeries),
            Packaging.distroseries == DistroSeries.id,
            Packaging.productseries == ProductSeries.id,
            ProductSeries.product == self)
        result = result.order_by(
            DistroSeries.version, ProductSeries.name, Packaging.id)

        def decorate(row):
            packaging, distroseries = row
            return packaging
        return DecoratedResultSet(result, decorate)

    @property
    def name_with_project(self):
        """See lib.canonical.launchpad.interfaces.IProduct"""
        if self.project and self.project.name != self.name:
            return self.project.name + ": " + self.name
        return self.name

    @property
    def releases(self):
        store = Store.of(self)
        origin = [
            ProductRelease,
            Join(Milestone, ProductRelease.milestone == Milestone.id),
            ]
        result = store.using(*origin)
        result = result.find(ProductRelease, Milestone.product == self)
        return result.order_by(Milestone.name)

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
        return sorted(drivers, key=lambda driver: driver.displayname)

    @property
    def sourcepackages(self):
        from lp.registry.model.sourcepackage import SourcePackage
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

    @cachedproperty
    def distrosourcepackages(self):
        from lp.registry.model.distributionsourcepackage import (
            DistributionSourcePackage,
            )
        store = IStore(Packaging)
        origin = [
            Packaging,
            Join(SourcePackageName,
                 Packaging.sourcepackagename == SourcePackageName.id),
            Join(ProductSeries, Packaging.productseries == ProductSeries.id),
            Join(DistroSeries, Packaging.distroseries == DistroSeries.id),
            Join(Distribution, DistroSeries.distribution == Distribution.id),
            ]
        result = store.using(*origin).find(
            (SourcePackageName, Distribution),
            ProductSeries.product == self)
        result = result.order_by(SourcePackageName.name, Distribution.name)
        result.config(distinct=True)

        return [
            DistributionSourcePackage(
                sourcepackagename=sourcepackagename,
                distribution=distro)
            for sourcepackagename, distro in result]

    @cachedproperty
    def ubuntu_packages(self):
        """The Ubuntu `IDistributionSourcePackage`s linked to the `IProduct`.
        """
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        return [
            package for package in self.distrosourcepackages
            if package.distribution == ubuntu]

    @property
    def bugtargetdisplayname(self):
        """See IBugTarget."""
        return self.displayname

    @property
    def bugtargetname(self):
        """See `IBugTarget`."""
        return self.name

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

    def getBugSummaryContextWhereClause(self):
        """See BugTargetBase."""
        # Circular fail.
        from lp.bugs.model.bugsummary import BugSummary
        return BugSummary.product_id == self.id

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
        packages = set(
            package
            for package in self.sourcepackages
            if package.has_current_translation_templates)

        # Sort packages by distroseries.name and package.name
        return sorted(packages, key=lambda p: (p.distroseries.name, p.name))

    @property
    def translatable_series(self):
        """See `IProduct`."""
        if not service_uses_launchpad(self.translations_usage):
            return []
        translatable_product_series = set(
            product_series
            for product_series in self.series
            if product_series.has_current_translation_templates)
        return sorted(
            translatable_product_series,
            key=operator.attrgetter('datecreated'))

    def getVersionSortedSeries(self, statuses=None, filter_statuses=None):
        """See `IProduct`."""
        store = Store.of(self)
        dev_focus = store.find(
            ProductSeries,
            ProductSeries.id == self.development_focus.id)
        other_series_conditions = [
            ProductSeries.product == self,
            ProductSeries.id != self.development_focus.id,
            ]
        if statuses is not None:
            other_series_conditions.append(
                ProductSeries.status.is_in(statuses))
        if filter_statuses is not None:
            other_series_conditions.append(
                Not(ProductSeries.status.is_in(filter_statuses)))
        other_series = store.find(ProductSeries, other_series_conditions)
        # The query will be much slower if the version_sort_key is not
        # the first thing that is sorted, since it won't be able to use
        # the productseries_name_sort index.
        other_series.order_by(SQL('version_sort_key(name) DESC'))
        # UNION ALL must be used to preserve the sort order from the
        # separate queries. The sorting should not be done after
        # unioning the two queries, because that will prevent it from
        # being able to use the productseries_name_sort index.
        return dev_focus.union(other_series, all=True)

    @property
    def obsolete_translatable_series(self):
        """See `IProduct`."""
        obsolete_product_series = set(
            product_series for product_series in self.series
            if product_series.has_obsolete_translation_templates)
        return sorted(obsolete_product_series, key=lambda s: s.datecreated)

    @property
    def primary_translatable(self):
        """See `IProduct`."""
        packages = self.translatable_packages
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        targetseries = ubuntu.currentseries
        product_series = self.translatable_series

        if product_series:
            # First, go with translation focus
            if self.translation_focus in product_series:
                return self.translation_focus
            # Next, go with development focus
            if self.development_focus in product_series:
                return self.development_focus
            # Next, go with the latest product series that has templates:
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
    def translationgroups(self):
        return reversed(self.getTranslationGroups())

    def isTranslationsOwner(self, person):
        """See `ITranslationPolicy`."""
        # A Product owner gets special translation privileges.
        return person.inTeam(self.owner)

    def getInheritedTranslationPolicy(self):
        """See `ITranslationPolicy`."""
        # A Product inherits parts of it its effective translation
        # policy from its ProjectGroup, if any.
        return self.project

    def sharesTranslationsWithOtherSide(self, person, language,
                                        sourcepackage=None,
                                        purportedly_upstream=False):
        """See `ITranslationPolicy`."""
        assert sourcepackage is None, "Got a SourcePackage for a Product!"
        # Product translations are considered upstream.  They are
        # automatically shared.
        return True

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

        order = self._specification_sort(sort)

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
        completeness = Specification.completeness_clause

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

        if prejoin_people:
            results = self._preload_specifications_people(query)
        else:
            results = Store.of(self).find(
                Specification,
                SQL(query))
        results.order_by(order)
        if quantity is not None:
            results = results[:quantity]
        return results

    def getSpecification(self, name):
        """See `ISpecificationTarget`."""
        return Specification.selectOneBy(product=self, name=name)

    def getSeries(self, name):
        """See `IProduct`."""
        return ProductSeries.selectOneBy(product=self, name=name)

    def newSeries(
        self, owner, name, summary, branch=None, releasefileglob=None):
        # XXX: jamesh 2008-04-11
        # Set the ID of the new ProductSeries to avoid flush order
        # loops in ProductSet.createProduct()
        series = ProductSeries(
            productID=self.id, owner=owner, name=name,
            summary=summary, branch=branch, releasefileglob=releasefileglob)
        if owner.inTeam(self.driver) and not owner.inTeam(self.owner):
            # The user is a product driver, and should be the driver of this
            # series to make him the release manager.
            series.driver = owner
        return series

    def getRelease(self, version):
        """See `IProduct`."""
        store = Store.of(self)
        origin = [
            ProductRelease,
            Join(Milestone, ProductRelease.milestone == Milestone.id),
            ]
        result = store.using(*origin)
        return result.find(
            ProductRelease,
            And(Milestone.product == self,
                Milestone.name == version)).one()

    # XXX: jcsackett 2010-08-23 bug=620494
    # The second clause in the order_by in this method is a bandaid
    # on a sorting issue caused by date vs datetime conflicts in the
    # database. A fix is coming out, but this deals with the edge
    # case responsible for the referenced bug.
    def getMilestonesAndReleases(self):
        """See `IProduct`."""
        store = Store.of(self)
        result = store.find(
            (Milestone, ProductRelease),
            And(ProductRelease.milestone == Milestone.id,
                Milestone.productseries == ProductSeries.id,
                ProductSeries.product == self))
        return result.order_by(
            Desc(ProductRelease.datereleased),
            Desc(Milestone.name))

    def packagedInDistros(self):
        return IStore(Distribution).find(
            Distribution,
            Packaging.productseriesID == ProductSeries.id,
            ProductSeries.product == self,
            Packaging.distroseriesID == DistroSeries.id,
            DistroSeries.distributionID == Distribution.id,
            ).config(distinct=True).order_by(Distribution.name)

    def setBugSupervisor(self, bug_supervisor, user):
        """See `IHasBugSupervisor`."""
        self.bug_supervisor = bug_supervisor
        if bug_supervisor is not None:
            self.addBugSubscription(bug_supervisor, user)

    def composeCustomLanguageCodeMatch(self):
        """See `HasCustomLanguageCodesMixin`."""
        return CustomLanguageCode.product == self

    def createCustomLanguageCode(self, language_code, language):
        """See `IHasCustomLanguageCodes`."""
        return CustomLanguageCode(
            product=self, language_code=language_code, language=language)

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
            And(BugTask.product == self.id,
                BugTask.bugwatch == BugWatch.id,
                BugWatch.bugtracker == self.getExternalBugTracker()))

    def getTimeline(self, include_inactive=False):
        """See `IProduct`."""

        def decorate(series):
            return series.getTimeline(include_inactive=include_inactive)
        if include_inactive is True:
            statuses = None
        else:
            statuses = ACTIVE_STATUSES
        return DecoratedResultSet(
            self.getVersionSortedSeries(statuses=statuses), decorate)

    @property
    def recipes(self):
        """See `IHasRecipes`."""
        from lp.code.model.branch import Branch
        store = Store.of(self)
        return store.find(
            SourcePackageRecipe,
            SourcePackageRecipe.id ==
                SourcePackageRecipeData.sourcepackage_recipe_id,
            SourcePackageRecipeData.base_branch == Branch.id,
            Branch.product == self)

    def getBugTaskWeightFunction(self):
        """Provide a weight function to determine optimal bug task.

        Full weight is given to tasks for this product.

        Given that there must be a product task for a series of that product
        to have a task, we give no more weighting to a productseries task than
        any other.
        """
        productID = self.id

        def weight_function(bugtask):
            if bugtask.productID == productID:
                return OrderedBugTask(1, bugtask.id, bugtask)
            return OrderedBugTask(2, bugtask.id, bugtask)

        return weight_function


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
        return self.get_all_active()

    def get_all_active(self, eager_load=True):
        result = IStore(Product).find(Product, Product.active
            ).order_by(Desc(Product.datecreated))
        if not eager_load:
            return result

        def do_eager_load(rows):
            owner_ids = set(map(operator.attrgetter('_ownerID'), rows))
            # +detailed-listing renders the person with team branding.
            list(getUtility(IPersonSet).getPrecachedPersonsFromIDs(
                owner_ids, need_validity=True, need_icon=True))

        return DecoratedResultSet(result, pre_iter_hook=do_eager_load)

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
                      project_reviewed=False, mugshot=None, logo=None,
                      icon=None, licenses=None, license_info=None,
                      registrant=None):
        """See `IProductSet`."""
        if registrant is None:
            registrant = owner
        if licenses is None:
            licenses = set()
        product = Product(
            owner=owner, registrant=registrant, name=name,
            displayname=displayname, title=title, project=project,
            summary=summary, description=description, homepageurl=homepageurl,
            screenshotsurl=screenshotsurl, wikiurl=wikiurl,
            downloadurl=downloadurl, freshmeatproject=freshmeatproject,
            sourceforgeproject=sourceforgeproject,
            programminglang=programminglang,
            project_reviewed=project_reviewed,
            icon=icon, logo=logo, mugshot=mugshot, license_info=license_info)

        if len(licenses) > 0:
            product._setLicenses(licenses, reset_project_reviewed=False)

        # Create a default trunk series and set it as the development focus
        trunk = product.newSeries(
            owner, 'trunk',
            ('The "trunk" series represents the primary line of development '
             'rather than a stable release branch. This is sometimes also '
             'called MAIN or HEAD.'))
        product.development_focus = trunk

        return product

    def forReview(self, search_text=None, active=None,
                  project_reviewed=None, license_approved=None, licenses=None,
                  license_info_is_empty=None,
                  has_zero_licenses=None,
                  created_after=None, created_before=None,
                  subscription_expires_after=None,
                  subscription_expires_before=None,
                  subscription_modified_after=None,
                  subscription_modified_before=None):
        """See lp.registry.interfaces.product.IProductSet."""

        conditions = []

        if project_reviewed is not None:
            conditions.append(Product.project_reviewed == project_reviewed)

        if license_approved is not None:
            conditions.append(Product.license_approved == license_approved)

        if active is not None:
            conditions.append(Product.active == active)

        if search_text is not None and search_text.strip() != '':
            conditions.append(SQL('''
                Product.fti @@ ftq(%(text)s) OR
                Product.name = lower(%(text)s)
                ''' % sqlvalues(text=search_text)))

        def dateToDatetime(date):
            """Convert a datetime.date to a datetime.datetime

            The returned time will have a zero time component and be based on
            UTC.
            """
            return datetime.datetime.combine(
                date, datetime.time(tzinfo=pytz.UTC))

        if created_after is not None:
            if not isinstance(created_after, datetime.datetime):
                created_after = dateToDatetime(created_after)
                created_after = datetime.datetime(
                    created_after.year, created_after.month,
                    created_after.day, tzinfo=pytz.utc)
            conditions.append(Product.datecreated >= created_after)

        if created_before is not None:
            if not isinstance(created_before, datetime.datetime):
                created_before = dateToDatetime(created_before)
            conditions.append(Product.datecreated <= created_before)

        needs_join = False

        if subscription_expires_after is not None:
            if not isinstance(subscription_expires_after, datetime.datetime):
                subscription_expires_after = (
                    dateToDatetime(subscription_expires_after))
            conditions.append(
                CommercialSubscription.date_expires >=
                    subscription_expires_after)
            needs_join = True

        if subscription_expires_before is not None:
            if not isinstance(subscription_expires_before, datetime.datetime):
                subscription_expires_before = (
                    dateToDatetime(subscription_expires_before))
            conditions.append(
                CommercialSubscription.date_expires <=
                    subscription_expires_before)
            needs_join = True

        if subscription_modified_after is not None:
            if not isinstance(subscription_modified_after, datetime.datetime):
                subscription_modified_after = (
                    dateToDatetime(subscription_modified_after))
            conditions.append(
                CommercialSubscription.date_last_modified >=
                    subscription_modified_after)
            needs_join = True
        if subscription_modified_before is not None:
            if not isinstance(subscription_modified_before,
                              datetime.datetime):
                subscription_modified_before = (
                    dateToDatetime(subscription_modified_before))
            conditions.append(
                CommercialSubscription.date_last_modified <=
                    subscription_modified_before)
            needs_join = True

        if needs_join:
            conditions.append(
                CommercialSubscription.productID == Product.id)

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
            conditions.append(SQL('(%s)' % '\nOR '.join(or_conditions)))

        result = IStore(Product).find(
            Product, *conditions).config(
                distinct=True).order_by(
                    Product.datecreated, Product.displayname)
        return result

    def search(self, text=None):
        """See lp.registry.interfaces.product.IProductSet."""
        # Circular...
        from lp.registry.model.projectgroup import ProjectGroup
        conditions = []
        conditions = [Product.active]
        if text:
            conditions.append(
                SQL("Product.fti @@ ftq(%s) " % sqlvalues(text)))
        result = IStore(Product).find(Product, *conditions)

        def eager_load(rows):
            product_ids = set(obj.id for obj in rows)
            if not product_ids:
                return
            products = dict((product.id, product) for product in rows)
            caches = dict((product.id, get_property_cache(product))
                for product in rows)
            for cache in caches.values():
                if not safe_hasattr(cache, 'commercial_subscription'):
                    cache.commercial_subscription = None
                if not safe_hasattr(cache, '_cached_licenses'):
                    cache._cached_licenses = []
            for subscription in IStore(CommercialSubscription).find(
                CommercialSubscription,
                CommercialSubscription.productID.is_in(product_ids)):
                cache = caches[subscription.productID]
                cache.commercial_subscription = subscription
            for license in IStore(ProductLicense).find(
                ProductLicense,
                ProductLicense.productID.is_in(product_ids)):
                cache = caches[license.productID]
                cache._cached_licenses.append(license.license)
            for cache in caches.values():
                cache._cached_licenses = tuple(sorted(cache._cached_licenses))
            bulk.load_related(ProjectGroup, products.values(), ['projectID'])
            bulk.load_related(ProductSeries, products.values(),
                ['development_focusID'])
            # Only need the objects for canonical_url, no need for validity.
            bulk.load_related(Person, products.values(),
                ['_ownerID', 'registrantID', 'bug_supervisorID', 'driverID',
                 'security_contactID'])
        return DecoratedResultSet(result, pre_iter_hook=eager_load)

    def search_sqlobject(self, text):
        """See `IProductSet`"""
        queries = ["Product.fti @@ ftq(%s) " % sqlvalues(text)]
        queries.append('Product.active IS TRUE')
        query = "Product.active IS TRUE AND Product.fti @@ ftq(%s)" \
            % sqlvalues(text)
        return Product.select(query)

    def getTranslatables(self):
        """See `IProductSet`"""
        # XXX j.c.sackett 2010-11-19 bug=677532 It's less than ideal that
        # this query is using _translations_usage, but there's no cleaner
        # way to deal with it. Once the bug above is resolved, this should
        # should be fixed to use translations_usage.
        results = IStore(Product).find(
            (Product, Person),
            Product.active == True,
            Product.id == ProductSeries.productID,
            POTemplate.productseriesID == ProductSeries.id,
            Product._translations_usage == ServiceUsage.LAUNCHPAD,
            Person.id == Product._ownerID).config(
                distinct=True).order_by(Product.title)

        # We only want Product - the other tables are just to populate
        # the cache.
        return DecoratedResultSet(results, operator.itemgetter(0))

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
                    WHERE Product.active AND Product.translations_usage = %s
                    ORDER BY place
                ) AS randomized_products
                LIMIT %s
            )
            ''' % sqlvalues(ServiceUsage.LAUNCHPAD, maximumproducts),
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
