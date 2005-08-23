# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Interfaces including and related to IProduct."""

__metaclass__ = type

__all__ = [
    'IProduct',
    'IProductSet',
    ]

from zope.schema import Bool, Choice, Int, Text, TextLine
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory

from canonical.launchpad.fields import Title, Summary, Description
from canonical.launchpad.interfaces import IHasOwner, IBugTarget
from canonical.launchpad.validators.name import name_validator

_ = MessageIDFactory('launchpad')

class IProduct(IHasOwner, IBugTarget):
    """A Hatchery Product.

    TheHatchery describes the open source world as Projects and
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
        description=_("""Optional related Project.
            Used to group similar products in a coherent way."""))

    owner = Choice(
        title=_('Owner'),
        required=True,
        vocabulary='ValidOwner',
        description=_("""Product owner, it can either a valid Person or Team
            inside Launchpad context."""))

    name = TextLine(
        title=_('Name'),
        constraint=name_validator,
        description=_("""The short name of this product, which must be
            unique among all the products. It should be at least one
            lowercase letters or number followed by one or more chars,
            numbers, plusses, dots or hyphens and will be part of the url
            to this product in the Launchpad."""))

    displayname = TextLine(
        title=_('Display Name'),
        description=_("""The display name of this product is the name of
            this product as it would appear in a paragraph of text."""))

    title = Title(
        title=_('Title'),
        description=_("""The product title. Should be just a few words."""))

    summary = Summary(
        title=_('Summary'),
        description=_("""The summary should be a single short paragraph."""))

    description = Description(
        title=_('Description'),
        description=_("""The product description, may be several paragraphs
            of text, giving the product highlights and details."""))

    datecreated = TextLine(
        title=_('Date Created'),
        description=_("""The date this product was created in Launchpad."""))

    homepageurl = TextLine(
        title=_('Homepage URL'),
        required=False,
        description=_("""The product home page. Please include 
            the http://"""))

    wikiurl = TextLine(
        title=_('Wiki URL'),
        required=False,
        description=_("""The URL of this product's wiki, if it has one.
            Please include the http://"""))

    screenshotsurl = TextLine(
        title=_('Screenshots URL'),
        required=False,
        description=_("""The location of screenshots of this product.
            Please include the http://"""))

    downloadurl = TextLine(
        title=_('Download URL'),
        required=False)

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

    sourcepackages = Attribute(_("List of distribution packages for this \
        product"))

    bugtasks = Attribute(
        """A list of BugTasks for this Product.""")

    serieslist = Attribute(_("""An iterator over the ProductSeries for this
        product"""))


    name_with_project = Attribute(_("Returns the product name prefixed "
        "by the project name, if a project is associated with this "
        "product; otherwise, simply returns the product name."))

    releases = Attribute(_("""An iterator over the ProductReleases for this
        product."""))

    bugsummary = Attribute(_("""A matrix by bug severity and status of the
        number of bugs of that severity and status assigned to this
        product."""))

    branches = Attribute(_("""An iterator over the Bazaar branches that are
    related to this product."""))

    milestones = Attribute(_(
        """The release milestones associated with this product, useful in
        particular to the maintainer, for organizing which bugs will be fixed
        when."""))

    bounties = Attribute(_("The bounties that are related to this product."))

    translatable_packages = Attribute(
        "A list of the source packages for this product that can be"
        " translated sorted by distrorelease.name and sourcepackage.name.")

    translatable_series = Attribute(
        "A list of the series of this product for which we have translation"
        " templates.")

    primary_translatable = Attribute(
        "The best guess we have for what new translators will want to"
        " translate for a given product. First, tries the current development"
        " Ubuntu package. Then tries the latest series for which we have"
        " potemplates.")

    translationgroups = Attribute("The list of applicable translation "
        "groups for a product. There can be several: one from the product, "
        "and potentially one from the project, too.")

    aggregatetranslationpermission = Attribute("The translation permission "
        "that applies to translations in this product, based on the "
        "permissions that apply to the product as well as its project.")

    releaseroot = Text(title=_("The URL of the root directory for the product "
        "used when the series doesn't supply one."))

    def getPackage(distrorelease):
        """Return a package in that distrorelease for this product."""

    def getMilestone(name):
        """Return a milestone with the given name for this product, or
        raise NotFoundError.
        """

    def newSeries(name, displayname, summary):
        """Creates a new ProductSeries for this series."""

    def getSeries(name):
        """Returns the series for this product that has the name given."""

    def getRelease(version):
        """Returns the release for this product that has the version
        given."""

    def packagedInDistros():
        """Returns the distributions this product has been packaged in."""

    def ensureRelatedBounty(bounty):
        """Ensure that the bounty is linked to this product. Return None.
        """


class IProductSet(Interface):
    """The collection of products."""

    title = Attribute("""The set of Products registered in the Launchpad""")

    def __iter__():
        """Return an iterator over all the products."""

    def __getitem__(name):
        """Get a product by its name."""

    def get(productid):
        """Get a product by its id.

        If the product can't be found a zope.exceptions.NotFoundError will be
        raised.
        """

    def createProduct(owner, name, displayname, title, summary,
                      description, project=None, homepageurl=None,
                      screenshotsurl=None, wikiurl=None,
                      downloadurl=None, freshmeatproject=None,
                      sourceforgeproject=None):
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
        in malone."""

    def count_reviewed(self):
        """return a count of the number of products in the Launchpad that
        are both active and reviewed."""
