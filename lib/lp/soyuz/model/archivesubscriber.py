# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Database class for table ArchiveSubscriber."""

__metaclass__ = type

__all__ = [
    'ArchiveSubscriber',
    ]

import pytz
from storm.expr import (
    And,
    Desc,
    LeftJoin,
    Select,
    )
from storm.locals import (
    DateTime,
    Int,
    Reference,
    Store,
    Storm,
    Unicode,
    )
from storm.store import EmptyResultSet
from zope.component import getUtility
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.enumcol import DBEnum
from lp.registry.interfaces.person import validate_person
from lp.registry.model.teammembership import TeamParticipation
from lp.soyuz.interfaces.archiveauthtoken import IArchiveAuthTokenSet
from lp.soyuz.interfaces.archivesubscriber import (
    IArchiveSubscriber,
    )
from lp.soyuz.enums import ArchiveSubscriberStatus
from lp.soyuz.model.archiveauthtoken import ArchiveAuthToken


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

    subscriber_id = Int(
        name='subscriber', allow_none=False,
        validator=validate_person)
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

    @property
    def displayname(self):
        """See `IArchiveSubscriber`."""
        return "%s's access to %s" % (
            self.subscriber.displayname, self.archive.displayname)

    def cancel(self, cancelled_by):
        """See `IArchiveSubscriber`."""
        self.date_cancelled = UTC_NOW
        self.cancelled_by = cancelled_by
        self.status = ArchiveSubscriberStatus.CANCELLED

    def getNonActiveSubscribers(self):
        """See `IArchiveSubscriber`."""
        # Imported here because of circular imports.
        from lp.registry.model.person import Person

        store = Store.of(self)
        if self.subscriber.is_team:

            # We want to get all participants who are themselves
            # individuals, not teams:
            all_subscribers = store.find(
                Person,
                TeamParticipation.teamID == self.subscriber_id,
                TeamParticipation.personID == Person.id,
                Person.teamowner == None)

            # Then we get all the people who already have active
            # tokens for this archive (for example, through separate
            # subscriptions).
            active_subscribers = store.find(
                Person,
                Person.id == ArchiveAuthToken.person_id,
                ArchiveAuthToken.archive_id == self.archive_id,
                ArchiveAuthToken.date_deactivated == None)

            # And return just the non active subscribers:
            non_active_subscribers = all_subscribers.difference(
                active_subscribers)
            non_active_subscribers.order_by(Person.name)
            return non_active_subscribers
        else:
            # Subscriber is not a team.
            token_set = getUtility(IArchiveAuthTokenSet)
            if token_set.getActiveTokenForArchiveAndPerson(
                self.archive, self.subscriber) is not None:
                # There are active tokens, so return an empty result
                # set.
                return EmptyResultSet()

            # Otherwise return a result set containing only the
            # subscriber.
            return store.find(Person, Person.id == self.subscriber_id)


class ArchiveSubscriberSet:
    """See `IArchiveSubscriberSet`."""

    def getBySubscriber(self, subscriber, archive=None, current_only=True):
        """See `IArchiveSubscriberSet`."""

        # Grab the extra Storm expressions, for this query,
        # depending on the params:
        extra_exprs = self._getExprsForSubscriptionQueries(
            archive, current_only)

        # Set the main expression to find all the subscriptions for
        # which the subscriber is a direct subscriber OR is a member
        # of a subscribed team.
        # Note: the subscription to the owner itself will also be
        # part of the join as there is a TeamParticipation entry
        # showing that each person is a member of the "team" that
        # consists of themselves.
        store = Store.of(subscriber)
        return store.find(
            ArchiveSubscriber,
            ArchiveSubscriber.subscriber_id.is_in(
                self._getTeamsWithSubscriptionsForUser(
                    subscriber)),
            *extra_exprs).order_by(Desc(ArchiveSubscriber.date_created))

    def getBySubscriberWithActiveToken(self, subscriber, archive=None):
        """See `IArchiveSubscriberSet`."""

        # We need a left join with ArchiveSubscriber as
        # the origin:
        origin = [
            ArchiveSubscriber,
            LeftJoin(
                ArchiveAuthToken,
                And(
                    ArchiveAuthToken.archive_id ==
                        ArchiveSubscriber.archive_id,
                    ArchiveAuthToken.person_id == subscriber.id,
                    ArchiveAuthToken.date_deactivated == None))]

        # Grab the extra Storm expressions, for this query,
        # depending on the params:
        extra_exprs = self._getExprsForSubscriptionQueries(
            archive)

        store = Store.of(subscriber)
        return store.using(*origin).find(
            (ArchiveSubscriber, ArchiveAuthToken),
            ArchiveSubscriber.subscriber_id.is_in(
                self._getTeamsWithSubscriptionsForUser(
                    subscriber)),
            *extra_exprs).order_by(Desc(ArchiveSubscriber.date_created))

    def getByArchive(self, archive, current_only=True):
        """See `IArchiveSubscriberSet`."""
        # Grab the extra Storm expressions, for this query,
        # depending on the params:
        extra_exprs = self._getExprsForSubscriptionQueries(
            archive, current_only)

        store = Store.of(archive)
        return store.find(
            ArchiveSubscriber,
            *extra_exprs).order_by(Desc(ArchiveSubscriber.date_created))

    def _getExprsForSubscriptionQueries(self, archive=None,
                                        current_only=True):
        """Return the Storm expressions required for the parameters.

        Just to keep the code DRY.
        """
        extra_exprs = []

        # Restrict the results to the specified archive if requested:
        if archive:
            extra_exprs.append(ArchiveSubscriber.archive == archive)

        # Restrict the results to only those subscriptions that are current
        # if requested:
        if current_only:
            extra_exprs.append(
                ArchiveSubscriber.status == ArchiveSubscriberStatus.CURRENT)

        return extra_exprs

    def _getTeamsWithSubscriptionsForUser(self, subscriber):
        """Return a subselect that defines all the teams the subscriber
        is a member of.that have subscriptions.

        Just to keep the code DRY.
        """
        # Include subscriptions for teams of which the subscriber is a
        # member. First create a subselect to capture all the teams that are
        # subscribed to archives AND the user is a member of:
        return Select(
            TeamParticipation.teamID,
            where=And(
                TeamParticipation.personID == subscriber.id,
                TeamParticipation.teamID ==
                    ArchiveSubscriber.subscriber_id))
