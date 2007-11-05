# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

from zope.interface import Attribute, Interface
from zope.schema import (
    Bool, Bytes, Choice, Datetime, Int, Object, Text, TextLine)

from canonical.launchpad.interfaces.launchpad import NotFoundError
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias
from canonical.launchpad.interfaces.distribution import IDistribution
from canonical.launchpad.interfaces.distroseries import IDistroSeries
from canonical.launchpad.interfaces.product import IProduct
from canonical.launchpad.interfaces.productseries import IProductSeries
from canonical.launchpad.interfaces.rosettastats import IRosettaStats
from canonical.launchpad.interfaces.sourcepackagename import (
    ISourcePackageName)
from canonical.launchpad.interfaces.translationfileformat import (
    TranslationFileFormat)
from canonical.launchpad import _
from canonical.lazr import DBEnumeratedType, DBItem


__metaclass__ = type

__all__ = [
    'IHasTranslationTemplates',
    'IPOTemplate',
    'IPOTemplateSet',
    'IPOTemplateSubset',
    'IPOTemplateWithContent',
    'LanguageNotFound',
    'TranslationPriority',
    ]


class LanguageNotFound(NotFoundError):
    """Raised when a a language does not exist in the database."""


class TranslationPriority(DBEnumeratedType):
    """Translation Priority

    Translations in Rosetta can be assigned a priority. This is used in a
    number of places. The priority stored on the translation itself is set
    by the upstream project maintainers, and used to identify the
    translations they care most about. For example, if Apache were nearing a
    big release milestone they would set the priority on those POTemplates
    to 'high'. The priority is also used by TranslationEfforts to indicate
    how important that POTemplate is to the effort. And lastly, an
    individual translator can set the priority on his personal subscription
    to a project, to determine where it shows up on his list.  """

    HIGH = DBItem(1, """
        High

        This translation should be shown on any summary list of translations
        in the relevant context. For example, 'high' priority projects show
        up on the home page of a TranslationEffort or Project in Rosetta.
        """)

    MEDIUM = DBItem(2, """
        Medium

        A medium priority POTemplate should be shown on longer lists and
        dropdowns lists of POTemplates in the relevant context.  """)

    LOW = DBItem(3, """
        Low

        A low priority POTemplate should only show up if a comprehensive
        search or complete listing is requested by the user.  """)


class IHasTranslationTemplates(Interface):
    """An entity that has translation templates attached.

    Examples include ISourcePackage, IDistribution, IDistroSeries, IProduct
    and IProductSeries.
    """

    def getCurrentTranslationTemplates():
        """Return an iterator over its active translation templates.

        A translation template is considered active when both
        `IPOTemplate`.iscurrent and `IDistribution`.official_rosetta flags
        are set to True.
        """

    def getObsoleteTranslationTemplates():
        """Return an iterator over its not active translation templates.

        A translation template is considered not active when any of
        `IPOTemplate`.iscurrent or `IDistribution`.official_rosetta flags
        are set to False.
        """

    def getTranslationTemplates():
        """Return an iterator over all its translation templates.

        The returned templates are either obsolete or current.
        """


class IPOTemplate(IRosettaStats):
    """A translation template."""

    id = Int(
        title=u"The translation template id.",
        required=True, readonly=True)

    name = TextLine(
        title=_("Template name"),
        description=_("The name of this PO template, for example "
            "'evolution-2.2'. Each translation template has a "
            "unique name in its package. It's important to get this "
            "correct, because Launchpad will recommend alternative "
            "translations based on the name."),
        required=True)

    translation_domain = Text(
        title=_("Template Name"),
        description=_("The translation domain for a translation template. "
            "Used with PO file format when generating MO files for inclusion "
            "in language pack or MO tarball exports."),
        required=True)

    description = Text(
        title=_("Description"),
        description=_("Please provide a brief description of the content "
            "of this translation template, for example, telling translators "
            "if this template contains strings for end-users or other "
            "developers."),
        required=False)

    header = Text(
        title=_('Header'),
        description=_("The standard template header in its native format."),
        required=True)

    iscurrent = Bool(
        title=_("Accept translations?"),
        description=_(
            "If unchecked, people can no longer change the template's "
            "translations."),
        required=True,
        default=True)

    owner = Choice(
        title=_("Owner"),
        required=True,
        description=_(
            "The owner of the template in Launchpad can edit the template "
            "and change it's status, and can also upload new versions "
            "of the template when a new release is made or when the "
            "translation strings have been changed during development."),
        vocabulary="ValidOwner")

    productseries = Choice(
        title=_("Series"),
        required=False,
        vocabulary="ProductSeries")

    distroseries = Choice(
        title=_("Series"),
        required=False,
        vocabulary="DistroSeries")

    sourcepackagename = Choice(
        title=_("Source Package Name"),
        description=_(
            "The source package that uses this template."),
        required=False,
        vocabulary="SourcePackageName")

    from_sourcepackagename = Choice(
        title=_("From Source Package Name"),
        description=_(
            "The source package this template comes from (set it only if it's"
            " different from the previous 'Source Package Name'."),
        required=False,
        vocabulary="SourcePackageName")

    sourcepackageversion = TextLine(
        title=_("Source Package Version"),
        required=False)

    binarypackagename = Choice(
        title=_("Binary Package"),
        description=_(
            "The package in which this template's translations are "
            "installed."),
        required=False,
        vocabulary="BinaryPackageName")

    languagepack = Bool(
        title=_("Include translations for this template in language packs?"),
        description=_(
            "Check this box if this template is part of a language pack so "
            "its translations should be exported that way."),
        required=True,
        default=False)

    path = TextLine(
        title=_("Path of the template in the source tree, including filename."),
        required=False)

    source_file = Object(
        title=_('Source file for this translation template'),
        readonly=True, schema=ILibraryFileAlias)

    source_file_format = Choice(
        title=_("File format for the source file"),
        required=False,
        vocabulary=TranslationFileFormat)

    priority = Int(
        title=_('Priority'),
        required=True,
        default=0,
        description=_(
            'A number that describes how important this template is. Often '
            'there are multiple templates, and you can use this as a way '
            'of indicating which are more important and should be '
            'translated first. Pick any number - higher priority '
            'templates will generally be listed first.'))

    datecreated = Datetime(
        title=_('When this translation template was created.'), required=True,
        readonly=True)

    translationgroups = Attribute(
        _('''
            The `ITranslationGroup` objects that handle translations for this
            template.
            There can be several because they can be inherited from project to
            product, for example.
            '''))

    translationpermission = Choice(
        title=_('Translation permission'),
        required=True,
        readonly=True,
        description=_('''
            The permission system which is used for this translation template.
            This is inherited from the product, project and/or distro in which
            the translation template is found.
            '''),
        vocabulary='TranslationPermission')

    pofiles = Attribute(
        _('All `IPOFile` that exist for this template.'))

    relatives_by_name = Attribute(
        _('All `IPOTemplate` objects that have the same name asa this one.'))

    relatives_by_source = Attribute(
        _('''All `IPOTemplate` objects that have the same source.
            For example those that came from the same productseries or the
            same source package.
            '''))

    displayname = TextLine(
        title=_('The translation template brief name.'), required=True,
        readonly=True)

    title = TextLine(
        title=_('The translation template title.'), required=True,
        readonly=True)

    product = Object(
        title=_('The `IProduct` to which this translation template belongs.'),
        required=False, readonly=True, schema=IProduct)

    distribution = Object(
        title=_(
            'The `IDistribution` to which this translation template belongs.'
            ),
        readonly=True, schema=IDistribution)

    language_count = Int(
        title=_('The number of languages for which we have translations.'),
        required=True, readonly=True)

    translationtarget = Attribute(
        _('''
            The direct object in which this template is attached.
            This will either be an `ISourcePackage` or an `IProductSeries`.
            '''))

    date_last_updated = Datetime(
            title=_('Date for last update'),
            required=True)

    def __iter__():
        """Return an iterator over current `IPOTMsgSet` in this template."""

    def getHeader():
        """Return an `ITranslationHeaderData` representing its header."""

    def getPOTMsgSetByMsgIDText(msgidtext, only_current=False, context=None):
        """Return the `IPOTMesgSet` indexed by msgidtext from this template.

        If the key is a string or a unicode object, returns the
        `IPOTMsgSet` in this template that has a primary message ID
        with the given text.

        If only_current is True, then get only current message sets.

        If context is not None, look for a message set with that context
        value.

        If no `IPOTMsgSet` is found, return None.
        """

    def getPOTMsgSetBySequence(sequence):
        """Return the `IPOTMsgSet` with the given sequence or None.

        :arg sequence: The sequence number when the `IPOTMsgSet` appears.

        The sequence number must be > 0.
        """

    def getPOTMsgSets(current=True, slice=None):
        """Return an iterator over `IPOTMsgSet` objects in this template.

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
        """Same as getPOTMsgSetByMsgIDText(), with only_current=True
        """

    def getPOTMsgSetByID(id):
        """Return the POTMsgSet object related to this POTemplate with the id.

        If there is no POTMsgSet with that id and for that POTemplate, return
        None.
        """

    def languages():
        """This Return the set of languages for which we have POFiles for
        this POTemplate.

        NOTE that variants are simply ignored, if we have three variants for
        en_GB we will simply return the one with variant=NULL.
        """

    def getPOFileByPath(path):
        """Get the PO file of the given path.

        Return None if there is no such `IPOFile`.
        """

    def getPOFileByLang(language_code, variant=None):
        """Get the PO file of the given language and (potentially)
        variant. If no variant is specified then the translation
        without a variant is given.

        Return None if there is no such POFile.
        """

    def hasPluralMessage():
        """Test whether this template has any message sets which are plural
        message sets."""

    def invalidateCache():
        """Invalidate the cached export for all pofiles."""

    def export():
        """Return a serialized version as a string using its native format."""

    def exportWithTranslations():
        """Return an ExportedTranslationFile using its native format.

        It include all translations available.
        """

    def expireAllMessages():
        """Mark all of our message sets as not current (sequence=0)"""

    def newPOFile(language_code, variant=None, requester=None):
        """Return a new `IPOFile` for the given language. The variant is
        optional.

        Raise LanguageNotFound if the language does not exist in the
        database.

        We should not have already an `IPOFile` for the given language_code and
        variant.
        """

    def getDummyPOFile(language_code, variant=None, requester=None):
        """Return a DummyPOFile if there isn't already a persistent `IPOFile`

        Raise `LanguageNotFound` if the language does not exist in the
        database.

        This method is designed to be used by read only actions. This way you
        only create a POFile when you actually need to store data.

        We should not have already a POFile for the given language_code and
        variant.
        """

    def createPOTMsgSetFromMsgIDs(msgid_singular, msgid_plural=None,
                                  context=None):
        """Creates a new template message in the database.

        :param msgid_singular: A reference to a singular msgid.
        :param msgid_plural: A reference to a plural msgid.  Can be None
        if the message is not a plural message.
        :param context: A context for the template message differentiating
        it from other template messages with exactly the same `msgid`.
        :return: The newly created message set.
        """

    def createMessageSetFromText(singular_text, plural_text, context=None):
        """Creates a new template message in the database using strings.

        Similar to createMessageSetFromMessageID, but takes text objects
        (unicode or string) along with textual context, rather than a
        message IDs.

        For non-plural messages, plural_text should be None.

        Returns the newly created message set.
        """

    def getNextToImport():
        """Return the next entry on the import queue to be imported."""

    def importFromQueue(logger=None):
        """Execute the import of the next entry on the queue, if needed.

        If a logger argument is given, any problem found with the
        import will be logged there.
        """


class IPOTemplateSubset(Interface):
    """A subset of POTemplate."""

    sourcepackagename = Object(
        title=_(
            'The `ISourcePackageName` associated with this subset.'),
        schema=ISourcePackageName)

    distroseries = Object(
        title=_(
            'The `IDistroSeries` associated with this subset.'),
        schema=IDistroSeries)

    productseries = Object(
        title=_(
            'The `IProductSeries` associated with this subset.'),
        schema=IProductSeries)

    title = TextLine(
        title=_('The translation file title.'), required=True, readonly=True)

    def __iter__():
        """Return an iterator over all POTemplate for this subset."""

    def __len__():
        """Return the number of `IPOTemplate` objects in this subset."""

    def __getitem__(name):
        """Get a POTemplate by its name."""

    def new(name, translation_domain, title, contents, owner):
        """Create a new template for the context of this Subset."""

    def getPOTemplateByName(name):
        """Return the `IPOTemplate` with the given name or None.

        The `IPOTemplate` is restricted to this concrete `IPOTemplateSubset`.
        """

    def getPOTemplateByTranslationDomain(translation_domain):
        """Return the `IPOTemplate` with the given translation_domain or None.

        The `IPOTemplate` is restricted to this concrete `IPOTemplateSubset`.
        """

    def getPOTemplateByPath(path):
        """Return the `IPOTemplate` from this subset that has the given path.

        Return None if there is no such `IPOTemplate`.
        """

    def getAllOrderByDateLastUpdated():
        """Return an iterator over all POTemplate for this subset.

        The iterator will give entries sorted by modification.
        """

    def getClosestPOTemplate(path):
        """Return a `IPOTemplate` with a path closer to the given path or None.

        If there is no `IPOTemplate` with a common path with the given argument,
        or if there are more than one `IPOTemplate` with the same common path,
        and both are the closer ones, returns None.
        """


class IPOTemplateSet(Interface):
    """A set of PO templates."""

    def __iter__():
        """Return an iterator over all PO templates."""

    def getByIDs(ids):
        """Return all PO templates with the given IDs."""

    def getAllByName(name):
        """Return a list with all PO templates with the given name."""

    def getAllOrderByDateLastUpdated():
        """Return an iterator over all POTemplate sorted by modification."""

    def getSubset(distroseries=None, sourcepackagename=None,
                  productseries=None):
        """Return a POTemplateSubset object depending on the given arguments.
        """

    def getSubsetFromImporterSourcePackageName(
        distroseries, sourcepackagename):
        """Return a POTemplateSubset based on the origin sourcepackagename.
        """

    def getPOTemplateByPathAndOrigin(path, productseries=None,
        distroseries=None, sourcepackagename=None):
        """Return an `IPOTemplate` that is stored at 'path' in source code and
           came from the given arguments.

        Return None if there is no such `IPOTemplate`.
        """


class IPOTemplateWithContent(IPOTemplate):
    """Interface for an `IPOTemplate` used to create the new POTemplate form."""

    content = Bytes(
        title=_("PO Template File to Import"),
        required=True)
