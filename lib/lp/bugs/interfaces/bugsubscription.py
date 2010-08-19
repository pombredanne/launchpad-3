# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Bug subscription interfaces."""

__metaclass__ = type

__all__ = [
    'IBugSubscription',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Int, Choice, Datetime
from canonical.launchpad import _

from lp.bugs.interfaces.bug import IBug
from lp.registry.enum import BugNotificationLevel
from lp.services.fields import PersonChoice

from lazr.restful.declarations import (
    REQUEST_USER, call_with, export_as_webservice_entry,
    export_read_operation, exported)
from lazr.restful.fields import Reference


class IBugSubscription(Interface):
    """The relationship between a person and a bug."""

    export_as_webservice_entry()

    id = Int(title=_('ID'), readonly=True, required=True)
    person = exported(PersonChoice(
        title=_('Person'), required=True, vocabulary='ValidPersonOrTeam',
        readonly=True, description=_("The person's Launchpad ID or "
        "e-mail address.")))
    bug = exported(Reference(
        IBug, title=_("Bug"), required=True, readonly=True))
    bug_notification_level = Choice(
        title=_("Bug notification level"), required=True,
        vocabulary=BugNotificationLevel,
        default=BugNotificationLevel.COMMENTS,
        description=_(
            "The volume and type of bug notifications "
            "this subscription will generate."))
    date_created = exported(
        Datetime(title=_('Date subscribed'), required=True, readonly=True))
    subscribed_by = exported(PersonChoice(
        title=_('Subscribed by'), required=True,
        vocabulary='ValidPersonOrTeam', readonly=True,
        description=_("The person who created this subscription.")))

    display_subscribed_by = Attribute(
        "`subscribed_by` formatted for display.")

    @call_with(user=REQUEST_USER)
    @export_read_operation()
    def canBeUnsubscribedByUser(user):
        """Can the user unsubscribe the subscriber from the bug?"""
