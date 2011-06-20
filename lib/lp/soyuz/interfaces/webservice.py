# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""All the interfaces that are exposed through the webservice.

There is a declaration in ZCML somewhere that looks like:
  <webservice:register module="lp.soyuz.interfaces.webservice" />

which tells `lazr.restful` that it should look for webservice exports here.
"""

__all__ = [
    'AlreadySubscribed',
    'ArchiveDisabled',
    'ArchiveNotPrivate',
    'CannotBeRescored',
    'CannotCopy',
    'CannotSwitchPrivacy',
    'CannotUploadToArchive',
    'CannotUploadToPPA',
    'CannotUploadToPocket',
    'ComponentNotFound',
    'DistroSeriesNotFound',
    'DuplicatePackagesetName',
    'IArchive',
    'IArchiveDependency',
    'IArchivePermission',
    'IArchiveSubscriber',
    'IBinaryPackageBuild',
    'IBinaryPackagePublishingHistory',
    'IBinaryPackageReleaseDownloadCount',
    'IDistroArchSeries',
    'IPackageUpload',
    'IPackageset',
    'IPackagesetSet',
    'IProcessor',
    'IProcessorFamily',
    'IProcessorFamilySet',
    'ISourcePackagePublishingHistory',
    'IncompatibleArguments',
    'InsufficientUploadRights',
    'InvalidComponent',
    'InvalidPocketForPPA',
    'InvalidPocketForPartnerArchive',
    'NoRightsForArchive',
    'NoRightsForComponent',
    'NoSuchPPA',
    'NoSuchPackageSet',
    'NoTokensForTeams',
    'PocketNotFound',
    'VersionRequiresName',
    ]

from lp.soyuz.interfaces.archive import (
    AlreadySubscribed,
    ArchiveDisabled,
    ArchiveNotPrivate,
    CannotCopy,
    CannotSwitchPrivacy,
    CannotUploadToArchive,
    CannotUploadToPPA,
    CannotUploadToPocket,
    ComponentNotFound,
    DistroSeriesNotFound,
    IArchive,
    InsufficientUploadRights,
    InvalidComponent,
    InvalidPocketForPPA,
    InvalidPocketForPartnerArchive,
    NoRightsForArchive,
    NoRightsForComponent,
    NoSuchPPA,
    NoTokensForTeams,
    PocketNotFound,
    VersionRequiresName,
    )
from lp.soyuz.interfaces.archivedependency import IArchiveDependency
from lp.soyuz.interfaces.archivepermission import IArchivePermission
from lp.soyuz.interfaces.archivesubscriber import IArchiveSubscriber
from lp.soyuz.interfaces.binarypackagebuild import (
    CannotBeRescored,
    IBinaryPackageBuild,
    )
from lp.soyuz.interfaces.binarypackagerelease import (
    IBinaryPackageReleaseDownloadCount,
    )
from lp.soyuz.interfaces.buildrecords import (
    IncompatibleArguments,
    )
from lp.soyuz.interfaces.distroarchseries import IDistroArchSeries
from lp.soyuz.interfaces.packageset import (
    DuplicatePackagesetName,
    IPackageset,
    IPackagesetSet,
    NoSuchPackageSet,
    )
from lp.soyuz.interfaces.processor import (
    IProcessor,
    IProcessorFamily,
    IProcessorFamilySet,
    )
from lp.soyuz.interfaces.publishing import (
    IBinaryPackagePublishingHistory,
    ISourcePackagePublishingHistory,
    )
from lp.soyuz.interfaces.queue import IPackageUpload

from canonical.launchpad.components.apihelpers import (
    patch_entry_return_type,
    )
# XXX: JonathanLange 2010-11-09 bug=673083: Legacy work-around for circular
# import bugs.  Break this up into a per-package thing.
from canonical.launchpad.interfaces import _schema_circular_imports
_schema_circular_imports

from lazr.restful.declarations import LAZR_WEBSERVICE_EXPORTED
IProcessorFamilySet.queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)['collection_entry_schema'] = IProcessorFamily

patch_entry_return_type(IProcessorFamilySet, 'getByName', IProcessorFamily)
