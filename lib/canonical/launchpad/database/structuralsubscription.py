# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['StructuralSubscription']

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase, sqlvalues

from canonical.launchpad.interfaces import (
    BlueprintNotificationLevel, BugNotificationLevel, DeleteSubscriptionError,
    DuplicateSubscriptionError, IDistribution, IDistributionSourcePackage,
    IDistroSeries, IMilestone, IProduct, IProductSeries, IProject,
    IStructuralSubscription, IStructuralSubscriptionTarget)


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
        dbName='project', foreignKey='Project', notNull=False, default=None)
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
        dbName='subscriber', foreignKey='Person', notNull=True)
    subscribed_by = ForeignKey(
        dbName='subscribed_by', foreignKey='Person', notNull=True)
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
                from canonical.launchpad.database import (
                    DistributionSourcePackage)
                return DistributionSourcePackage(
                    self.distribution, self.sourcepackagename)
            else:
                return self.distribution
        elif self.distroseries is not None:
            return self.distroseries
        else:
            raise AssertionError, 'StructuralSubscription has no target.'


class StructuralSubscriptionTargetMixin:
    """Mixin class for implementing `IStructuralSubscriptionTarget`."""
    @property
    def subscriptions(self):
        """See `IStructuralSubscriptionTarget`."""
        if IDistributionSourcePackage.providedBy(self):
            target_clause = """
                StructuralSubscription.distribution = %s
                AND StructuralSubscription.sourcepackagename = %s
                """ % sqlvalues(self.distribution, self.sourcepackagename)
        else:
            if IProduct.providedBy(self):
                target_column = 'product'
            elif IProductSeries.providedBy(self):
                target_column = 'productseries'
            elif IProject.providedBy(self):
                target_column = 'project'
            elif IMilestone.providedBy(self):
                target_column = 'milestone'
            elif IDistribution.providedBy(self):
                target_column = 'distribution'
            elif IDistroSeries.providedBy(self):
                target_column = 'distroseries'
            else:
                raise AssertionError(
                    '%s is not a valid structural subscription target.')
            target_clause = (
                "StructuralSubscription." +
                target_column + " = %s" % sqlvalues(self))
        query = "%s AND StructuralSubscription.subscriber = Person.id" % (
            target_clause)
        contacts = StructuralSubscription.select(
            query,
            orderBy='Person.displayname',
            clauseTables=['Person'])
        contacts.prejoin(["subscriber"])
        # Use "list" here because it's possible that this list will be longer
        # than a "shortlist", though probably uncommon.
        return list(contacts)

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
        elif IProductSeries.providedBy(self):
            args['productseries'] = self
        elif IProject.providedBy(self):
            args['project'] = self
        elif IMilestone.providedBy(self):
            args['milestone'] = self
        elif IDistribution.providedBy(self):
            args['distribution'] = self
        elif IDistroSeries.providedBy(self):
            args['distroseries'] = self
        else:
            raise AssertionError(
                '%s is not a valid structural subscription target.')
        return args

    def addSubscription(self, subscriber, subscribed_by):
        """See `IStructuralSubscriptionTarget`."""
        subscription_already_exists = self.isSubscribed(subscriber)

        if subscription_already_exists:
            raise DuplicateSubscriptionError(
                "%s is already subscribed to %s." %
                (subscriber.name, self.displayname))
        else:
            return StructuralSubscription(
                distribution=self.distribution,
                sourcepackagename=self.sourcepackagename,
                subscriber=subscriber,
                subscribed_by=subscribed_by)

    def addBugSubscription(self, subscriber, subscribed_by):
        """See `IStructuralSubscriptionTarget`."""
        # This is a helper method for creating a structural
        # subscription and immediately giving it a full
        # bug notification level. It is useful so long as
        # subscriptions are mainly used to implement bug contacts.
        sub = self.addSubscription(subscriber, subscribed_by)
        sub.bug_notification_level = BugNotificationLevel.COMMENTS
        return sub

    def removeSubscription(self, person):
        """See `IStructuralSubscriptionTarget`."""
        subscription_to_remove = self.isSubscribed(person)

        if not subscription_to_remove:
            raise DeleteSubscriptionError(
                "%s is not subscribed to %s." % (
                person.name, self.displayname))
        else:
            subscription_to_remove.destroySelf()

    def isSubscribed(self, person):
        """See `IStructuralSubscriptionTarget`."""
        args = {'subscriber': person}
        args.update(self._target_args)
        subscription = StructuralSubscription.selectOneBy(**args)

        if subscription is not None:
            return subscription
        else:
            return False

    @property
    def parent(self):
        """See `IStructuralSubscriptionTarget`."""
        # Some structures have a related structure which can be thought
        # of as their parent. A package is related to a distribution,
        # a product is related to a project, etc'...
        # This method determines whether the target has a parent,
        # returning it if it exists.
        parent = None
        if IDistributionSourcePackage.providedBy(self):
            parent = self.distribution
        elif IProduct.providedBy(self):
            parent = self.project
        elif IProductSeries.providedBy(self):
            parent = self.product
        elif IDistroSeries.providedBy(self):
            parent = self.distribution
        elif IMilestone.providedBy(self):
            if self.product is not None:
                parent = self.product
            elif self.distribution is not None:
                parent = self.distribution
            elif self.distribution is not None:
                parent = self.distribution
            elif self.productseries is not None:
                parent = self.productseries
            elif self.distroseries is not None:
                parent = self.distroseries
            else:
                parent = None
        else:
            parent = None
        # We only want to return the parent it's
        # an `IStructuralSubscriptionTarget`.
        if IStructuralSubscriptionTarget.providedBy(parent):
            return parent
        else:
            return None
