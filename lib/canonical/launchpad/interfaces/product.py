# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Interfaces including and related to IProduct."""

__metaclass__ = type

__all__ = [
    'IProduct',
    'IProductSet',
    'IProductLaunchpadUsageForm',
    ]

from zope.schema import Bool, Choice, Int, Text, TextLine
from zope.interface import Interface, Attribute

from canonical.launchpad import _
from canonical.launchpad.fields import (
    Description, ProductBugTracker, Summary, Title, URIField)
from canonical.launchpad.interfaces import (
    IHasAppointedDriver, IHasOwner, IHasDrivers, IBugTarget,
    ISpecificationTarget, IHasSecurityContact, IKarmaContext, PillarNameField)
from canonical.launchpad.validators.name import name_validator
from canonical.launchpad.interfaces.mentoringoffer import IHasMentoringOffers
from canonical.launchpad.fields import (
    LargeImageUpload, BaseImageUpload, SmallImageUpload)


class ProductNameField(PillarNameField):

    @property
    def _content_iface(self):
        return IProduct


class IProduct(IHasAppointedDriver, IHasDrivers, IHasOwner, IBugTarget,
               ISpecificationTarget, IHasSecurityContact, IKarmaContext,
               IHasMentoringOffers):
    """A Product.

    The Launchpad Registry describes the open source world as Projects and
    Products. Each Project may be responsible for several Products.
    For example, the Mozilla Project has Firefox, Thunderbird and The
    Mozilla App Suite as Products, among others.
    """

    # XXX Mark Shuttleworth comments: lets get rid of ID's in interfaces
    # unless we really need them. BradB says he can remove the need for them
    # in SQLObject soon. 12/10/04
    id = Int(title=_('The Product ID'))

    project = Choice(
        title=_('Project'),
        required=False,
        vocabulary='Project',
        description=_("""Optional project. In Launchpad, a "Project" is a
            group that produces several related products. For example, the
            Mozilla Project produces Firefox, Thunderbird and Gecko. This
            information is used to group those products in a coherent way.
            If you make this product part of a group, the group preferences
            and decisions around bug tracking, translation and security
            policy will apply to this product."""))

    owner = Choice(
        title=_('Owner'),
        required=True,
        vocabulary='ValidOwner',
        description=_("""Product owner, it can either a valid Person or Team
            inside Launchpad context."""))

    bugcontact = Choice(
        title=_("Bug Contact"),
        description=_(
            "The person or team who will receive all bugmail for this "
            "product"),
        required=False, vocabulary='ValidPersonOrTeam')

    driver = Choice(
        title=_("Driver"),
        description=_(
            "This person or team will be able to set feature goals for "
            "and approve bug targeting or backporting for ANY major series "
            "in this product. You might want to leave this blank and just "
            "appoint a team for each specific series, rather than having "
            "one product team that does it all."),
        required=False, vocabulary='ValidPersonOrTeam')

    drivers = Attribute(
        "Presents the drivers of this product as a list. A list is "
        "required because there might be a product driver and a project "
        "driver.")

    name = ProductNameField(
        title=_('Name'),
        constraint=name_validator,
        description=_("""At least one lowercase letter or number, followed by
            letters, dots, hyphens or plusses.
            Keep this name short, as it is used in URLs."""))

    displayname = TextLine(
        title=_('Display Name'),
        description=_("""The name of the product as it would appear in a paragraph."""))

    title = Title(
        title=_('Title'),
        description=_("""The product title. Should be just a few words."""))

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
        description=_("""The date this product was created in Launchpad."""))

    homepageurl = URIField(
        title=_('Homepage URL'),
        required=False,
        allowed_schemes=['http', 'https', 'ftp'], allow_userinfo=False,
        description=_("""The product home page. Please include
            the http://"""))

    wikiurl = URIField(
        title=_('Wiki URL'),
        required=False,
        allowed_schemes=['http', 'https', 'ftp'], allow_userinfo=False,
        description=_("""The full URL of this product's wiki, if it has one.
            Please include the http://"""))

    screenshotsurl = URIField(
        title=_('Screenshots URL'),
        required=False,
        allowed_schemes=['http', 'https', 'ftp'], allow_userinfo=False,
        description=_("""The full URL for screenshots of this product,
            if available. Please include the http://"""))

    downloadurl = URIField(
        title=_('Download URL'),
        required=False,
        allowed_schemes=['http', 'https', 'ftp'], allow_userinfo=False,
        description=_("""The full URL where downloads for this product
            are located, if available. Please include the http://"""))

    programminglang = TextLine(
        title=_('Programming Language'),
        required=False,
        description=_("""A comma delimited list of programming
            languages used to produce this product."""))

    sourceforgeproject = TextLine(title=_('Sourceforge Project'),
        required=False,
        description=_("""The SourceForge project name for
            this product, if it is in sourceforge."""))

    freshmeatproject = TextLine(title=_('Freshmeat Project'),
        required=False, description=_("""The Freshmeat project name for
            this product, if it is in freshmeat."""))

    homepage_content = Text(
        title=_("Homepage Content"), required=False,
        description=_(
            "The content of this product's home page. Edit this and it will "
            "be displayed for all the world to see. It is NOT a wiki "
            "so you cannot undo changes."))

    emblem = SmallImageUpload(
        title=_("Emblem"), required=False,
        description=_(
            "A small image, max 16x16 pixels and 25k in file size, that can "
            "be used to refer to this product."))

    # This field should not be used on forms, so we use a BaseImageUpload here
    # only for documentation purposes.
    gotchi_heading = BaseImageUpload(
        title=_("Heading icon"), required=False,
        description=_(
            "An image, maximum 64x64 pixels, that will be displayed on "
            "the header of all pages related to this product. It should be "
            "no bigger than 50k in size."))

    gotchi = LargeImageUpload(
        title=_("Icon"), required=False,
        description=_(
            "An image, maximum 170x170 pixels, that will be displayed on "
            "this product's home page. It should be no bigger than 100k in "
            "size. "))

    translationgroup = Choice(
        title = _("Translation group"),
        description = _("The translation group for this product. This group "
            "is made up of a set of translators for all the languages "
            "approved by the group manager. These translators then have "
            "permission to edit the groups translation files, based on the "
            "permission system selected below."),
        required=False,
        vocabulary='TranslationGroup')

    translationpermission = Choice(
        title=_("Translation Permission System"),
        description=_("The permissions this group requires for "
            "translators. If 'Open', then anybody can edit translations "
            "in any language. If 'Reviewed', then anybody can make "
            "suggestions but only the designated translators can edit "
            "or confirm translations. And if 'Closed' then only the "
            "designated translation group will be able to touch the "
            "translation files at all."),
        required=True,
        vocabulary='TranslationPermission')

    autoupdate = Bool(title=_('Automatic update'),
        description=_("""Whether or not this product's attributes are
        updated automatically."""))

    active = Bool(title=_('Active'), description=_("""Whether or not
        this product is considered active."""))

    reviewed = Bool(title=_('Reviewed'), description=_("""Whether or not
        this product has been reviewed."""))

    def getExternalBugTracker():
        """Return the external bug tracker used by this bug tracker.

        If the product uses Malone, return None.
        If the product doesn't have a bug tracker specified, return the
        project bug tracker instead.
        """

    bugtracker = Choice(title=_('Bug Tracker'), required=False,
        vocabulary='BugTracker',
        description=_(
            "The external bug tracker this product uses, if it's different"
            " from its Project's bug tracker."))

    official_malone = Bool(title=_('Uses Malone Officially'),
        required=True, description=_('Check this box to indicate that '
        'this application officially uses Malone for bug tracking '
        'upstream. This will remove the caution from the product page.'
        ))

    official_rosetta = Bool(title=_('Uses Rosetta Officially'),
        required=True, description=_('Check this box to indicate that '
        'this application officially uses Rosetta for upstream '
        'translation. This will remove the caution from the '
        'pages for this product in Launchpad.'))

    sourcepackages = Attribute(_("List of distribution packages for this \
        product"))

    serieslist = Attribute(_("""An iterator over the ProductSeries for this
        product"""))

    development_focus = Choice(
        title=_('Development focus'), required=True,
        vocabulary='FilteredProductSeries',
        description=_('The product series where development is focused'))

    name_with_project = Attribute(_("Returns the product name prefixed "
        "by the project name, if a project is associated with this "
        "product; otherwise, simply returns the product name."))

    releases = Attribute(_("""An iterator over the ProductReleases for this
        product."""))

    branches = Attribute(_("""An iterator over the Bazaar branches that are
    related to this product."""))

    milestones = Attribute(_(
        """The release milestones associated with this product, useful in
        particular to the maintainer, for organizing which bugs will be fixed
        when."""))

    bounties = Attribute(_("The bounties that are related to this product."))

    translatable_packages = Attribute(
        "A list of the source packages for this product that can be "
        "translated sorted by distrorelease.name and sourcepackage.name.")

    translatable_series = Attribute(
        "A list of the series of this product for which we have translation "
        "templates.")

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

    def getLatestBranches(quantity=5):
        """Latest <quantity> branches registered for this product."""

    def getPackage(distrorelease):
        """Return a package in that distrorelease for this product."""

    def getMilestone(name):
        """Return a milestone with the given name for this product, or
        None.
        """

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

    def newBranch(name, title, url, home_page, lifecycle_status, summary,
                  whiteboard):
        """Create a new Branch for this product."""


class IProductSet(Interface):
    """The collection of products."""

    title = Attribute("""The set of Products registered in the Launchpad""")

    def __iter__():
        """Return an iterator over all the products."""

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

    def getProductsWithBranches():
        """Return an iterator over all products that have branches."""
        
    def createProduct(owner, name, displayname, title, summary,
                      description, project=None, homepageurl=None,
                      screenshotsurl=None, wikiurl=None,
                      downloadurl=None, freshmeatproject=None,
                      sourceforgeproject=None, programminglang=None,
                      reviewed=False, gotchi=None, gotchi_heading=None,
                      emblem=None):
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

    def translatables():
        """Return an iterator over products that have resources translatables.
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
        in Malone."""

    def count_featureful():
        """Return the number of products that have specs associated with
        them in Blueprint."""

    def count_reviewed():
        """return a count of the number of products in the Launchpad that
        are both active and reviewed."""


class IProductLaunchpadUsageForm(Interface):
    """Form for indicating whether Rosetta or Malone is used."""

    official_rosetta = IProduct['official_rosetta']
    bugtracker = ProductBugTracker(
        title=_('Bug Tracker'),
        description=_('Where are bugs primarily tracked?'),
        vocabulary="BugTracker")
