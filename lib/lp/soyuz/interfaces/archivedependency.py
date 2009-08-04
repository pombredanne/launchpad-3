# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""ArchiveDependency interface."""

__metaclass__ = type

__all__ = [
    'IArchiveDependency',
    ]

from zope.interface import Attribute, Interface
from zope.schema import Choice, Datetime, Int, Object, TextLine

from canonical.launchpad import _
from lp.soyuz.interfaces.archive import IArchive
from lp.soyuz.interfaces.publishing import PackagePublishingPocket
from lazr.restful.fields import Reference
from lazr.restful.declarations import (
    export_as_webservice_entry, exported)


class IArchiveDependency(Interface):
    """ArchiveDependency interface."""
    export_as_webservice_entry()

    id = Int(title=_("The archive ID."), readonly=True)

    date_created = exported(
        Datetime(
            title=_("Instant when the dependency was created."),
            required=False, readonly=True))

    archive = exported(
        Choice(
            title=_('Target archive'),
            required=True,
            vocabulary='PPA',
            description=_("The PPA affected by this dependecy.")))

    dependency = exported(
        Reference(
            schema=IArchive,
            title=_("The archive set as a dependency."),
            required=False)) # XXX: Huh? How is it not required?

    pocket = exported(
        Choice(
            title=_("Pocket"), required=True,
            vocabulary=PackagePublishingPocket))

    component = Choice(
        title=_("Component"), required=True, vocabulary='Component')

    # We don't want to export IComponent, so the name is exported specially.
    component_name = exported(
        TextLine(
            title=_("Component name"),
            required=True))

    title = exported(TextLine(title=_("Archive dependency title.")))
