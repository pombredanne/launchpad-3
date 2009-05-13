# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""ArchiveDependency interface."""

__metaclass__ = type

__all__ = [
    'IArchiveDependency',
    ]

from zope.interface import Attribute, Interface
from zope.schema import Choice, Datetime, Int, Object

from canonical.launchpad import _
from lp.soyuz.interfaces.archive import IArchive
from lp.soyuz.interfaces.publishing import PackagePublishingPocket


class IArchiveDependency(Interface):
    """ArchiveDependency interface."""

    id = Int(title=_("The archive ID."), readonly=True)

    date_created = Datetime(
        title=_("Instant when the dependency was created."),
        required=False, readonly=True)

    archive = Choice(
        title=_('Target archive'),
        required=True,
        vocabulary='PPA',
        description=_("The PPA affected by this dependecy."))

    dependency = Object(
        schema=IArchive,
        title=_("The archive set as a dependency."),
        required=False)

    pocket = Choice(
        title=_("Pocket"), required=True, vocabulary=PackagePublishingPocket)

    component = Choice(
        title=_("Component"), required=True, vocabulary='Component')

    title = Attribute("Archive dependency title.")
