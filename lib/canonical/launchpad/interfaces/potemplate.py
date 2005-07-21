# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from zope.interface import Interface, Attribute
from zope.schema import Bool, Choice, Text, TextLine, Bytes

from canonical.launchpad.interfaces.rawfiledata import ICanAttachRawFileData
from canonical.launchpad.interfaces.rosettastats import IRosettaStats

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

__metaclass__ = type

__all__ = (
    'LanguageNotFound', 'IPOTemplateSubset', 'IPOTemplateSet', 'IPOTemplate',
    'IEditPOTemplate', 'IPOTemplateWithContent')

class LanguageNotFound(ValueError):
    """Raised when a a language does not exist in the database."""

class IPOTemplate(IRosettaStats, ICanAttachRawFileData):
    """A PO template. For example 'nautilus/po/nautilus.pot'."""

    id = Attribute("A unique ID number")

    potemplatename = Choice(
        title=_("Template Name"),
        description=_("The name of this PO template, for example "
            "'evolution-2.2'. Each translation template has a "
            "unique name in its package. It's important to get this "
            "correct, because Rosetta will recommend alternative "
            "translations based on the name."),
        required=True,
        vocabulary="POTemplateName")

    name = TextLine(
        title=_("Template name"),
        readonly=True)

    description = Text(
        title=_("Description"),
        description=_("Please provide a brief description of the content "
            "of this translation template, for example, telling translators "
            "if this template contains strings for end-users or other "
            "developers."),
        required=False)

    header = Text(
        title=_('Header'),
        description=_(
            "The standard template header as gettext creates it. It's used to"
            " get some default values when creating a new PO file."),
        required=True)

    iscurrent = Bool(
        title=_("Accept translations?"),
        description=_(
            "If unchecked, people can no longer change the template's"
            " translations."),
        required=True,
        default=True)

    owner = Choice(
        title=_("Owner"),
        required=True,
        description=_(
            "The owner of the template in Rosetta can edit the template "
            "and change it's status, and can also upload new versions "
            "of the template when a new release is made or when the "
            "translation strings have been changed during development."),
        vocabulary="ValidOwner")

    productseries = Choice(
        title=_("Product Branch or Series"),
        required=False,
        vocabulary="ProductSeries")

    distrorelease = Choice(
        title=_("Distribution Release"),
        required=False,
        vocabulary="DistroRelease")

    sourcepackagename = Choice(
        title=_("Source Package Name"),
        description=_(
            "The source package this template comes from."),
        required=False,
        vocabulary="SourcePackageName")

    sourcepackageversion = TextLine(
        title=_("Source Package Version"),
        required=False)

    binarypackagename = Choice(
        title=_("Binary Package"),
        description=_(
            "The package in which this template's translations are installed."
            ),
        required=False,
        vocabulary="BinaryPackageName")

    languagepack = Bool(
        title=_("Include translations for this template in language packs?"),
        description=_(
            "Check this box if this template is part of a language pack so"
            "its translations should be exported that way."),
        required=True,
        default=False)

    path = TextLine(
        title=_("Path of the template in the source tree"),
        required=False)

    filename = TextLine(
        title=_("Filename of template in the source tree"),
        required=False)

    priority = Attribute("The template priority.")

    copyright = Attribute("The copyright information for this template.")

    license = Attribute("The license that applies to this template.")

    datecreated = Attribute("When this template was created.")

    translationgroups = Attribute("The translation groups that have "
        "been selected to apply to this template. There can be several "
        "because they can be inherited from project to product, for "
        "example.")

    translationpermission = Attribute("The permission system which "
        "is used for this potemplate. This is inherited from the product, "
        "project and/or distro in which the pofile is found.")

    pofiles = Attribute("An iterator over the PO files that exist for "
        "this template.")

    relatives_by_name = Attribute("An iterator over other PO templates "
        "that have the same potemplate name as this one.")

    relatives_by_source = Attribute("An iterator over other PO templates "
        "that have the same source, for example those that came from the "
        "same productseries or the same source package.")

    displayname = Attribute("A brief name for this template, generated.")

    title = Attribute("A title for this template, generated.")

    language_count = Attribute("The number of languages for which we have "
        "some number of translations.")

    translationtarget = Attribute("The object for which this template is "
        "a translation. This will either be a SourcePackage or a Product "
        "Series.")

    def __len__():
        """Return the number of Current IPOTMsgSets in this template."""

    def __iter__():
        """Return an iterator over current IPOTMsgSets in this template."""

    def getPOTMsgSetByMsgIDText(msgidtext, onlyCurrent=False):
        """Extract one IPOTMesgSet from this template.

        If the key is a string or a unicode object, returns the
        IPOTMsgSet in this template that has a primary message ID
        with the given text.

        If onlyCurrent is True, then get only current message sets.

        If no IPOTMsgSet is found, raises NotFoundError.
        """

    def getPOTMsgSetBySequence(slice, onlyCurrent=False):
        """Extract one or several POTMessageSets from this template.

        Return the message IDs by sequence within the given slice.

        If onlyCurrent is True, then get only current message sets.
        """

    def getPOTMsgSets(current=True, slice=None):
        """Return an iterator over IPOTMsgSet objects in this template.

        The 'current' argument is used to select only current POTMsgSets or
        all of them.
        'slice' is a slice object that selects a subset of POTMsgSets.
        """

    def getPOTMsgSetsCount(current=True):
        """Return the number of POTMsgSet objects related to this object.

        The current argument is used to select only current POTMsgSets or all
        of them.
        """

    def __getitem__(key):
        """Same as getPOTMsgSetByMsgIDText(), with onlyCurrent=True
        """

    def getPOTMsgSetByID(id):
        """Return the POTMsgSet object related to this POTemplate with the id.

        If there is no POTMsgSet with that id and for that POTemplate, return
        None.
        """

    def languages():
        """Return an iterator over languages that this template's messages are
        translated into.
        """

    def poFilesToImport():
        """Returns all PO files from this POTemplate that have a rawfile 
        pending of import into Rosetta."""

    def getPOFileByLang(language_code, variant=None):
        """Get the PO file of the given language and (potentially)
        variant. If no variant is specified then the translation
        without a variant is given.

        Raises KeyError if there is no such POFile."""

    def queryPOFileByLang(language_code, variant=None):
        """Return a PO file for this PO template in the given language, if
        it exists, or None if it does not."""

    def hasMessageID(msgid):
        """Check whether a message set with the given message ID exists within
        this template."""

    def hasPluralMessage():
        """Test whether this template has any message sets which are plural
        message sets."""

    def invalidateCache():
        """Invalidate the cached export for all pofiles."""


class IEditPOTemplate(IPOTemplate):
    """Edit interface for an IPOTemplate."""

    sourcepackagename = Attribute("""The name of the sourcepackage from where
        this PO template is.""")

    distrorelease = Attribute("""The distribution where this PO template
        belongs""")

    def expireAllMessages():
        """Mark all of our message sets as not current (sequence=0)"""

    #def makeMessageSet(messageid_text, pofile=None):
    #    """Add a message set to this template.  Primary message ID
    #    is 'messageid_text'.
    #    If one already exists, a KeyError is raised."""

    def getOrCreatePOFile(language_code, variant=None, owner=None):
        """Create and return a new po file in the given language. The
        variant is optional.

        Raises LanguageNotFound if the language does not exist in the
        database.
        """

    def createMessageSetFromMessageID(msgid):
        """Creates in the database a new message set.

        As a side-effect, creates a message ID sighting in the database for the
        new set's prime message ID.

        Returns the newly created message set.
        """

    def createMessageSetFromText(text):
        """Creates in the database a new message set.

        Similar to createMessageSetFromMessageID, but takes a text object
        (unicode or string) rather than a message ID.

        Returns the newly created message set.
        """


class IPOTemplateSubset(Interface):
    """A subset of POTemplate."""

    sourcepackagename = Attribute(
        "The sourcepackagename associated with this subset of POTemplates.")

    distrorelease = Attribute(
        "The distrorelease associated with this subset of POTemplates.")

    productseries = Attribute(
        "The productseries associated with this subset of POTemplates.")

    title = Attribute("Title - use for launchpad pages")

    def __iter__():
        """Returns an iterator over all POTemplate for this subset."""

    def __getitem__(name):
        """Get a POTemplate by its name."""

    def new(potemplatename, title, contents, owner):
        """Create a new template for the context of this Subset."""


class IPOTemplateSet(Interface):
    """A set of PO templates."""

    def __iter__():
        """Return an iterator over all PO templates."""

    def __getitem__(name):
        """Get a PO template by its name."""

    def getSubset(distrorelease=None, sourcepackagename=None,
                  productseries=None):
        """Return a POTemplateSubset object depending on the given arguments.
        """

    def getTemplatesPendingImport():
        """Return a list of PO templates that have data to be imported."""


class IPOTemplateWithContent(IEditPOTemplate):
    """Interface for an IPOTemplate used to create the new POTemplate form."""

    content = Bytes(
        title=_("PO Template File to Import"),
        required=True)
