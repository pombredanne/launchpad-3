# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Product release interfaces."""

__metaclass__ = type

__all__ = [
    'IProductReleaseSet',
    'IProductRelease',
    'IProductReleaseFile',
    'IProductReleaseFileAddForm',
    ]

from zope.schema import Bytes, Choice, Datetime, Int, Object, Text, TextLine
from zope.interface import Interface, Attribute
from zope.component import getUtility

from canonical.launchpad import _
from canonical.lp.dbschema import UpstreamFileType
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias
from canonical.launchpad.interfaces.productseries import IProductSeries
from canonical.launchpad.validators.version import sane_version
from canonical.launchpad.validators.productrelease import (
    productrelease_file_size_constraint)

from canonical.launchpad.fields import ContentNameField


class ProductReleaseVersionField(ContentNameField):

    errormessage = _(
        "%s is already in use by another version in this release series.")

    @property
    def _content_iface(self):
        return IProductRelease

    def _getByName(self, version):
        if IProductSeries.providedBy(self.context):
            productseries = self.context
        else:
            productseries = self.context.productseries
        releaseset = getUtility(IProductReleaseSet)
        return releaseset.getBySeriesAndVersion(productseries, version)


class IProductRelease(Interface):
    """A specific release (i.e. has a version) of a product. For example,
    Mozilla 1.7.2 or Apache 2.0.48."""
    id = Int(title=_('ID'), required=True, readonly=True)
    datereleased = Datetime(title=_('Date Released'), required=True,
        readonly=False, description=_('The date this release was '
        'published. Before release, this should have an estimated '
        'release date.'))
    version = ProductReleaseVersionField(title=_('Version'), required=True,
        readonly=True, constraint=sane_version, description=_(
        'The specific version number assigned to this release. Letters and '
        'numbers are acceptable, for releases like "1.2rc3".'))
    owner = Int(title=_('Owner'), required=True)
    productseries = Choice(title=_('Release Series'), required=True,
        vocabulary='FilteredProductSeries')
    codename = TextLine(title=_('Code name'), required=False,
        description=_('The release code-name. Famously, one Gnome release '
        'was code-named "that, and a pair of testicles", but you don\'t '
        'have to be as brave with your own release codenames.'))
    summary = Text(title=_("Summary"), required=False,
        description=_('A brief summary of the release highlights, to '
        'be shown at the top of the release page, and in listings.'))
    description = Text(title=_("Description"), required=False,
        description=_('A detailed description of the new features '
        '(though the changelog below might repeat some of this '
        'information). The description here will be shown on the project '
        'release home page.'))
    changelog = Text(title=_('Changelog'), required=False)
    datecreated = Datetime(title=_('Date Created'),
        description=_("The date this productrelease was created in "
        "Launchpad."), required=True, readonly=True)
    displayname = Attribute('Constructed displayname for a product release.')
    title = Attribute('Constructed title for a product release.')
    product = Attribute(_('The upstream project of this release.'))
    files = Attribute(_('Iterable of product release files.'))

    def addFileAlias(alias, uploader,
                     file_type=UpstreamFileType.CODETARBALL,
                     description=None):
        """Add a link between this product and a library file alias."""

    def deleteFileAlias(alias):
        """Delete the link between this product and a library file alias."""

    def getFileAliasByName(name):
        """Return the LibraryFileAlias by file name or None if not found."""

class IProductReleaseFile(Interface):

    productrelease = Choice(title=_('Project release'), required=True,
                            vocabulary='ProductRelease')
    libraryfile = Object(schema=ILibraryFileAlias, title=_("File"),
                         description=_("The attached file."),
                         required=True)
    filetype = Choice(title=_("Upstream file type"), required=True,
                      vocabulary='UpstreamFileType',
                      default=UpstreamFileType.CODETARBALL)

    description = Text(title=_("Description"), required=False,
        description=_('A detailed description of the file contents'))

class IProductReleaseFileAddForm(Interface):
    """Schema for adding ProductReleaseFiles to a project."""
    description = Text(title=_("Description"), required=True,
        description=_('A short description of the file contents'))

    filecontent = Bytes(
        title=u"File", required=True,
        constraint=productrelease_file_size_constraint)

    contenttype = Choice(title=_("File content type"), required=True,
                         vocabulary='UpstreamFileType',
                         default=UpstreamFileType.CODETARBALL)

class IProductReleaseSet(Interface):
    """Auxiliary class for ProductRelease handling."""

    def new(version, owner, productseries, codename=None, shortdesc=None,
            description=None, changelog=None):
        """Create a new ProductRelease"""

    def getBySeriesAndVersion(productseries, version, default=None):
        """Get a release by its version and productseries.

        If no release is found, default will be returned.
        """
