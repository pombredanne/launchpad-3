# Copyright 2005-2007 Canonical Ltd. All rights reserved.

from zope.interface import Interface, Attribute
from zope.schema import Bool, Choice, TextLine, Datetime, Field

from canonical.launchpad import _
from canonical.lazr import DBEnumeratedType, DBItem

__metaclass__ = type

__all__ = [
    'ITranslationImportQueueEntry',
    'ITranslationImportQueue',
    'IEditTranslationImportQueueEntry',
    'IHasTranslationImports',
    'RosettaImportStatus',
    ]


class RosettaImportStatus(DBEnumeratedType):
    """Rosetta Import Status

    Define the status of an import on the Import queue. It could have one
    of the following states: approved, imported, deleted, failed, needs_review
    or blocked.
    """

    APPROVED = DBItem(1, """
        Approved

        The entry has been approved by a Rosetta Expert or was able to be
        approved by our automatic system and is waiting to be imported.
        """)

    IMPORTED = DBItem(2, """
        Imported

        The entry has been imported.
        """)

    DELETED = DBItem(3, """
        Deleted

        The entry has been removed before being imported.
        """)

    FAILED = DBItem(4, """
        Failed

        The entry import failed.
        """)

    NEEDS_REVIEW = DBItem(5, """
        Needs Review

        A Rosetta Expert needs to review this entry to decide whether it will
        be imported and where it should be imported.
        """)

    BLOCKED = DBItem(6, """
        Blocked

        The entry has been blocked to be imported by a Rosetta Expert.
        """)


class ITranslationImportQueueEntry(Interface):
    """An entry of the Translation Import Queue."""

    id = Attribute('The entry ID')

    path = TextLine(
        title=_("Path"),
        description=_(
            "The path to this file inside the source tree. Includes the"
            " filename."),
        required=True)

    importer = Choice(
        title=_("Importer"),
        required=True,
        description=_(
            "The person that imported this file in Launchpad."),
        vocabulary="ValidOwner")

    dateimported = Datetime(
        title=_("The timestamp when this file was imported."),
        required=True)

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
            "The source package from where this entry comes."),
        required=False,
        vocabulary="SourcePackageName")

    is_published = Bool(
        title=_("This import comes from a published file"),
        description=_(
            "If checked, this import will be handled as already published."),
        required=True,
        default=False)

    content = Attribute(
        "An ILibraryFileAlias reference with the file content. Must not be"
        " None.")

    format = Choice(
        title=_('The file format of the import.'),
        vocabulary='TranslationFileFormat',
        required=True, readonly=True)

    status = Choice(
        title=_("The status of the import."),
        values=RosettaImportStatus.items,
        required=True)

    date_status_changed = Datetime(
        title=_("The timestamp when the status was changed."),
        required=True)

    sourcepackage = Attribute("The sourcepackage associated with this entry.")

    guessed_potemplate = Attribute(
        "The IPOTemplate that we can guess this entry could be imported into."
        " None if we cannot guess it.")

    import_into = Attribute("The Object where this entry will be imported. Is"
        " None if we don't know where to import it.")

    pofile = Field(
        title=_("The IPOfile where this entry should be imported."),
        required=False)

    potemplate = Field(
        title=_("The IPOTemplate associated with this entry."),
        description=_("The IPOTemplate associated with this entry. If path"
        " notes a .pot file, it should be used as the place where this entry"
        " will be imported, if it's a .po file, it indicates the template"
        " associated with tha translation."),
        required=False)

    def getGuessedPOFile():
        """Return an IPOFile that we think this entry should be imported into.

        Return None if we cannot guess it."""

    def getFileContent():
        """Return the imported file content as a stream."""

    def getTemplatesOnSameDirectory():
        """Return import queue entries stored on the same directory as self.

        The returned entries will be only .pot entries.
        """

    def getElapsedTimeText():
        """Return a string representing the elapsed time since we got the file.

        The returned string is like:
            '2 days 3 hours 10 minutes ago' or 'just requested'
        """


class ITranslationImportQueue(Interface):
    """A set of files to be imported into Rosetta."""

    def __iter__():
        """Iterate over all entries in the queue."""

    def __getitem__(id):
        """Return the ITranslationImportQueueEntry with the given id.

        If there is not entries with that id, the NotFoundError exception is
        raised.
        """

    def entryCount():
        """Return the number of TranslationImportQueueEntry records."""

    def iterNeedReview():
        """Iterate over all entries in the queue that need review."""

    def addOrUpdateEntry(path, content, is_published, importer,
        sourcepackagename=None, distroseries=None, productseries=None,
        potemplate=None, pofile=None, format=None):
        """Return a new or updated entry of the import queue.

        :arg path: is the path, with the filename, of the file imported.
        :arg content: is the file content.
        :arg is_published: indicates if the imported file is already published
            by upstream.
        :arg importer: is the person that did the import.
        :arg sourcepackagename: is the link of this import with source
            package.
        :arg distroseries: is the link of this import with a distribution.
        :arg productseries: is the link of this import with a product branch.
        :arg potemplate: is the link of this import with an IPOTemplate.
        :arg pofile: is the link of this import with an IPOFile.
        :arg format: a TranslationFileFormat.

        sourcepackagename + distroseries and productseries are exclusive, we
        must have only one combination of them.
        """

    def addOrUpdateEntriesFromTarball(content, is_published, importer,
        sourcepackagename=None, distroseries=None, productseries=None,
        potemplate=None):
        """Add all .po or .pot files from the tarball at :content:.

        :arg content: is a tarball stream.
        :arg is_published: indicates if the imported file is already published
            by upstream.
        :arg importer: is the person that did the import.
        :arg sourcepackagename: is the link of this import with source
            package.
        :arg distroseries: is the link of this import with a distribution.
        :arg productseries: is the link of this import with a product branch.
        :arg potemplate: is the link of this import with an IPOTemplate.

        sourcepackagename + distroseries and productseries are exclusive, we
        must have only one combination of them.

        Return the number of files attached.
        """

    def get(id):
        """Return the ITranslationImportQueueEntry with the given id or None.
        """

    def getAllEntries(target=None, import_status=None, file_extension=None):
        """Return all entries this import queue has

        :arg target: IPerson, IProduct, IProductSeries, IDistribution,
            IDistroSeries or ISourcePackage the import entries are attached to
            or None to get all entries available.
        :arg import_status: RosettaImportStatus entry.
        :arg file_extension: String with the file type extension, usually 'po'
            or 'pot'.

        If any of target, status or file_extension are given, the returned
        entries are filtered based on those values.
        """

    def getFirstEntryToImport(target=None):
        """Return the first entry of the queue ready to be imported.

        :arg target: IPerson, IProduct, IProductSeries, IDistribution,
            IDistroSeries or ISourcePackage the import entries are attached to
            or None to get all entries available.
        """

    def getPillarObjectsWithImports(status=None):
        """Return list of Product and DistroSeries with pending imports.

        :arg status: Filter by RosettaImportStatus.

        All returned items will implement IHasTranslationImports.
        """

    def executeOptimisticApprovals(ztm):
        """Try to move entries from the Needs Review status to Approved one.

        :arg ztm: Zope transaction manager object.

        This method moves all entries that we know where should they be
        imported from the Needs Review status to the Accepted one.
        """

    def executeOptimisticBlock(ztm):
        """Try to move entries from the Needs Review status to Blocked one.

        :arg ztm: Zope transaction manager object or None.

        This method moves all .po entries that are on the same directory that
        a .pot entry that has the status Blocked to that same status.

        Return the number of items blocked.
        """

    def cleanUpQueue():
        """Remove old DELETED and IMPORTED entries.

        Only entries older than 5 days will be removed.
        """

    def remove(entry):
        """Remove the given :entry: from the queue."""


class IEditTranslationImportQueueEntry(Interface):
    """Set of widgets needed to moderate an entry on the imports queue."""

    potemplatename = Choice(
        title=_("Template Name"),
        description=_("The name of this PO template, for example"
            " 'evolution-2.2'. Each translation template's name"
            " is unique within its package"),
        required=True,
        vocabulary="POTemplateName")

    sourcepackagename = Choice(
        title=_("Source Package Name"),
        description=_(
            "The source package where this entry will be imported."),
        required=True,
        vocabulary="SourcePackageName")

    language = Choice(
        title=_("Language"),
        required=False,
        vocabulary="Language")

    variant = TextLine(
        title=_("Variant"),
        description=_(
            "Language variant, usually used to note the script used to"
            " write the translations (like 'Latn' for Latin)"),
        required=False)

    path = TextLine(
        title=_("Path"),
        description=_(
            "The path to this file inside the source tree. If it's empty, we"
            " use the one from the queue entry."),
        required=False)


class IHasTranslationImports(Interface):
    """An entity on which a translation import queue entry is attached.

    Examples include an IProductSeries, ISourcePackage, IDistroSeries and
    IPerson.
    """

    def getFirstEntryToImport():
        """Return the first entry of the queue ready to be imported."""

    def getTranslationImportQueueEntries(imports_status=None,
                                         file_extension=None):
        """Return entries in the translation import queue for this entity.

        :arg import_status: RosettaImportStatus DB Schema entry.
        :arg file_extension: String with the file type extension, usually 'po'
            or 'pot'.

        If one of both of 'import_status' or 'file_extension' are given, the
        returned entries are filtered based on those values.
        """
