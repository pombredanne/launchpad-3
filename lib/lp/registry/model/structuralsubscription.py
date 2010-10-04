# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = ['StructuralSubscription',
           'StructuralSubscriptionTargetMixin']

from sqlobject import ForeignKey
from zope.component import getUtility
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import (
    quote,
    SQLBase,
    )
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from lp.registry.enum import BugNotificationLevel
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.milestone import IMilestone
from lp.registry.interfaces.person import (
    validate_person,
    validate_public_person,
    )
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.projectgroup import IProjectGroup
from lp.registry.interfaces.structuralsubscription import (
    BlueprintNotificationLevel,
    DeleteSubscriptionError,
    IStructuralSubscription,
    IStructuralSubscriptionTarget,
    UserCannotSubscribePerson,
    )


class StructuralSubscription(SQLBase):
    """A subscription to a Launchpad structure."""

    implements(IStructuralSubscription)

    _table = 'StructuralSubscription'

    product = ForeignKey(
        dbName='product', foreignKey='Product', notNull=False, default=None)
    productseries = ForeignKey(
        dbName='productseries', foreignKey='ProductSeries', notNull=False,
        default=None)
    project = ForeignKey(
        dbName='project', foreignKey='ProjectGroup', notNull=False,
        default=None)
    milestone = ForeignKey(
        dbName='milestone', foreignKey='Milestone', notNull=False,
        default=None)
    distribution = ForeignKey(
        dbName='distribution', foreignKey='Distribution', notNull=False,
        default=None)
    distroseries = ForeignKey(
        dbName='distroseries', foreignKey='DistroSeries', notNull=False,
        default=None)
    sourcepackagename = ForeignKey(
        dbName='sourcepackagename', foreignKey='SourcePackageName',
        notNull=False, default=None)
    subscriber = ForeignKey(
        dbName='subscriber', foreignKey='Person',
        storm_validator=validate_person, notNull=True)
    subscribed_by = ForeignKey(
        dbName='subscribed_by', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    bug_notification_level = EnumCol(
        enum=BugNotificationLevel,
        default=BugNotificationLevel.NOTHING,
        notNull=True)
    blueprint_notification_level = EnumCol(
        enum=BlueprintNotificationLevel,
        default=BlueprintNotificationLevel.NOTHING,
        notNull=True)
    date_created = UtcDateTimeCol(
        dbName='date_created', notNull=True, default=UTC_NOW)
    date_last_updated = UtcDateTimeCol(
        dbName='date_last_updated', notNull=True, default=UTC_NOW)

    @property
    def target(self):
        """See `IStructuralSubscription`."""
        if self.product is not None:
            return self.product
        elif self.productseries is not None:
            return self.productseries
        elif self.project is not None:
            return self.project
        elif self.milestone is not None:
            return self.milestone
        elif self.distribution is not None:
            if self.sourcepackagename is not None:
                # XXX intellectronica 2008-01-15:
                #   We're importing this pseudo db object
                #   here because importing it from the top
                #   doesn't play well with the loading
                #   sequence.
                from lp.registry.model.distributionsourcepackage import (
                    DistributionSourcePackage)
                return DistributionSourcePackage(
                    self.distribution, self.sourcepackagename)
            else:
                return self.distribution
        elif self.distroseries is not None:
            return self.distroseries
        else:
            raise AssertionError('StructuralSubscription has no target.')


class StructuralSubscriptionTargetMixin:
    """Mixin class for implementing `IStructuralSubscriptionTarget`."""

    @property
    def _target_args(self):
        """Target Arguments.

        Return a dictionary with the arguments representing this
        target in a call to the structural subscription constructor.
        """
        args = {}
        if IDistributionSourcePackage.providedBy(self):
            args['distribution'] = self.distribution
            args['sourcepackagename'] = self.sourcepackagename
        elif IProduct.providedBy(self):
            args['product'] = self
        elif IProjectGroup.providedBy(self):
            args['project'] = self
        elif IDistribution.providedBy(self):
            args['distribution'] = self
            args['sourcepackagename'] = None
        elif IMilestone.providedBy(self):
            args['milestone'] = self
        elif IProductSeries.providedBy(self):
            args['productseries'] = self
        elif IDistroSeries.providedBy(self):
            args['distroseries'] = self
        else:
            raise AssertionError(
                '%s is not a valid structural subscription target.')
        return args

    def userCanAlterSubscription(self, subscriber, subscribed_by):
        """See `IStructuralSubscriptionTarget`."""
        # A Launchpad administrator or the user can subscribe a user.
        # A Launchpad or team admin can subscribe a team.

        # Nobody else can, unless the context is a IDistributionSourcePackage,
        # in which case the drivers or owner can.
        if IDistributionSourcePackage.providedBy(self):
            for driver in self.distribution.drivers:
                if subscribed_by.inTeam(driver):
                    return True
            if subscribed_by.inTeam(self.distribution.owner):
                return True

        admins = getUtility(ILaunchpadCelebrities).admin
        return (subscriber == subscribed_by or
                subscriber in subscribed_by.getAdministratedTeams() or
                subscribed_by.inTeam(admins))

    def addSubscription(self, subscriber, subscribed_by):
        """See `IStructuralSubscriptionTarget`."""
        if subscriber is None:
            subscriber = subscribed_by

        if not self.userCanAlterSubscription(subscriber, subscribed_by):
            raise UserCannotSubscribePerson(
                '%s does not have permission to subscribe %s.' % (
                    subscribed_by.name, subscriber.name))

        existing_subscription = self.getSubscription(subscriber)

        if existing_subscription is not None:
            return existing_subscription
        else:
            return StructuralSubscription(
                subscriber=subscriber,
                subscribed_by=subscribed_by,
                **self._target_args)

    def userCanAlterBugSubscription(self, subscriber, subscribed_by):
        """See `IStructuralSubscriptionTarget`."""

        admins = getUtility(ILaunchpadCelebrities).admin
        # If the object to be structurally subscribed to for bug
        # notifications is a distribution and that distribution has a
        # bug supervisor then only the bug supervisor or a member of
        # that team or, of course, admins, can subscribe someone to it.
        if IDistribution.providedBy(self) and self.bug_supervisor is not None:
            if subscriber is None or subscribed_by is None:
                return False
            elif (subscriber != self.bug_supervisor
                and not subscriber.inTeam(self.bug_supervisor)
                and not subscribed_by.inTeam(admins)):
                return False
        return True

    def addBugSubscription(self, subscriber, subscribed_by):
        """See `IStructuralSubscriptionTarget`."""
        # This is a helper method for creating a structural
        # subscription and immediately giving it a full
        # bug notification level. It is useful so long as
        # subscriptions are mainly used to implement bug contacts.

        if not self.userCanAlterBugSubscription(subscriber, subscribed_by):
            raise UserCannotSubscribePerson(
                '%s does not have permission to subscribe %s' % (
                    subscribed_by.name, subscriber.name))

        sub = self.addSubscription(subscriber, subscribed_by)
        sub.bug_notification_level = BugNotificationLevel.COMMENTS
        return sub

    def removeBugSubscription(self, subscriber, unsubscribed_by):
        """See `IStructuralSubscriptionTarget`."""
        if subscriber is None:
            subscriber = unsubscribed_by

        if not self.userCanAlterSubscription(subscriber, unsubscribed_by):
            raise UserCannotSubscribePerson(
                '%s does not have permission to unsubscribe %s.' % (
                    unsubscribed_by.name, subscriber.name))

        subscription_to_remove = None
        for subscription in self.getSubscriptions(
            min_bug_notification_level=BugNotificationLevel.METADATA):
            # Only search for bug subscriptions
            if subscription.subscriber == subscriber:
                subscription_to_remove = subscription
                break

        if subscription_to_remove is None:
            raise DeleteSubscriptionError(
                "%s is not subscribed to %s." % (
                subscriber.name, self.displayname))
        else:
            if (subscription_to_remove.blueprint_notification_level >
                BlueprintNotificationLevel.NOTHING):
                # This is a subscription to other application too
                # so only set the bug notification level
                subscription_to_remove.bug_notification_level = (
                    BugNotificationLevel.NOTHING)
            else:
                subscription_to_remove.destroySelf()

    def getSubscription(self, person):
        """See `IStructuralSubscriptionTarget`."""
        all_subscriptions = self.getSubscriptions()
        for subscription in all_subscriptions:
            if subscription.subscriber == person:
                return subscription
        return None

    def getSubscriptions(self,
                         min_bug_notification_level=
                         BugNotificationLevel.NOTHING,
                         min_blueprint_notification_level=
                         BlueprintNotificationLevel.NOTHING):
        """See `IStructuralSubscriptionTarget`."""
        clauses = [
            "StructuralSubscription.subscriber = Person.id",
            "StructuralSubscription.bug_notification_level "
            ">= %s" % quote(min_bug_notification_level),
            "StructuralSubscription.blueprint_notification_level "
            ">= %s" % quote(min_blueprint_notification_level),
            ]
        for key, value in self._target_args.iteritems():
            if value is None:
                clauses.append(
                    "StructuralSubscription.%s IS NULL" % (key,))
            else:
                clauses.append(
                    "StructuralSubscription.%s = %s" % (key, quote(value)))
        query = " AND ".join(clauses)
        return StructuralSubscription.select(
            query, orderBy='Person.displayname', clauseTables=['Person'])

    def getBugNotificationsRecipients(self, recipients=None, level=None):
        """See `IStructuralSubscriptionTarget`."""
        if level is None:
            subscriptions = self.bug_subscriptions
        else:
            subscriptions = self.getSubscriptions(
                min_bug_notification_level=level)
        subscribers = set(
            subscription.subscriber for subscription in subscriptions)
        if recipients is not None:
            for subscriber in subscribers:
                recipients.addStructuralSubscriber(subscriber, self)
        parent = self.parent_subscription_target
        if parent is not None:
            subscribers.update(
                parent.getBugNotificationsRecipients(recipients, level))
        return subscribers

    @property
    def bug_subscriptions(self):
        """See `IStructuralSubscriptionTarget`."""
        return self.getSubscriptions(
            min_bug_notification_level=BugNotificationLevel.METADATA)

    @property
    def parent_subscription_target(self):
        """See `IStructuralSubscriptionTarget`."""
        # Some structures have a related structure which can be thought
        # of as their parent. A package is related to a distribution,
        # a product is related to a project, etc'...
        # This method determines whether the target has a parent,
        # returning it if it exists.
        if IDistributionSourcePackage.providedBy(self):
            parent = self.distribution
        elif IProduct.providedBy(self):
            parent = self.project
        elif IProductSeries.providedBy(self):
            parent = self.product
        elif IDistroSeries.providedBy(self):
            parent = self.distribution
        elif IMilestone.providedBy(self):
            parent = self.target
        else:
            parent = None
        # We only want to return the parent if it's
        # an `IStructuralSubscriptionTarget`.
        if IStructuralSubscriptionTarget.providedBy(parent):
            return parent
        else:
            return None

    @property
    def target_type_display(self):
        """See `IStructuralSubscriptionTarget`."""
        if IDistributionSourcePackage.providedBy(self):
            return 'package'
        elif IProduct.providedBy(self):
            return 'project'
        elif IProjectGroup.providedBy(self):
            return 'project group'
        elif IDistribution.providedBy(self):
            return 'distribution'
        elif IMilestone.providedBy(self):
            return 'milestone'
        elif IProductSeries.providedBy(self):
            return 'project series'
        elif IDistroSeries.providedBy(self):
            return 'distribution series'
        else:
            raise AssertionError(
                '%s is not a valid structural subscription target.', self)

    def userHasBugSubscriptions(self, user):
        """See `IStructuralSubscriptionTarget`."""
        bug_subscriptions = self.getSubscriptions(
            min_bug_notification_level=BugNotificationLevel.METADATA)
        if user is not None:
            for subscription in bug_subscriptions:
                if (subscription.subscriber == user or
                    user.inTeam(subscription.subscriber)):
                    # The user has a bug subscription
                    return True
        return False
