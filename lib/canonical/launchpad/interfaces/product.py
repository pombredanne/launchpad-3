# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces including and related to IProduct."""

__metaclass__ = type

__all__ = [
    'IProduct',
    'IProductSet',
    'License',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Bool, Choice, Int, Set, Text, TextLine

from canonical.launchpad import _
from canonical.launchpad.fields import (
    Description, IconImageUpload, LogoImageUpload, MugshotImageUpload,
    ProductBugTracker, ProductNameField, PublicPersonChoice,
    Summary, Title, URIField)
from canonical.launchpad.interfaces.branchvisibilitypolicy import (
    IHasBranchVisibilityPolicy)
from canonical.launchpad.interfaces.bugtarget import IBugTarget
from canonical.launchpad.interfaces.karma import IKarmaContext
from canonical.launchpad.interfaces.launchpad import (
    IHasAppointedDriver, IHasDrivers, IHasIcon, IHasLogo, IHasMugshot,
    IHasOwner, IHasSecurityContact, ILaunchpadUsage)
from canonical.launchpad.interfaces.milestone import IHasMilestones
from canonical.launchpad.interfaces.announcement import IMakesAnnouncements
from canonical.launchpad.interfaces.pillar import IPillar
from canonical.launchpad.interfaces.specificationtarget import (
    ISpecificationTarget)
from canonical.launchpad.interfaces.sprint import IHasSprints
from canonical.launchpad.interfaces.translationgroup import (
    IHasTranslationGroup)
from canonical.launchpad.validators.name import name_validator
from canonical.launchpad.interfaces.mentoringoffer import IHasMentoringOffers
from canonical.lazr import DBEnumeratedType, DBItem


class License(DBEnumeratedType):
    """Licenses under which a project's code can be released."""

    # XXX: EdwinGrubbs 2008-04-11 bug=216040
    # The deprecated licenses can be removed in the next cycle.

    ACADEMIC = DBItem(10, "Academic Free License")
    AFFERO = DBItem(20, "Affero GPL")
    APACHE = DBItem(30, "Apache License")
    ARTISTIC = DBItem(40, "Artistic License")
    BSD = DBItem(50, "BSD License (revised)")
    _DEPRECATED_CDDL = DBItem(60, "CDDL")
    _DEPRECATED_CECILL = DBItem(70, "CeCILL License")
    COMMON_PUBLIC = DBItem(80, "Common Public License")
    ECLIPSE = DBItem(90, "Eclipse Public License")
    EDUCATIONAL_COMMUNITY = DBItem(100, "Educational Community License")
    _DEPRECATED_EIFFEL = DBItem(110, "Eiffel Forum License")
    _DEPRECATED_GNAT = DBItem(120, "GNAT Modified GPL")
    GNU_GPL_V2 = DBItem(130, "GNU GPL v2")
    GNU_GPL_V3 = DBItem(135, "GNU GPL v3")
    GNU_LGPL_V2_1 = DBItem(150, "GNU LGPL v2.1")
    GNU_LGPL_V3 = DBItem(155, "GNU LGPL v3")
    _DEPRECATED_IBM = DBItem(140, "IBM Public License")
    MIT = DBItem(160, "MIT / X / Expat License")
    MPL = DBItem(170, "Mozilla Public License")
    _DEPRECATED_OPEN_CONTENT = DBItem(180, "Open Content License")
    OPEN_SOFTWARE = DBItem(190, "Open Software License")
    PERL = DBItem(200, "Perl License")
    PHP = DBItem(210, "PHP License")
    PUBLIC_DOMAIN = DBItem(220, "Public Domain")
    PYTHON = DBItem(230, "Python License")
    _DEPRECATED_QPL = DBItem(240, "Q Public License")
    _DEPRECATED_SUN_PUBLIC = DBItem(250, "SUN Public License")
    _DEPRECATED_W3C = DBItem(260, "W3C License")
    _DEPRECATED_ZLIB = DBItem(270, "zlib/libpng License")
    ZPL = DBItem(280, "Zope Public License")

    OTHER_PROPRIETARY = DBItem(1000, "Other/Proprietary")
    OTHER_OPEN_SOURCE = DBItem(1010, "Other/Open Source")


class IProduct(IBugTarget, IHasAppointedDriver, IHasBranchVisibilityPolicy,
               IHasDrivers, IHasIcon, IHasLogo, IHasMentoringOffers,
               IHasMilestones, IHasMugshot, IMakesAnnouncements, IHasOwner,
               IHasSecurityContact, IHasSprints, IHasTranslationGroup,
               IKarmaContext, ILaunchpadUsage, ISpecificationTarget,
               IPillar):
    """A Product.

    The Launchpad Registry describes the open source world as Projects and
    Products. Each Project may be responsible for several Products.
    For example, the Mozilla Project has Firefox, Thunderbird and The
    Mozilla App Suite as Products, among others.
    """

    # XXX Mark Shuttleworth 2004-10-12: Let's get rid of ID's in interfaces
    # unless we really need them. BradB says he can remove the need for them
    # in SQLObject soon.
    id = Int(title=_('The Project ID'))

    project = Choice(
        title=_('Part of'),
        required=False,
        vocabulary='Project',
        description=_("""Super-project. In Launchpad, we can setup a
            special "project group" that is an overarching initiative that
            includes several related projects. For example, the
            Mozilla Project produces Firefox, Thunderbird and Gecko. This
            information is used to group those projects in a coherent way.
            If you make this project part of a group, the group preferences
            and decisions around bug tracking, translation and security
            policy will apply to this project."""))

    owner = PublicPersonChoice(
        title=_('Owner'),
        required=True,
        vocabulary='ValidOwner',
        description=_("""Project owner, it can either a valid Person or Team
            inside Launchpad context."""))

    driver = PublicPersonChoice(
        title=_("Driver"),
        description=_(
            "This person or team will be able to set feature goals for "
            "and approve bug targeting or backporting for ANY major series "
            "in this project. You might want to leave this blank and just "
            "appoint a team for each specific series, rather than having "
            "one project team that does it all."),
        required=False, vocabulary='ValidPersonOrTeam')

    drivers = Attribute(
        "Presents the drivers of this project as a list. A list is "
        "required because there might be a project driver and also a "
        "driver appointed in the overarching project group.")

    name = ProductNameField(
        title=_('Name'),
        constraint=name_validator,
        description=_("""At least one lowercase letter or number, followed by
            letters, dots, hyphens or plusses.
            Keep this name short, as it is used in URLs."""))

    displayname = TextLine(
        title=_('Display Name'),
        description=_("""The name of the project as it would appear in a
            paragraph."""))

    title = Title(
        title=_('Title'),
        description=_("""The project title. Should be just a few words."""))

    summary = Summary(
        title=_('Summary'),
        description=_("""The summary should be a single short paragraph."""))

    description = Description(
        title=_('Description'),
        required=False,
        description=_("""Include information on how to get involved with
            development. Don't repeat anything from the Summary."""))

    datecreated = TextLine(
        title=_('Date Created'),
        description=_("""The date this project was created in Launchpad."""))

    homepageurl = URIField(
        title=_('Homepage URL'),
        required=False,
        allowed_schemes=['http', 'https', 'ftp'], allow_userinfo=False,
        description=_("""The project home page. Please include
            the http://"""))

    wikiurl = URIField(
        title=_('Wiki URL'),
        required=False,
        allowed_schemes=['http', 'https', 'ftp'], allow_userinfo=False,
        description=_("""The full URL of this project's wiki, if it has one.
            Please include the http://"""))

    screenshotsurl = URIField(
        title=_('Screenshots URL'),
        required=False,
        allowed_schemes=['http', 'https', 'ftp'], allow_userinfo=False,
        description=_("""The full URL for screenshots of this project,
            if available. Please include the http://"""))

    downloadurl = URIField(
        title=_('Download URL'),
        required=False,
        allowed_schemes=['http', 'https', 'ftp'], allow_userinfo=False,
        description=_("""The full URL where downloads for this project
            are located, if available. Please include the http://"""))

    programminglang = TextLine(
        title=_('Programming Language'),
        required=False,
        description=_("""A comma delimited list of programming
            languages used for this project."""))

    sourceforgeproject = TextLine(title=_('Sourceforge Project'),
        required=False,
        description=_("""The SourceForge project name for
            this project, if it is in sourceforge."""))

    freshmeatproject = TextLine(title=_('Freshmeat Project'),
        required=False, description=_("""The Freshmeat project name for
            this project, if it is in freshmeat."""))

    homepage_content = Text(
        title=_("Homepage Content"), required=False,
        description=_(
            "The content of this project's home page. Edit this and it will "
            "be displayed for all the world to see. It is NOT a wiki "
            "so you cannot undo changes."))

    icon = IconImageUpload(
        title=_("Icon"), required=False,
        default_image_resource='/@@/product',
        description=_(
            "A small image of exactly 14x14 pixels and at most 5kb in size, "
            "that can be used to identify this project. The icon will be "
            "displayed next to the project name everywhere in Launchpad that "
            "we refer to the project and link to it."))

    logo = LogoImageUpload(
        title=_("Logo"), required=False,
        default_image_resource='/@@/product-logo',
        description=_(
            "An image of exactly 64x64 pixels that will be displayed in "
            "the heading of all pages related to this project. It should be "
            "no bigger than 50kb in size."))

    mugshot = MugshotImageUpload(
        title=_("Brand"), required=False,
        default_image_resource='/@@/product-mugshot',
        description=_(
            "A large image of exactly 192x192 pixels, that will be displayed "
            "on this project's home page in Launchpad. It should be no "
            "bigger than 100kb in size. "))

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

    licenses = Set(
        title=_('Licenses'),
        value_type=Choice(vocabulary=License))

    license_info = Description(
        title=_('Description of additional licenses'),
        required=False,
        description=_(
            "Description of licenses that do not appear in the list above."))

    def getExternalBugTracker():
        """Return the external bug tracker used by this bug tracker.

        If the product uses Launchpad, return None.
        If the product doesn't have a bug tracker specified, return the
        project bug tracker instead.
        """

    bugtracker = ProductBugTracker(
        title=_('Bugs are tracked'),
        vocabulary="BugTracker")

    sourcepackages = Attribute(_("List of packages for this product"))

    distrosourcepackages = Attribute(_("List of distribution packages for "
        "this product"))

    serieses = Attribute(_("""An iterator over the ProductSeries for this
        product"""))

    development_focus = Choice(
        title=_('Development focus'), required=True,
        vocabulary='FilteredProductSeries',
        description=_('The "trunk" series where development is focused'))

    name_with_project = Attribute(_("Returns the product name prefixed "
        "by the project name, if a project is associated with this "
        "product; otherwise, simply returns the product name."))

    releases = Attribute(_("""An iterator over the ProductReleases for this
        product."""))

    branches = Attribute(_("""An iterator over the Bazaar branches that are
    related to this product."""))

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

    requires_commercial_subscription = Attribute("""
        Whether the project's licensing requires a commercial
        subscription to use launchpad.""")

    is_permitted = Attribute("""
        Whether the project's licensing qualifies for free
        hosting or the project has an up-to-date subscription.""")

    license_approved = Attribute("""
        Whether a license is manually approved for free hosting
        after automatic approval fails.""")

    def redeemSubscriptionVoucher(voucher, registrant, purchaser,
                                  subscription_months, whiteboard=None):
        """Redeem a voucher and extend the subscription expiration date.

        The voucher must have already been verified to be redeemable.
        :param voucher: The voucher id as tracked in the external system.
        :param registrant: Who is redeeming the voucher.
        :param purchaser: Who purchased the voucher.  May not be known.
        :param subscription_months: integer indicating the number of months
            the voucher is for.
        :param whiteboard: Notes for this activity.
        :return: None
        """

    def getLatestBranches(quantity=5):
        """Latest <quantity> branches registered for this product."""

    def getPackage(distroseries):
        """Return a package in that distroseries for this product."""

    def newSeries(owner, name, summary, branch=None):
        """Creates a new ProductSeries for this product."""

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


class IProductSet(Interface):
    """The collection of products."""

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

    def getByName(name, default=None, ignore_inactive=False):
        """Return the product with the given name, ignoring inactive products
        if ignore_inactive is True.

        Return the default value if there is no such product.
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

    def createProduct(owner, name, displayname, title, summary,
                      description, project=None, homepageurl=None,
                      screenshotsurl=None, wikiurl=None,
                      downloadurl=None, freshmeatproject=None,
                      sourceforgeproject=None, programminglang=None,
                      reviewed=False, mugshot=None, logo=None,
                      icon=None, licenses=(), license_info=None):
        """Create and Return a brand new Product."""

    def forReview():
        """Return an iterator over products that need to be reviewed."""

    def search(text=None, soyuz=None,
               rosetta=None, malone=None,
               bazaar=None):
        """Search through the Registry database for products that match the
        query terms. text is a piece of text in the title / summary /
        description fields of product. soyuz, bazaar, malone etc are
        hints as to whether the search should be limited to products
        that are active in those Launchpad applications."""

    def latest(quantity=5):
        """Return the latest products registered in the Launchpad."""

    def getTranslatables():
        """Return an iterator over products that have resources translatables.
        """

    def featuredTranslatables(maximumproducts=8):
        """Return an iterator over a sample of translatable products.

        maximum_products is a maximum number of products to be displayed
        on the front page (it will be less if there are no enough products).
        """

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
