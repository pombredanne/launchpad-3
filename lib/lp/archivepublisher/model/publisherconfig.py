# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Database class for table PublisherConfig."""

__metaclass__ = type

__all__ = [
    'PublisherConfig',
    'PublisherConfigSet',
    ]

from storm.locals import (
    Int,
    Reference,
    Storm,
    Unicode,
    )
from zope.interface import implements

from canonical.launchpad.interfaces.lpstorm import (
    IMasterStore,
    )
from lp.archivepublisher.interfaces.publisherconfig import (
    IPublisherConfig,
    IPublisherConfigSet,
    )


class PublisherConfig(Storm):
    """See `IArchiveAuthToken`."""
    implements(IPublisherConfig)
    __storm_table__ = 'PublisherConfig'

    id = Int(primary=True)

    distribution_id = Int(name='distribution', allow_none=False)
    distribution = Reference(distribution_id, 'Distribution.id')

    root_dir = Unicode(name='root_dir', allow_none=False)

    base_url = Unicode(name='base_url', allow_none=False)

    copy_base_url = Unicode(name='copy_base_url', allow_none=False)


class PublisherConfigSet:
    """See `IPublisherConfigSet`."""
    implements(IPublisherConfigSet)
    title = "Soyuz Publisher Configurations"

    def new(distribution, root_dir, base_url, copy_base_url):
        return PublisherConfig(
            distribution=distribution,
            root_dir=root_dir,
            base_url=base_url,
            copy_base_url=copy_base_url
            )
    def getByDistribution(self, distribution):
        """See `IArchiveAuthTokenSet`."""
        store = IMasterStore(PublisherConfig)
        return store.find(
            PublisherConfig,
            PublisherConfig.distribution_id == distribution.id).one()
