
# Zope schema imports
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from canonical.launchpad.fields import Title, Summary, Description

class IProduct(Interface):
    """A DOAP Product. DOAP describes the open source world as Projects
    and Products. Each Project may be responsible for several Products.
    For example, the Mozilla Project has Firefox, Thunderbird and The
    Mozilla App Suite as Products, among others."""
    
    # XXX Mark Shuttleworth comments: lets get rid of ID's in interfaces
    # unless we really need them. BradB says he can remove the need for them
    # in SQLObject soon. 12/10/04
    id = Int(title=_('The Product ID'))
    
    project = Int(title=_('Project ID.'), required=False)
    
    owner = Int(title=_('Owner'))

    name = TextLine(title=_('Name'), description=_("""The short name of this
        product, which must be unique among all the products from the same
        project."""))

    displayname = TextLine(title=_('Display Name'), description=_("""The
        display name of this product is the name of this product as it
        would appear in a paragraph of text."""))

    title = Title(title=_('Title'), description=_("""The product
    title. Should be just a few words."""))

    shortdesc = Summary(title=_('Summary'), description=_("""The summary should
        be a single short paragraph."""))

    description = Description(title=_('Description'), description=_("""The product
        description, may be several paragraphs of text, giving the product
        highlights and details."""))

    homepageurl = TextLine(title=_('Homepage URL'), required=False)

    wikiurl = TextLine(title=_('Wiki URL'), required=False)
    
    screenshotsurl = TextLine(title=_('Screenshots URL'), required=False)

    downloadurl = TextLine(title=_('Download URL'), required=False)

    programminglang = TextLine(title=_('Programming Language'),
        required=False)

    sourceforgeproject = TextLine(title=_('Sourceforge Project'),
        required=False)

    freshmeatproject = TextLine(title=_('Freshmeat Project'),
        required=False)

    manifest = Attribute(_('Manifest'))

    active = Bool(title=_('Active'), description=_("""Whether or not
        this product is considered active."""))
    
    reviewed = Bool(title=_('Reviewed'), description=_("""Whether or not
        this product has been reviewed."""))
    
    sourcesources = Attribute(_('Sources of source code. These are \
        pointers to the revision control system for that product, along \
        with status information about our ability to publish that \
        source in Arch.'))

    sourcepackages = Attribute(_("List of distribution packages for this \
        product"))

    packages = Attribute (_('SourcePackages related to a Product'))

    bugs = Attribute(
        """A list of ProductBugAssignments for this Product.""")

    serieslist = Attribute(_("""An iterator over the ProductSeries for this
        product"""))

    releases = Attribute(_("""An iterator over the ProductReleases for this
        product."""))

    bugsummary = Attribute(_("""A matrix by bug severity and status of the
        number of bugs of that severity and status assigned to this
        product."""))

    branches = Attribute(_("""An iterator over the Bazaar branches that are
    related to this product."""))

    def poTemplates():
        """Returns an iterator over this product's PO templates."""

    def poTemplatesToImport():
        """Returns all PO templates from this product that have a rawfile 
        pending of import into Rosetta."""

    def poTemplate(name):
        """Returns the PO template with the given name."""

    def newPOTemplate(person, name, title):
        """Creates a new PO template.

        Returns the newly created template.

        Raises an KeyError if a PO template with that name already exists.
        """

    def fullname():
        """Returns a name that uniquely identifies this product, by combining
            product name and project name
        """

    def newseries(form):
        """Creates a new ProductSeries for this series."""

    def newSourceSource(form):
        """Creates a new SourceSource entry for upstream code sync."""

    def messageCount():
        """Returns the number of Current IPOMessageSets in all templates
        inside this product."""

    def currentCount(language):
        """Returns the number of msgsets matched to a potemplate for this
        product that have a non-fuzzy translation in its PO file for this
        language when we last parsed it."""

    def updatesCount(language):
        """Returns the number of msgsets for this product where we have a
        newer translation in rosetta than the one in the PO file for this
        language, when we last parsed it."""

    def rosettaCount(language):
        """Returns the number of msgsets for all POTemplates in this Product
        where we have a translation in Rosetta but there was no translation
        in the PO file for this language when we last parsed it."""

    def getRelease(version):
        """Returns the release for this product that has the version
        given."""

    def packagedInDistros():
        """Returns the distributions this product has been packaged in."""



class IProductSet(Interface):
    """The collection of products."""

    def __iter__():
        """Return an iterator over all the products."""

    def __getitem__(name):
        """Get a product by its name."""

    def forReview():
        """Return an iterator over products that need to be reviewed."""

    def search(text=None, soyuz=None,
               rosetta=None, malone=None,
               buttress=None):
        """Search through the DOAP database for products that match the
        query terms. text is a piece of text in the title / summary /
        description fields of product. soyuz, buttress, malone etc are
        hints as to whether the search should be limited to products
        that are active in those Launchpad applications."""

