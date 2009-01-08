# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces including and related to IProduct."""

__metaclass__ = type

__all__ = [
    'IProduct',
    'IProductEditRestricted',
    'IProductPublic',
    'IProductReviewSearch',
    'IProductSet',
    'License',
    'LicenseStatus',
    'NoSuchProduct',
    ]

import sets

from zope.interface import Interface, Attribute
from zope.schema import (
    Bool, Choice, Date, Datetime, Int, Object, Set, Text, TextLine)
from zope.schema.vocabulary import SimpleVocabulary


from canonical.launchpad import _
from canonical.launchpad.fields import (
    Description, IconImageUpload, LogoImageUpload, MugshotImageUpload,
    ProductBugTracker, ProductNameField, PublicPersonChoice,
    Summary, Title, URIField)
from canonical.launchpad.interfaces.branch import IBranch
from canonical.launchpad.interfaces.branchvisibilitypolicy import (
    IHasBranchVisibilityPolicy)
from canonical.launchpad.interfaces.bugtarget import IBugTarget
from canonical.launchpad.interfaces.karma import IKarmaContext
from canonical.launchpad.interfaces.launchpad import (
    IHasAppointedDriver, IHasDrivers, IHasExternalBugTracker, IHasIcon,
    IHasLogo, IHasMugshot, IHasOwner, IHasSecurityContact,
    ILaunchpadUsage)
from canonical.launchpad.interfaces.milestone import (
    ICanGetMilestonesDirectly, IHasMilestones)
from canonical.launchpad.interfaces.announcement import IMakesAnnouncements
from canonical.launchpad.interfaces.mentoringoffer import IHasMentoringOffers
from canonical.launchpad.interfaces.pillar import IPillar
from canonical.launchpad.interfaces.productrelease import IProductRelease
from canonical.launchpad.interfaces.productseries import IProductSeries
from canonical.launchpad.interfaces.project import IProject
from canonical.launchpad.interfaces.specificationtarget import (
    ISpecificationTarget)
from canonical.launchpad.interfaces.sprint import IHasSprints
from canonical.launchpad.interfaces.translationgroup import (
    IHasTranslationGroup)
from canonical.launchpad.validators.name import name_validator
from canonical.launchpad.webapp.interfaces import NameLookupFailed
from canonical.lazr.enum import DBEnumeratedType, DBItem
from canonical.lazr.fields import CollectionField, Reference, ReferenceChoice
from canonical.lazr.rest.declarations import (
    REQUEST_USER, call_with, collection_default_content,
    export_as_webservice_collection, export_as_webservice_entry,
    export_factory_operation, export_operation_as, export_read_operation,
    exported, operation_parameters, operation_returns_collection_of,
    rename_parameters_as)


class LicenseStatus(DBEnumeratedType):
    """The status of a project's license review."""

    OPEN_SOURCE = DBItem(
        10, "Open Source",
        u"This project&rsquo;s license is open source.")
    PROPRIETARY = DBItem(
        20, "Proprietary",
        u"This project&rsquo;s license is proprietary.")
    UNREVIEWED = DBItem(
        30, "Unreviewed",
        u"This project&rsquo;s license has not been reviewed.")
    UNSPECIFIED = DBItem(
        40, "Unspecified",
        u"This project&rsquo;s license has not been specified.")

class License(DBEnumeratedType):
    """Licenses under which a project's code can be released."""

    ACADEMIC = DBItem(10, "Academic Free License")
    AFFERO = DBItem(20, "GNU Affero GPL v3")
    APACHE = DBItem(30, "Apache License")
    ARTISTIC = DBItem(40, "Artistic License")
    BSD = DBItem(50, "BSD License (revised)")
    COMMON_PUBLIC = DBItem(80, "Common Public License")
    ECLIPSE = DBItem(90, "Eclipse Public License")
    EDUCATIONAL_COMMUNITY = DBItem(100, "Educational Community License")
    GNU_GPL_V2 = DBItem(130, "GNU GPL v2")
    GNU_GPL_V3 = DBItem(135, "GNU GPL v3")
    GNU_LGPL_V2_1 = DBItem(150, "GNU LGPL v2.1")
    GNU_LGPL_V3 = DBItem(155, "GNU LGPL v3")
    MIT = DBItem(160, "MIT / X / Expat License")
    MPL = DBItem(170, "Mozilla Public License")
    OPEN_SOFTWARE = DBItem(190, "Open Software License")
    PERL = DBItem(200, "Perl License")
    PHP = DBItem(210, "PHP License")
    PUBLIC_DOMAIN = DBItem(220, "Public Domain")
    PYTHON = DBItem(230, "Python License")
    ZPL = DBItem(280, "Zope Public License")

    OTHER_PROPRIETARY = DBItem(1000, "Other/Proprietary")
    OTHER_OPEN_SOURCE = DBItem(1010, "Other/Open Source")


class IProductEditRestricted(Interface):
    """IProduct properties which require launchpad.Edit permission."""

    def newSeries(owner, name, summary, branch=None):
        """Creates a new ProductSeries for this product."""


class IProductPublic(
    IBugTarget, ICanGetMilestonesDirectly, IHasAppointedDriver,
    IHasBranchVisibilityPolicy, IHasDrivers, IHasExternalBugTracker, IHasIcon,
    IHasLogo, IHasMentoringOffers, IHasMilestones, IHasMugshot, IHasOwner,
    IHasSecurityContact, IHasSprints, IHasTranslationGroup, IKarmaContext,
    ILaunchpadUsage, IMakesAnnouncements, ISpecificationTarget, IPillar):
    """Public IProduct properties."""

    # XXX Mark Shuttleworth 2004-10-12: Let's get rid of ID's in interfaces
    # unless we really need them. BradB says he can remove the need for them
    # in SQLObject soon.
    id = Int(title=_('The Project ID'))

    project = exported(
        ReferenceChoice(
            title=_('Part of'),
            required=False,
            vocabulary='Project',
            schema=IProject,
            description=_(
                'Super-project. In Launchpad, we can setup a special '
                '"project group" that is an overarching initiative that '
                'includes several related projects. For example, the Mozilla '
                'Project produces Firefox, Thunderbird and Gecko. This '
                'information is used to group those projects in a coherent '
                'way. If you make this project part of a group, the group '
                'preferences and decisions around bug tracking, translation '
                'and security policy will apply to this project.')),
        exported_as='project_group')

    owner = exported(
        PublicPersonChoice(
            title=_('Maintainer'),
            required=True,
            vocabulary='ValidOwner',
            description=_("The person or team who maintains the project "
                          "information in Launchpad.")))

    registrant = exported(
        PublicPersonChoice(
            title=_('Registrant'),
            required=True,
            readonly=True,
            vocabulary='ValidPersonOrTeam',
            description=_("This person registered the project in "
                          "Launchpad.")))

    driver = exported(
        PublicPersonChoice(
            title=_("Driver"),
            description=_(
                "This person or team will be able to set feature goals for "
                "and approve bug targeting or backporting for ANY major "
                "series in this project. You might want to leave this blank "
                "and just appoint a team for each specific series, rather "
                "than having one project team that does it all."),
            required=False, vocabulary='ValidPersonOrTeam'))

    drivers = Attribute(
        "Presents the drivers of this project as a list. A list is "
        "required because there might be a project driver and also a "
        "driver appointed in the overarching project group.")

    name = exported(
        ProductNameField(
            title=_('Name'),
            constraint=name_validator,
            description=_(
                "At least one lowercase letter or number, followed by "
                "letters, dots, hyphens or plusses. "
                "Keep this name short, as it is used in URLs.")))

    displayname = exported(
        TextLine(
            title=_('Display Name'),
            description=_("""The name of the project as it would appear in a
                paragraph.""")),
        exported_as='display_name')

    title = exported(
        Title(
            title=_('Title'),
            description=_("The project title. Should be just a few words.")))

    summary = exported(
        Summary(
            title=_('Summary'),
            description=_("The summary should be a single short paragraph.")))

    description = exported(
        Description(
            title=_('Description'),
            required=False,
            description=_("""Include information on how to get involved with
                development. Don't repeat anything from the Summary.""")))

    datecreated = exported(
        Datetime(
            title=_('Date Created'),
            required=True, readonly=True,
            description=_("The date this project was created in Launchpad.")),
        exported_as='date_created')

    homepageurl = exported(
        URIField(
            title=_('Homepage URL'),
            required=False,
            allowed_schemes=['http', 'https', 'ftp'], allow_userinfo=False,
            description=_("""The project home page. Please include
                the http://""")),
        exported_as="homepage_url")

    wikiurl = exported(
        URIField(
            title=_('Wiki URL'),
            required=False,
            allowed_schemes=['http', 'https', 'ftp'], allow_userinfo=False,
            description=_("""The full URL of this project's wiki, if it has
                one. Please include the http://""")),
        exported_as='wiki_url')

    screenshotsurl = exported(
        URIField(
            title=_('Screenshots URL'),
            required=False,
            allowed_schemes=['http', 'https', 'ftp'], allow_userinfo=False,
            description=_("""The full URL for screenshots of this project,
                if available. Please include the http://""")),
        exported_as='screenshots_url')

    downloadurl = exported(
        URIField(
            title=_('Download URL'),
            required=False,
            allowed_schemes=['http', 'https', 'ftp'], allow_userinfo=False,
            description=_("""The full URL where downloads for this project
                are located, if available. Please include the http://""")),
        exported_as='download_url')

    programminglang = exported(
        TextLine(
            title=_('Programming Languages'),
            required=False,
            description=_("""A comma delimited list of programming
                languages used for this project.""")),
        exported_as='programming_language')

    sourceforgeproject = exported(
        TextLine(
            title=_('Sourceforge Project'),
            required=False,
            description=_("""The SourceForge project name for
                this project, if it is in sourceforge.""")),
        exported_as='sourceforge_project')

    freshmeatproject = exported(
        TextLine(
            title=_('Freshmeat Project'),
            required=False, description=_("""The Freshmeat project name for
                this project, if it is in freshmeat.""")),
        exported_as='freshmeat_project')

    homepage_content = Text(
        title=_("Homepage Content"), required=False,
        description=_(
            "The content of this project's home page. Edit this and it will "
            "be displayed for all the world to see. It is NOT a wiki "
            "so you cannot undo changes."))

    icon = exported(
        IconImageUpload(
            title=_("Icon"), required=False,
            default_image_resource='/@@/product',
            description=_(
                "A small image of exactly 14x14 pixels and at most 5kb in "
                "size, that can be used to identify this project. The icon "
                "will be displayed next to the project name everywhere in "
                "Launchpad that we refer to the project and link to it.")))

    logo = exported(
        LogoImageUpload(
            title=_("Logo"), required=False,
            default_image_resource='/@@/product-logo',
            description=_(
                "An image of exactly 64x64 pixels that will be displayed in "
                "the heading of all pages related to this project. It should "
                "be no bigger than 50kb in size.")))

    mugshot = exported(
        MugshotImageUpload(
            title=_("Brand"), required=False,
            default_image_resource='/@@/product-mugshot',
            description=_(
                "A large image of exactly 192x192 pixels, that will be "
                "displayed on this project's home page in Launchpad. It "
                "should be no bigger than 100kb in size.")),
        exported_as='brand')

    autoupdate = Bool(title=_('Automatic update'),
        description=_("""Whether or not this project's attributes are
        updated automatically."""))

    license_reviewed = Bool(
        title=_('License reviewed'),
        description=_("""Whether or not this project's license has been
        reviewed. Editable only by reviewers (Admins & Commercial Admins).
        """))

    private_bugs = Bool(title=_('Private bugs'), description=_("""Whether
        or not bugs reported into this project are private by default"""))

    reviewer_whiteboard = Text(
        title=_('Notes for the project reviewer'),
        required=False,
        description=_(
            "Notes on the project's license, editable only by reviewers "
            "(Admins & Commercial Admins)."))

    licenses = exported(
        Set(title=_('Licenses'),
            value_type=Choice(vocabulary=License)))

    license_info = exported(
        Description(
            title=_('Description of additional licenses'),
            required=False,
            description=_(
                "Description of licenses that do not appear in the list "
                "above.")))

    bugtracker = exported(
        ProductBugTracker(
            title=_('Bugs are tracked'),
            vocabulary="BugTracker"),
        exported_as='bug_tracker')

    sourcepackages = Attribute(_("List of packages for this product"))

    distrosourcepackages = Attribute(_("List of distribution packages for "
        "this product"))

    serieses = exported(
        CollectionField(value_type=Object(schema=IProductSeries)),
        exported_as='series')

    development_focus = exported(
        ReferenceChoice(
            title=_('Development focus'), required=True,
            vocabulary='FilteredProductSeries',
            schema=IProductSeries,
            description=_('The "trunk" series where development is focused')))

    default_stacked_on_branch = Attribute(
        _('The branch that new branches will be stacked on by default.'))

    name_with_project = Attribute(_("Returns the product name prefixed "
        "by the project name, if a project is associated with this "
        "product; otherwise, simply returns the product name."))

    releases = exported(
        CollectionField(
            title=_("An iterator over the ProductReleases for this product."),
            readonly=True,
            value_type=Reference(schema=IProductRelease)))

    branches = exported(
        CollectionField(
            title=_("An iterator over the Bazaar branches that are "
                    "related to this product."),
            readonly=True,
            value_type=Reference(schema=IBranch)))

    bounties = Attribute(_("The bounties that are related to this product."))

    translatable_packages = Attribute(
        "A list of the source packages for this product that can be "
        "translated sorted by distroseries.name and sourcepackage.name.")

    translatable_series = Attribute(
        "A list of the series of this product for which we have translation "
        "templates.")

    obsolete_translatable_series = Attribute("""
        A list of the series of this product with obsolete translation
        templates.""")

    primary_translatable = Attribute(
        "The best guess we have for what new translators will want to "
        "translate for a given product: the latest series for which we have "
        "templates, and failing that, an Ubuntu package.")

    translationgroups = Attribute("The list of applicable translation "
        "groups for a product. There can be several: one from the product, "
        "and potentially one from the project, too.")

    aggregatetranslationpermission = Attribute("The translation permission "
        "that applies to translations in this product, based on the "
        "permissions that apply to the product as well as its project.")

    commercial_subscription = Attribute("""
        An object which contains the timeframe and the voucher
        code of a subscription.""")

    qualifies_for_free_hosting = Attribute("""
        Whether the project's licensing qualifies it for free
        use of launchpad.""")

    commercial_subscription_is_due = Attribute("""
        Whether the project's licensing requires a new commercial
        subscription to use launchpad.""")

    is_permitted = Attribute("""
        Whether the project's licensing qualifies for free
        hosting or the project has an up-to-date subscription.""")

    license_approved = Bool(
        title=_("License approved"),
        description=_(
            "Whether a license is manually approved for free "
            "hosting after automatic approval fails.  May only "
            "be applied to licenses of 'Other/Open Source'."))

    license_status = Attribute("""
        Whether the license is OPENSOURCE, UNREVIEWED, or PROPRIETARY.""")

    def redeemSubscriptionVoucher(voucher, registrant, purchaser,
                                  subscription_months, whiteboard=None,
                                  current_datetime=None):
        """Redeem a voucher and extend the subscription expiration date.

        The voucher must have already been verified to be redeemable.
        :param voucher: The voucher id as tracked in the external system.
        :param registrant: Who is redeeming the voucher.
        :param purchaser: Who purchased the voucher.  May not be known.
        :param subscription_months: integer indicating the number of months
            the voucher is for.
        :param whiteboard: Notes for this activity.
        :param current_datetime: Current time.  Will be datetime.now() if not specified.
        :return: None
        """

    def getLatestBranches(quantity=5):
        """Latest <quantity> branches registered for this product."""

    def getPackage(distroseries):
        """Return a package in that distroseries for this product."""

    def getSeries(name):
        """Returns the series for this product that has the name given, or
        None."""

    def getRelease(version):
        """Returns the release for this product that has the version
        given."""

    def packagedInDistros():
        """Returns the distributions this product has been packaged in."""

    def ensureRelatedBounty(bounty):
        """Ensure that the bounty is linked to this product. Return None.
        """

    def getCustomLanguageCode(language_code):
        """Look up `ICustomLanguageCode` for `language_code`, if any.

        Products may override language code definitions for translation
        import purposes.
        """

    def userCanEdit(user):
        """Can the user edit this product?"""

class IProduct(IProductEditRestricted, IProductPublic):
    """A Product.

    The Launchpad Registry describes the open source world as Projects and
    Products. Each Project may be responsible for several Products.
    For example, the Mozilla Project has Firefox, Thunderbird and The
    Mozilla App Suite as Products, among others.
    """

    export_as_webservice_entry('project')

# Fix cyclic references.
IProject['products'].value_type = Reference(IProduct)
IProductRelease['product'].schema = IProduct


class IProductSet(Interface):
    """The collection of products."""
    export_as_webservice_collection(IProduct)

    title = Attribute("The set of Products registered in the Launchpad")

    people = Attribute(
        "The PersonSet, placed here so we can easily render "
        "the list of latest teams to register on the /projects/ page.")

    all_active = Attribute(
        "All the active products, sorted newest first.")

    def __iter__():
        """Return an iterator over all the active products."""

    def __getitem__(name):
        """Get a product by its name."""

    def get(productid):
        """Get a product by its id.

        If the product can't be found a NotFoundError will be
        raised.
        """

    def getByName(name, ignore_inactive=False):
        """Return the product with the given name, ignoring inactive products
        if ignore_inactive is True.

        Return None if there is no such product.
        """

    def getProductsWithBranches(num_products=None):
        """Return an iterator over all active products that have branches.

        If num_products is not None, then the first `num_products` are
        returned.
        """

    def getProductsWithUserDevelopmentBranches():
        """Return products that have a user branch for the development series.

        Only active products are returned.

        A user branch is one that is either HOSTED or MIRRORED, not IMPORTED.
        """

    @call_with(owner=REQUEST_USER)
    @rename_parameters_as(
        displayname='display_name', project='project_group',
        homepageurl='home_page_url', screenshotsurl='screenshots_url',
        freshmeatproject='freshmeat_project', wikiurl='wiki_url',
        downloadurl='download_url',
        sourceforgeproject='sourceforge_project',
        programminglang='programming_lang')
    @export_factory_operation(
        IProduct, ['name', 'displayname', 'title', 'summary', 'description',
                   'project', 'homepageurl', 'screenshotsurl',
                   'downloadurl', 'freshmeatproject', 'wikiurl',
                   'sourceforgeproject', 'programminglang',
                   'licenses', 'license_info', 'registrant'])
    @export_operation_as('new_project')
    def createProduct(owner, name, displayname, title, summary,
                      description=None, project=None, homepageurl=None,
                      screenshotsurl=None, wikiurl=None,
                      downloadurl=None, freshmeatproject=None,
                      sourceforgeproject=None, programminglang=None,
                      license_reviewed=False, mugshot=None, logo=None,
                      icon=None, licenses=None, license_info=None,
                      registrant=None):
        """Create and return a brand new Product.

        See `IProduct` for a description of the parameters.
        """

    def forReview():
        """Return an iterator over products that need to be reviewed."""

    @collection_default_content()
    @operation_parameters(text=TextLine(title=_("Search text")))
    @operation_returns_collection_of(IProduct)
    @export_read_operation()
    def search(text=None, soyuz=None,
               rosetta=None, malone=None,
               bazaar=None):
        """Search through the Registry database for products that match the
        query terms. text is a piece of text in the title / summary /
        description fields of product. soyuz, bazaar, malone etc are
        hints as to whether the search should be limited to products
        that are active in those Launchpad applications."""


    @operation_returns_collection_of(IProduct)
    @call_with(quantity=None)
    @export_read_operation()
    def latest(quantity=5):
        """Return the latest projects registered in the Launchpad.

        If the quantity is not specified or is a value that is not 'None'
        then the set of projects returned is limited to that value (the
        default quantity is 5).  If quantity is 'None' then all projects are
        returned.  For the web service it is not possible to specify the
        quantity, so all projects are returned, latest first.
        """

    def getTranslatables():
        """Return an iterator over products that have translatable resources.

        Skips products that are not configured to be translated in
        Launchpad, as well as non-active ones.
        """

    def featuredTranslatables(maximumproducts=8):
        """Return an iterator over a random sample of translatable products.

        Similar to `getTranslatables`, except the number of results is
        limited and they are randomly chosen.

        :param maximum_products: Maximum number of products to be
            returned.
        :return: An iterator over active, translatable products.
        """
        # XXX JeroenVermeulen 2008-07-31 bug=253583: this is not
        # currently used!

    def count_all():
        """Return a count of the total number of products registered in
        Launchpad."""

    def count_translatable():
        """Return a count of the number of products that have
        upstream-oriented translations configured in Rosetta."""

    def count_bounties():
        """Return a number of products that have bounties registered in the
        Launchpad for them."""

    def count_buggy():
        """Return the number of products that have bugs associated with them
        in Launchpad."""

    def count_featureful():
        """Return the number of products that have specs associated with
        them in Blueprint."""

    def count_reviewed():
        """Return a count of the number of products in the Launchpad that
        are both active and reviewed."""

    def count_answered():
        """Return the number of projects that have questions and answers
        associated with them.
        """

    def count_codified():
        """Return the number of projects that have branches associated with
        them.
        """


emptiness_vocabulary = SimpleVocabulary.fromItems(
        [('Empty', True), ('Not Empty', False)])

class IProductReviewSearch(Interface):
    """A search form for products being reviewed."""

    search_text = TextLine(
      title=_('Search text'),
      description=_("Search text in the product's name, displayname, title, "
                    "summary, and description."),
      required=False)

    active = Choice(
        title=_('Active'), values=[True, False],
        required=False, default=True)

    license_reviewed = Choice(
        title=_('License Reviewed'), values=[True, False],
        required=False, default=False)

    license_info_is_empty = Choice(
        title=_('Description of additional licenses'),
        description=_('Either this field or any one of the selected licenses'
                      ' must match.'),
        vocabulary=emptiness_vocabulary, required=False, default=False)

    licenses = Set(
        title=_('Licenses'),
        value_type=Choice(vocabulary=License),
        required=False,
        # Zope requires sets.Set() instead of the builtin set().
        default=sets.Set(
            [License.OTHER_PROPRIETARY, License.OTHER_OPEN_SOURCE]))

    has_zero_licenses = Choice(
        title=_('Or has no license specified'),
        values=[True, False], required=False)

    created_after = Date(title=_("Created between"), required=False)

    created_before = Date(title=_("and"), required=False)

    subscription_expires_after = Date(
        title=_("Subscription expires between"), required=False)

    subscription_expires_before = Date(
        title=_("and"), required=False)

    subscription_modified_after = Date(
        title=_("Subscription modified between"), required=False)

    subscription_modified_before = Date(
        title=_("and"), required=False)


class NoSuchProduct(NameLookupFailed):
    """Raised when we try to find a product that doesn't exist."""

    _message_prefix = "No such product"
