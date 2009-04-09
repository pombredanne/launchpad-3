# Copyright 2005-2009 Canonical Ltd. All rights reserved.
# pylint: disable-msg=E0211,E0213

from zope.interface import Interface, Attribute
from zope.schema import (
    Bool, Choice, Datetime, Field, Int, Object, Text, TextLine)
from lazr.enum import DBEnumeratedType, DBItem, EnumeratedType, Item

from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    ISourcePackage, TranslationFileFormat)
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.productseries import IProductSeries

from lazr.restful.interface import copy_field
from lazr.restful.fields import Reference, ReferenceChoice
from lazr.restful.declarations import (
    collection_default_content, exported, export_as_webservice_collection,
    export_as_webservice_entry, export_read_operation, operation_parameters,
    operation_returns_entry, operation_returns_collection_of)

from canonical.launchpad.interfaces.translationcommonformat import (
    TranslationImportExportBaseException)

__metaclass__ = type

__all__ = [
    'TranslationImportQueueConflictError',
    'ITranslationImportQueueEntry',
    'ITranslationImportQueue',
    'IEditTranslationImportQueueEntry',
    'IHasTranslationImports',
    'RosettaImportStatus',
    'SpecialTranslationImportTargetFilter',
    'TranslationFileType',
    ]


class TranslationImportQueueConflictError(
                                    TranslationImportExportBaseException):
    """A new entry cannot be inserted into the queue because it
    conflicts with existing entries."""


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


class SpecialTranslationImportTargetFilter(DBEnumeratedType):
    """Special "meta-targets" to filter the queue view by."""

    PRODUCT = DBItem(1, """
        Any project

        Any project registered in Launchpad.
        """)

    DISTRIBUTION = DBItem(2, """
        Any distribution

        Any distribution registered in Launchpad.
        """)


class IHasTranslationImports(Interface):
    """An entity on which a translation import queue entry is attached.

    Examples include an IProductSeries, ISourcePackage, IDistroSeries and
    IPerson.
    """
    export_as_webservice_entry(
        singular_name='object_with_translation_imports',
        plural_name='objects_with_translation_imports')

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


class ITranslationImportQueueEntry(Interface):
    """An entry of the Translation Import Queue."""
    export_as_webservice_entry(
        singular_name='translation_import_queue_entry',
        plural_name='translation_import_queue_entries')

    id = exported(Int(title=_('The entry ID'), required=True, readonly=True))

    path = exported(
        TextLine(
            title=_("Path"),
            description=_(
                "The path to this file inside the source tree. Includes the"
                " filename."),
            required=True))

    importer = exported(
        ReferenceChoice(
            title=_("Uploader"),
            schema=IPerson,
            required=True,
            readonly=True,
            description=_(
                "The person that uploaded this file to Launchpad."),
            vocabulary="ValidOwner"),
        exported_as="uploader")

    dateimported = exported(
        Datetime(
            title=_("The timestamp when this queue entry was created."),
            required=True,
            readonly=True),
        exported_as="date_created")

    productseries = exported(
        Object(
            title=_("Series"),
            required=False,
            readonly=True,
            schema=IProductSeries))

    distroseries = exported(
        Object(
            title=_("Series"),
            required=False,
            readonly=True,
            schema=IDistroSeries))

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

    format = exported(
        Choice(
            title=_('The file format of the import.'),
            vocabulary=TranslationFileFormat,
            required=True,
            readonly=True))

    status = exported(
        Choice(
            title=_("The status of the import."),
            values=RosettaImportStatus.items,
            required=True,
            readonly=True))

    date_status_changed = exported(
        Datetime(
            title=_("The timestamp when the status was changed."),
            required=True))

    is_targeted_to_ubuntu = Attribute(
        "True if this entry is to be imported into the Ubuntu distribution.")

    sourcepackage = exported(
        Object(
            schema=ISourcePackage,
            title=_("The sourcepackage associated with this entry."),
            readonly=True))

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

    error_output = exported(
        Text(
            title=_("Error output"),
            description=_("Output from most recent import attempt."),
            required=False))

    def setStatus(status):
        """Set status.

        :param status: new status to set.
        """

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
        """Return a string representing elapsed time since we got the file.

        The returned string is like:
            '2 days 3 hours 10 minutes ago' or 'just requested'
        """


class ITranslationImportQueue(Interface):
    """A set of files to be imported into Rosetta."""
    export_as_webservice_collection(ITranslationImportQueueEntry)

    def __iter__():
        """Iterate over all entries in the queue."""

    def __getitem__(id):
        """Return the ITranslationImportQueueEntry with the given id.

        If there is not entries with that id, the NotFoundError exception is
        raised.
        """

    def countEntries():
        """Return the number of `TranslationImportQueueEntry` records."""

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

    @collection_default_content()
    @operation_parameters(
        import_status=copy_field(ITranslationImportQueueEntry['status']))
    @operation_returns_collection_of(ITranslationImportQueueEntry)
    @export_read_operation()
    def getAllEntries(target=None, import_status=None, file_extensions=None):
        """Return all entries this import queue has.

        :arg target: IPerson, IProduct, IProductSeries, IDistribution,
            IDistroSeries or ISourcePackage the import entries are attached to
            or None to get all entries available.
        :arg import_status: RosettaImportStatus entry.
        :arg file_extensions: Sequence of filename suffixes to match, usually
            'po' or 'pot'.

        If any of target, status or file_extension are given, the returned
        entries are filtered based on those values.
        """

    @export_read_operation()
    @operation_parameters(target=Reference(schema=IHasTranslationImports))
    @operation_returns_entry(ITranslationImportQueueEntry)
    def getFirstEntryToImport(target=None):
        """Return the first entry of the queue ready to be imported.

        :param target: IPerson, IProduct, IProductSeries, IDistribution,
            IDistroSeries or ISourcePackage the import entries are attached to
            or None to get all entries available.
        """

    @export_read_operation()
    @operation_parameters(
        status=copy_field(ITranslationImportQueueEntry['status']))
    @operation_returns_collection_of(IHasTranslationImports)
    def getRequestTargets(status=None):
        """List `Product`s and `DistroSeries` with pending imports.

        :arg status: Filter by `RosettaImportStatus`.

        All returned items will implement `IHasTranslationImports`.
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


class TranslationFileType(EnumeratedType):
    """The different types of translation files that can be imported."""

    UNSPEC = Item("""
        <Please specify>

        Not yet specified.
        """)

    POT = Item("""
        Template

        A translation template file.
        """)

    PO = Item("""
        Translations

        A translation data file.
        """)


class IEditTranslationImportQueueEntry(Interface):
    """Set of widgets needed to moderate an entry on the imports queue."""

    file_type = Choice(
        title=_("File Type"),
        description=_(
            "The type of the file being imported imported."),
        required=True,
        vocabulary = TranslationFileType)

    path = TextLine(
        title=_("Path"),
        description=_(
            "The path to this file inside the source tree."),
        required=True)

    sourcepackagename = Choice(
        title=_("Source Package Name"),
        description=_(
            "The source package where this entry will be imported."),
        required=True,
        vocabulary="SourcePackageName")

    name = TextLine(
        title=_("Name"),
        description=_(
            "For templates only: "
            "The name of this PO template, for example "
            "'evolution-2.2'. Each translation template has a "
            "unique name in its package."),
        required=False)

    translation_domain = TextLine(
        title=_("Translation domain"),
        description=_(
            "For templates only: "
            "The translation domain for a translation template. "
            "Used with PO file format when generating MO files for inclusion "
            "in language pack or MO tarball exports."),
        required=False)

    languagepack = Bool(
        title=_("Include translations for this template in language packs?"),
        description=_(
            "For templates only: "
            "Check this box if this template is part of a language pack so "
            "its translations should be exported that way."),
        required=True,
        default=False)

    potemplate = Choice(
        title=_("Template"),
        description=_(
            "For translations only: "
            "The template that this translation is based on. "
            "The template has to be uploaded first."),
        required=False,
        vocabulary="TranslationTemplate")

    potemplate_name = TextLine(
        title=_("Template name"),
        description=_(
            "For translations only: "
            "Enter the template name if it does not appear "
            "in the list above."),
        required=False)

    language = Choice(
        title=_("Language"),
        required=True,
        description=_(
            "For translations only: "
            "The language this PO file translates to."),
        vocabulary="Language")

    variant = TextLine(
        title=_("Variant"),
        description=_(
            "For translations only: "
            "Language variant, usually used to note the script used to"
            " write the translations (like 'Latn' for Latin)"),
        required=False)
