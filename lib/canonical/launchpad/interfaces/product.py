
# Zope schema imports
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

class IProduct(Interface):
    """A DOAP Product. DOAP describes the open source world as Projects
    and Products. Each Project may be responsible for several Products.
    For example, the Mozilla Project has Firefox, Thunderbird and The
    Mozilla App Suite as Products, among others."""
    
    # XXX Mark Shuttleworth comments: lets get rid of ID's in interfaces
    # unless we really need them. BradB says he can remove the need for them
    # in SQLObject soon. 12/10/04
    id = Int(title=_('The Product ID'))
    
    project = Int(title=_('The Project that is responsible for this product.'))
    
    owner = Int(title=_('Owner'))

    name = TextLine(title=_('The short name of this product, which must be \
        unique among all the products from the same project.'))

    displayname = TextLine(title=_('The display name of this product, is \
        the name of this product as it would appear in a paragraph of text.'))

    title = TextLine(title=_('The product title. Should be just a few words.'))

    shortdesc = Text(title=_('A short description, should be a single \
        short paragraph.'))

    description = Text(title=_('The product description, may be several\
        paragraphs of text, giving the product highlights and details.'))

    homepageurl = TextLine(title=_('A Homepage URL for this product.'))

    manifest = TextLine(title=_('Manifest'))

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

    def poTemplate(name):
        """Returns the PO template with the given name."""

    def newPOTemplate(person, name, title):
        """Creates a new PO template.

        Returns the newly created template.

        Raises an KeyError if a PO template with that name already exists.
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


