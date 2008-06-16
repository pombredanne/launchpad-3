# Copyright 2004-2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces related to archive-rebuild system."""

__metaclass__ = type

__all__ = [
    'ArchiveRebuildAlreadyExists',
    'ArchiveRebuildInconsistentStateError',
    'ArchiveRebuildStatus',
    'ArchiveRebuildStatusWriteProtectedError',
    'IArchiveRebuild',
    'IArchiveRebuildSet',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Choice, Datetime, Object

from canonical.launchpad import _
from canonical.launchpad.fields import Description
from canonical.launchpad.interfaces.archive import IArchive
from canonical.launchpad.interfaces.distroseries import IDistroSeries

from canonical.lazr import DBEnumeratedType, DBItem


class ArchiveRebuildAlreadyExists(Exception):
    """Raised if a duplicated ArchiveRebuild creation was requested."""


class ArchiveRebuildStatusWriteProtectedError(Exception):
    """Raised if a callsite tried to update `IArchiveRebuild.status` directly.

    All callsites should use one of the status handling methods:

     * setCancelled()
     * setComplete()
     * setObsolete()
    """


class ArchiveRebuildInconsistentStateError(Exception):
    """Raised if a `ArchiveRebuild` is set to inconsistent status."""


class ArchiveRebuildStatus(DBEnumeratedType):
    """Archive rebuild status."""

    INPROGRESS = DBItem(1, """
        In progress

        The builds in this archive rebuild are being processed.
        """)

    COMPLETE = DBItem(2, """
        Complete

        The builds in this archive rebuild are already finished.
        """)

    CANCELLED = DBItem(3, """
        Cancelled

        This archive rebuild attempt has being cancelled.
        """)

    OBSOLETE = DBItem(4, """
        Obsolete

        The result of this archive rebuild is not relevant anymore.
        """)


class IArchiveRebuild(Interface):
    """Archive rebuild record.

    See `doc/archive-rebuild.txt` for details about the attributes.
    """
    id = Attribute("The ArchiveRebuild unique number.")

    archive = Object(
        schema=IArchive,
        title=_("The IArchive which contains the source for rebuild."),
        required=False)

    distroseries = Object(
        schema=IDistroSeries,
        title=_("The rebuild target IDistroSeries."),
        required=False)

    registrant = Choice(
        title=_('User'),
        required=True,
        vocabulary='ValidPerson',
        description=_("The person registering the archive rebuild."))

    status = Choice(
        title=_('Status'),
        readonly=True,
        vocabulary='ArchiveRebuildStatus',
        description=_("The status of the archive rebuild."))

    reason = Description(
        title=_("Reason"), required=True,
        description=_("A detailed description of the reason why the "
                      "ArchiveRebuild was created."))

    date_created = Datetime(
        title=_(u'Date Created'), required=True)

    title = Attribute("ArchiveRebuild title.")

    def setInProgress():
        """Reactivated rebuild."""

    def setCancelled():
        """Cancel rebuild. """

    def setComplete():
        """Mark rebuild as complete."""

    def setObsolete():
        """Mark rebuild as obsolete."""


class IArchiveRebuildSet(Interface):
    """The set and helpers for `IArchiveRebuild`."""

    def __iter__():
        """Iterate over all `IArchiveRebuild` records.

        Resuld is ordered by descending database ID
        """

    def get(rebuild_id):
        """Retrieve a `IArchiveRebuild` for the given id."""

    def getByDistributionAndArchiveName(distribution, archive_name):
        """Return a `IArchiveRebuild` matching the given parameters.

        :param distribution: `IDistribution` target;
        :param archive_name: text exactly matching `IArchive.name`;

        :return: a matching `IArchiveRebuild` or None if it could not be
            found.
        """

    def new(name, distroseries, registrant, reason):
        """Create a new `IArchiveRebuild` record.

        Create the corresponding `IArchive` and return the just created
        `IArchiveRebuild` in INPROGRESS status for the given attributes.

        :param name: text to be used as the `IArchive` name;
        :param distroseries: `IDistroSeries` to which the rebuild will be
             attached;
        :param registrant: `IPerson` which will be records as the rebuild
             registrant and as owner of the `IArchive`;
        :param reason: text to be used as the rebuild 'reason' field.

        :return: the just created `IArchiveRebuild` record.
        """

    def getByDistroSeries(distroseries):
        """All `IArchiveRebuild` targetted to the given `IDistroSeries`.

        The result is ordered by ascending 'status' and then descending
        'datecreated'.
        """
