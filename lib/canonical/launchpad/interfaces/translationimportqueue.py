# Copyright 2005 Canonical Ltd. All rights reserved.

from zope.interface import Interface, Attribute
from zope.schema import Bool, Choice, TextLine

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

__metaclass__ = type

__all__ = [
    'ITranslationImportQueue',
    'ITranslationImportQueueSet',
    'ITranslationImportQueueEdition',
    ]

class ITranslationImportQueue(Interface):
    """An entry of the Translation Import Queue."""

    id = Attribute('The item ID')

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
            "The person that imported this file in Rosetta."),
        vocabulary="ValidOwner")

    dateimport = Attribute('The timestamp when this file was imported.')

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
        required=False,
        vocabulary="SourcePackageName")

    ignore = Bool(
        title=_("Ignore this import request?"),
        description=_(
            "If checked, this import will not be imported ever."),
        required=True,
        default=False)

    is_published = Bool(
        title=_("This import comes from a published file"),
        description=_(
            "If checked, this import will be handled as already published."),
        required=True,
        default=False)

    content = Attribute("The file content.")

    sourcepackage = Attribute("The sourcepackage associated with this entry.")

    import_into = Attribute("The Object where this entry will be imported.")

    def attachToPOFileOrPOTemplate(pofile_or_potemplate):
        """Move the imported file into the given IPOFile or IPOTemplate.

        Raise the ValueError exception if the given argument is not an IPOFile
        or an IPOTemplate or if the argument is not for the same
        sourcepackage/productseries.
        """

    def block(value=True):
        """Set this object as being (or nor) importable."""

    def getFileContent():
        """Return the imported file content as a stream."""


class ITranslationImportQueueSet(Interface):
    """A set of files to be imported into Rosetta."""

    def __iter__():
        """Iterate over all entries in the queue."""

    def __getitem__(id):
        """Return the ITranslationImportQueue with the given id.

        If there is not entries with that id, the NotFoundError exception is
        raised.
        """

    def addOrUpdateEntry(path, content, is_published, importer,
        sourcepackagename=None, distrorelease=None, productseries=None):
        """Return a new or updated entry of the import queue.

        'path' is the path, with the filename, of the file imported.
        'content' is the file content.
        'is_published' indicates if the imported file is already published by
        upstream.
        'importer' is the person that did the import.
        'sourcepackagename' is the link of this import with source package.
        'distrorelease' is the link of this import with a distribution.
        'productseries' is the link of this import with a product branch.
        'sourcepackagename' + 'distrorelease' and 'productseries' are exclusive,
        we must have only one combination of them.
        """

    def addOrUpdateEntriesFromTarball(content, is_published, importer,
        sourcepackagename=None, distrorelease=None, productseries=None):
        """Add all .po or .pot files from the tarball at 'content'.

        'content' is a tarball stream.
        'is_published' indicates if the imported file is already published by
        upstream.
        'importer' is the person that did the import.
        'sourcepackagename' is the link of this import with source package.
        'distrorelease' is the link of this import with a distribution.
        'productseries' is the link of this import with a product branch.
        'sourcepackagename' + 'distrorelease' and 'productseries' are exclusive,
        we must have only one combination of them.
        Return the number of files attached.
        """

    def getEntries(include_ignored=False):
        """Iterate over the entries in the queue.

        If the 'include_ignored' flag is True all entries are returned, if
        it's False only the ones with 'ignore'= False are returned.
        """

    def getEntriesForProductSeries(productseries):
        """Return a set of ITranslationImportQueue objects that are related to
        the given IProductSeries.
        """

    def getEntriesForDistroReleaseAndSourcePackageName(distrorelease,
        sourcepackagename):
        """Return a set of ITranslationImportQueue objects that are related to
        the given distrorelease and sourcepackagename.
        """

    def hasBlockedEntries():
        """Return whether there are blocked entries in the queue or not."""

    def getBlockedEntries():
        """Return the set of ITranslationImportQueue objects that are set as
        blocked to be imported.
        """

    def get(id):
        """Return the ITranslationImportQueue with the given id.

        If there is not entries with that id, the NotFoundError exception is
        raised.
        """

    def remove(id):
        """Remove the item referered by 'id' from the queue."""


class ITranslationImportQueueEdition(Interface):
    """Set of widgets needed to moderate an entry on the imports queue."""

    potemplatename = Choice(
        title=_("Template Name"),
        description=_("The name of this PO template, for example "
            "'evolution-2.2'. Each translation template has a "
            "unique name in its package. It's important to get this "
            "correct, because Rosetta will recommend alternative "
            "translations based on the name."),
        required=True,
        vocabulary="POTemplateName")

    sourcepackagename = Choice(
        title=_("Source Package Name"),
        description=_(
            "The source package that uses this template."),
        required=True,
        vocabulary="SourcePackageName")

    language = Choice(
        title=_("Language"),
        required=False,
        vocabulary="Language")

    variant = TextLine(
        title=_("Variant"),
        required=False)

    path = TextLine(
        title=_("Path"),
        description=_(
            "The path to this file inside the source tree. If it's empty, we"
            " use the one from the queue entry."),
        required=False)
