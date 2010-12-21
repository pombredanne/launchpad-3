# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0213

"""StructuralSubscription interfaces."""

__metaclass__ = type

__all__ = [
    'BlueprintNotificationLevel',
    'BugNotificationLevel',
    'IStructuralSubscription',
    'IStructuralSubscriptionForm',
    'IStructuralSubscriptionTarget',
    'IStructuralSubscriptionTargetHelper',
    ]

from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    )
from lazr.restful.declarations import (
    call_with,
    export_as_webservice_entry,
    export_factory_operation,
    export_read_operation,
    export_write_operation,
    exported,
    operation_parameters,
    operation_returns_collection_of,
    operation_returns_entry,
    REQUEST_USER,
    )
from lazr.restful.fields import (
    CollectionField,
    Reference,
    )
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Bool,
    Choice,
    Datetime,
    Int,
    )

from canonical.launchpad import _
from lp.registry.enum import BugNotificationLevel
from lp.registry.interfaces.person import IPerson
from lp.services.fields import (
    PersonChoice,
    PublicPersonChoice,
    )


class BlueprintNotificationLevel(DBEnumeratedType):
    """Bug Notification Level.

    The type and volume of blueprint notification email sent to subscribers.
    """

    NOTHING = DBItem(10, """
        Nothing

        Don't send any notifications about blueprints.
        """)

    LIFECYCLE = DBItem(20, """
        Lifecycle

        Only send a low volume of notifications about new blueprints
        registered, blueprints accepted or blueprint targetting.
        """)

    METADATA = DBItem(30, """
        Details

        Send blueprint lifecycle notifications, as well as notifications about
        changes to the blueprints's details like status and description.
        """)


class IStructuralSubscription(Interface):
    """A subscription to a Launchpad structure."""
    export_as_webservice_entry()

    id = Int(title=_('ID'), readonly=True, required=True)
    product = Int(title=_('Product'), required=False, readonly=True)
    productseries = Int(
        title=_('Product series'), required=False, readonly=True)
    project = Int(title=_('Project group'), required=False, readonly=True)
    milestone = Int(title=_('Milestone'), required=False, readonly=True)
    distribution = Int(title=_('Distribution'), required=False, readonly=True)
    distroseries = Int(
        title=_('Distribution series'), required=False, readonly=True)
    sourcepackagename = Int(
        title=_('Source package name'), required=False, readonly=True)
    subscriber = exported(PersonChoice(
        title=_('Subscriber'), required=True, vocabulary='ValidPersonOrTeam',
        readonly=True, description=_("The person subscribed.")))
    subscribed_by = exported(PublicPersonChoice(
        title=_('Subscribed by'), required=True,
        vocabulary='ValidPersonOrTeam', readonly=True,
        description=_("The person creating the subscription.")))
    bug_notification_level = Choice(
        title=_("Bug notification level"), required=True,
        vocabulary=BugNotificationLevel,
        default=BugNotificationLevel.NOTHING,
        description=_("The volume and type of bug notifications "
                      "this subscription will generate."))
    blueprint_notification_level = Choice(
        title=_("Blueprint notification level"), required=True,
        vocabulary=BlueprintNotificationLevel,
        default=BlueprintNotificationLevel.NOTHING,
        description=_("The volume and type of blueprint notifications "
                      "this subscription will generate."))
    date_created = exported(Datetime(
        title=_("The date on which this subscription was created."),
        required=False, readonly=True))
    date_last_updated = exported(Datetime(
        title=_("The date on which this subscription was last updated."),
        required=False, readonly=True))

    target = exported(Reference(
        schema=Interface, # IStructuralSubscriptionTarget
        required=True, readonly=True,
        title=_("The structure to which this subscription belongs.")))

    bug_filters = exported(CollectionField(
        title=_('List of bug filters that narrow this subscription.'),
        readonly=True, required=False,
        value_type=Reference(schema=Interface)))

    @export_factory_operation(Interface, [])
    def newBugFilter():
        """Returns a new `BugSubscriptionFilter` for this subscription."""


class IStructuralSubscriptionTargetRead(Interface):
    """A Launchpad Structure allowing users to subscribe to it.

    Read-only parts.
    """

    # We don't really want to expose the level details yet. Only
    # BugNotificationLevel.COMMENTS is used at this time.
    @call_with(
        min_bug_notification_level=BugNotificationLevel.COMMENTS,
        min_blueprint_notification_level=BlueprintNotificationLevel.NOTHING)
    @operation_returns_collection_of(IStructuralSubscription)
    @export_read_operation()
    def getSubscriptions(min_bug_notification_level,
                         min_blueprint_notification_level):
        """Return all the subscriptions with the specified levels.

        :min_bug_notification_level: The lowest bug notification level
          for which subscriptions should be returned.
        :min_blueprint_notification_level: The lowest bleuprint
          notification level for which subscriptions should
          be returned.
        :return: A sequence of `IStructuralSubscription`.
        """

    parent_subscription_target = Attribute(
        "The target's parent, or None if one doesn't exist.")

    bug_subscriptions = Attribute(
        "All subscriptions to bugs at the METADATA level or higher.")

    def userCanAlterSubscription(subscriber, subscribed_by):
        """Check if a user can change a subscription for a person."""

    def userCanAlterBugSubscription(subscriber, subscribed_by):
        """Check if a user can change a bug subscription for a person."""

    @operation_parameters(person=Reference(schema=IPerson))
    @operation_returns_entry(IStructuralSubscription)
    @export_read_operation()
    def getSubscription(person):
        """Return the subscription for `person`, if it exists."""

    target_type_display = Attribute("The type of the target, for display.")

    def userHasBugSubscriptions(user):
        """Is `user` subscribed, directly or via a team, to bug mail?"""

    def getSubscriptionsForBugTask(bug, level):
        """Return subscriptions for a given `IBugTask` at `level`."""


class IStructuralSubscriptionTargetWrite(Interface):
    """A Launchpad Structure allowing users to subscribe to it.

    Modify-only parts.
    """

    def addSubscription(subscriber, subscribed_by):
        """Add a subscription for this structure.

        This method is used to create a new `IStructuralSubscription`
        for the target, with no levels set.

        :subscriber: The IPerson who will be subscribed. If omitted,
            subscribed_by will be used.
        :subscribed_by: The IPerson creating the subscription.
        :return: The new subscription.
        """

    @operation_parameters(
        subscriber=Reference(
            schema=IPerson,
            title=_(
                'Person to subscribe. If omitted, the requesting user will be'
                ' subscribed.'),
            required=False))
    @call_with(subscribed_by=REQUEST_USER)
    @export_factory_operation(IStructuralSubscription, [])
    def addBugSubscription(subscriber, subscribed_by,
                           bug_notification_level=None):
        """Add a bug subscription for this structure.

        This method is used to create a new `IStructuralSubscription`
        for the target with the bug notification level set to
        COMMENTS, the only level currently in use.

        :subscriber: The IPerson who will be subscribed. If omitted,
            subscribed_by will be used.
        :subscribed_by: The IPerson creating the subscription.
        :bug_notification_level: The BugNotificationLevel for the
            subscription. If omitted, BugNotificationLevel.COMMENTS will be
            used.
        :return: The new bug subscription.
        """

    @operation_parameters(
        subscriber=Reference(
            schema=IPerson,
            title=_(
                'Person to unsubscribe. If omitted, the requesting user will '
                'be unsubscribed.'),
            required=False))
    @call_with(unsubscribed_by=REQUEST_USER)
    @export_write_operation()
    def removeBugSubscription(subscriber, unsubscribed_by):
        """Remove a subscription to bugs from this structure.

        If subscription levels for other applications are set,
        set the subscription's `bug_notification_level` to
        `NOTHING`, otherwise, destroy the subscription.

        :subscriber: The IPerson who will be unsubscribed. If omitted,
            unsubscribed_by will be used.
        :unsubscribed_by: The IPerson removing the subscription.
        """


class IStructuralSubscriptionTarget(IStructuralSubscriptionTargetRead,
                                    IStructuralSubscriptionTargetWrite):
    """A Launchpad Structure allowing users to subscribe to it."""
    export_as_webservice_entry()


class IStructuralSubscriptionTargetHelper(Interface):
    """Provides information on subscribable objects."""

    target = Attribute("The target.")

    target_parent = Attribute(
        "The target's parent, or None if one doesn't exist.")

    target_type_display = Attribute(
        "The type of the target, for display.")

    target_arguments = Attribute(
        "A dict of arguments that can be used as arguments to the "
        "structural subscription constructor.")

    pillar = Attribute(
        "The pillar most closely corresponding to the context.")

    join = Attribute(
        "A Storm join to get the `IStructuralSubscription`s relating "
        "to the context.")


class IStructuralSubscriptionForm(Interface):
    """Schema for the structural subscription form."""
    subscribe_me = Bool(
        title=u"I want to receive these notifications by e-mail.",
        required=False)
