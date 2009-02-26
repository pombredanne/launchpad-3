# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Database class for table ArchiveSubscriber."""

__metaclass__ = type

__all__ = [
    'ArchiveSubscriber',
    ]

import pytz

from storm.expr import And, LeftJoin, Select
from storm.locals import DateTime, Int, Reference, Store, Storm, Unicode

from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.enumcol import DBEnum
from canonical.launchpad.database.archiveauthtoken import ArchiveAuthToken
from canonical.launchpad.database.teammembership import TeamParticipation
from canonical.launchpad.interfaces.archivesubscriber import (
    ArchiveSubscriberStatus, IArchiveSubscriber)


class ArchiveSubscriber(Storm):
    """See `IArchiveSubscriber`."""
    implements(IArchiveSubscriber)
    __storm_table__ = 'ArchiveSubscriber'

    id = Int(primary=True)

    archive_id = Int(name='archive', allow_none=False)
    archive = Reference(archive_id, 'Archive.id')

    registrant_id = Int(name='registrant', allow_none=False)
    registrant = Reference(registrant_id, 'Person.id')

    date_created = DateTime(
        name='date_created', allow_none=False, tzinfo=pytz.UTC)

    subscriber_id = Int(name='subscriber', allow_none=False)
    subscriber = Reference(subscriber_id, 'Person.id')

    date_expires = DateTime(
        name='date_expires', allow_none=True, tzinfo=pytz.UTC)

    status = DBEnum(
        name='status', allow_none=False,
        enum=ArchiveSubscriberStatus)

    description = Unicode(name='description', allow_none=True)

    date_cancelled = DateTime(
        name='date_cancelled', allow_none=True, tzinfo=pytz.UTC)

    cancelled_by_id = Int(name='cancelled_by', allow_none=True)
    cancelled_by = Reference(cancelled_by_id, 'Person.id')

    def cancel(self, cancelled_by):
        """See `IArchiveSubscriber`."""
        self.date_cancelled = UTC_NOW
        self.cancelled_by = cancelled_by
        self.status = ArchiveSubscriberStatus.CANCELLED


class ArchiveSubscriberSet:
    """See `IArchiveSubscriberSet`."""

    def getBySubscriber(self, subscriber, archive=None, current_only=True,
                        include_team_subscriptions=True,
                        return_tokens=False):
        """See `IArchiveSubscriberSet`."""
        extra_exprs = []

        # Restrict the results to the specified archive if requested:
        if archive:
            extra_exprs.append(ArchiveSubscriber.archive == archive)

        # Restrict the results to only those subscriptions that are current
        # if requested:
        if current_only:
            extra_exprs.append(
                ArchiveSubscriber.status == ArchiveSubscriberStatus.CURRENT)

        # Include subscriptions for teams of which the subscriber is a
        # member if requested:
        if include_team_subscriptions:
            # Create a subselect to capture all the teams that are
            # subscribed to archives AND the user is a member of:
            user_teams_subselect = Select(
                TeamParticipation.teamID,
                where=And(
                    TeamParticipation.personID == subscriber.id,
                    TeamParticipation.teamID ==
                        ArchiveSubscriber.subscriber_id))

            # Set the main expression to find all the subscriptions for
            # which the subscriber is a direct subscriber OR is a member
            # of a subscribed team.
            # Note: 'ArchiveSubscriber.subscriber == subscriber' 
            # is unnecessary below because there is a TeamParticipation
            # entry showing that each person is a member of the "team"
            # that consists of themselves.
            main_expr = ArchiveSubscriber.subscriber_id.is_in(
                user_teams_subselect)
        else:
            main_expr = ArchiveSubscriber.subscriber == subscriber

        store = Store.of(subscriber)
        find_spec = ArchiveSubscriber

        # If requested, include the corresponding ArchiveAuthToken - if
        # it exists - for each archive subscription returned for the
        # subscriber:
        if return_tokens:
            find_spec = (ArchiveSubscriber, ArchiveAuthToken)

            # We need a left join with ArchiveSubscriber as
            # the origin:
            origin = [
                ArchiveSubscriber,
                LeftJoin(
                    ArchiveAuthToken,
                    And(
                        ArchiveAuthToken.archive_id == 
                            ArchiveSubscriber.archive_id,
                        ArchiveAuthToken.person_id == subscriber.id))]
            store = store.using(*origin)

        return store.find(
            find_spec,
            main_expr,
            *extra_exprs)

    def getByArchive(self, archive, current_only=True):
        """See `IArchiveSubscriberSet`."""
        extra_exprs = []

        if current_only:
            extra_exprs.append(
                ArchiveSubscriber.status == ArchiveSubscriberStatus.CURRENT)

        store = Store.of(archive)
        return store.find(
            ArchiveSubscriber,
            ArchiveSubscriber.archive == archive,
            *extra_exprs)
