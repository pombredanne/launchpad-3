# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Entitlement interfaces."""

__metaclass__ = type

__all__ = [
    'EntitlementInvalidError',
    'EntitlementQuota',
    'EntitlementQuotaExceededError',
    'EntitlementState',
    'EntitlementType',
    'IEntitlement',
    'IEntitlementSet',
    ]

from lazr.enum import (
    DBEnumeratedType,
    DBItem,
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
from lp.services.fields import Whiteboard


class EntitlementQuotaExceededError(Exception):
    """The quota has been exceeded for the entitlement."""


class EntitlementInvalidError(Exception):
    """The entitlement is not valid."""


class EntitlementType(DBEnumeratedType):
    """The set of features supported via entitlements.

    The listed features may be enabled by the granting of an entitlement.
    """

    PRIVATE_BRANCHES = DBItem(10, """
        Private Branches

        The ability to create branches which are only visible to the team.
        """)

    PRIVATE_BUGS = DBItem(20, """
        Private Bugs

        The ability to create private bugs which are only visible to the team.
        """)

    PRIVATE_TEAMS = DBItem(30, """
        Private Teams

        The ability to create private teams which are only visible to parent
        teams.
        """)


class EntitlementState(DBEnumeratedType):
    """States for an entitlement.

    The entitlement may start life as a REQUEST that is then granted and
    made ACTIVE.  At some point the entitlement may be revoked by marking
    as INACTIVE.
    """

    REQUESTED = DBItem(10, """
        Entitlement has been requested.

        The entitlement is inactive in this state.
        """)

    ACTIVE = DBItem(20, """
        The entitlement is active.

        The entitlement is approved in Launchpad or was imported in the
        active state.
        """)

    INACTIVE = DBItem(30, """
        The entitlement is inactive.

        The entitlement has be deactivated.
        """)


class IEntitlement(Interface):
    """An entitlement the right to use a specific feature in Launchpad.

    Entitlements can be granted in an unlimited quantity or with a given
    quota.  They have a start date and optionally an expiration date.  An
    entitlement is invalid if it is not active, the quota is exceeded, or if
    it is expired.
    """

    id = Int(
        title=_("Entitlement id"),
        required=True,
        readonly=True)
    person = Choice(
        title=_('Person'),
        required=True,
        readonly=True,
        vocabulary='ValidPersonOrTeam',
        description=_("Person or team to whom the entitlements is assigned."))
    date_created = Datetime(
        title=_("Date Created"),
        description=_("The date on which this entitlement was created."),
        required=True,
        readonly=True)
    date_starts = Datetime(
        title=_("Date Starts"),
        description=_("The date on which this entitlement starts."),
        readonly=False)
    date_expires = Datetime(
        title=_("Date Expires"),
        description=_("The date on which this entitlement expires."),
        readonly=False)
    entitlement_type = Choice(
        title=_("Type of entitlement."),
        required=True,
        vocabulary='EntitlementType',
        description=_("Type of feature for this entitlement."),
        readonly=True)
    quota = Int(
        title=_("Allocated quota."),
        required=True,
        description=_(
            "A quota is the number of a feature allowed by this entitlement, "
            "for instance 50 private bugs."))
    amount_used = Int(
        title=_("Amount used."),
        description=_(
            "The amount used is the number of instances of a feature "
            "the person has used so far."))
    registrant = Choice(
        title=_('Registrant'),
        vocabulary='ValidPersonOrTeam',
        description=_(
            "Person who registered the entitlement.  "
            "May be None if created automatically."),
        readonly=True)
    approved_by = Choice(
        title=_('Approved By'),
        vocabulary='ValidPersonOrTeam',
        description=_(
            "Person who approved the entitlement.  "
            "May be None if created automatically."),
        readonly=True)
    state = Choice(
        title=_("State"),
        required=True,
        vocabulary='EntitlementState',
        description = _("Current state of the entitlement."))

    whiteboard = Whiteboard(title=_('Whiteboard'), required=False,
        description=_('Notes on the current status of the entitlement.'))

    is_dirty = Bool(
        title=_("Dirty?"),
        description=_(
            "Is the entitlement 'dirty', i.e. has been written since the "
            "most recent update to an external system?"))

    is_valid = Attribute(
        "Is this entitlement valid?")

    exceeded_quota = Attribute(
        "If the quota is not unlimited, is it exceeded?")

    in_date_range = Attribute(
        "Has the start date passed but not the expiration date?")

    def incrementAmountUsed():
        """Add one to the amount used."""


class IEntitlementSet(Interface):
    """Interface representing a set of Entitlements."""

    def __getitem__(entitlement_id):
        """Return the entitlement with the given id.

        Raise NotFoundError if there is no such entitlement.
        """

    def __iter__():
        """Return an iterator that will go through all entitlements."""

    def count():
        """Return the number of entitlements in the database."""

    def get(entitlement_id, default=None):
        """Return the entitlement with the given id.

        Return the default value if there is no such entitlement.
        """

    def getForPerson(person):
        """Return the entitlements for the person or team.

        Get all entitlements for a person.
        """

    def getValidForPerson(person):
        """Return a list of valid entitlements for the person or team.

        Get all valid entitlements for a person.  None is returned if no valid
        entitlements are found.
        """

    def getDirty():
        """Return the entitlements that have the dirty bit set.

        Get all entitlements that are marked as dirty.
        """

    def new(person, quota, entitlement_type, state,
            is_dirty=True, date_created=None, date_expires=None,
            date_starts=None, amount_used=None, registrant=None,
            approved_by=None):
        """Create a new entitlement."""


class EntitlementQuota:
    """This class stores constants for entitlements quotas."""

    UNLIMITED = 0
