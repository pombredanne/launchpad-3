# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad bugs."""

__metaclass__ = type
__all__ = [
    'BugEntry',
    'BugCollection',
    'IBugEntry',
    ]

from zope.component import adapts, getUtility
from zope.schema import Bool, Datetime, Int, List, Object, Text, TextLine

from canonical.lazr.interfaces import IEntry
from canonical.lazr.rest import Collection, Entry
from canonical.lazr.rest.schema import CollectionField

from canonical.launchpad.rest import IMessageTargetEntry
from canonical.launchpad.interfaces import IBug, IMessage, IPerson
from canonical.launchpad.fields import (
    ContentNameField, Tag, Title)
from canonical.lp import decorates


class IBugEntry(IMessageTargetEntry):
    """The part of a bug that we expose through the web service."""

    id = Int(title=_(u'Bug ID'), required=True, readonly=True)
    datecreated = Datetime(
        title=_(u'Date Created'), required=True, readonly=True)
    date_last_updated = Datetime(
        title=_(u'Date Last Updated'), required=True, readonly=True)
    name = ContentNameField(
        title=_(u'Nickname'), required=False,
        description=_(u"""A short and unique name.
        Add one only if you often need to retype the URL
        but have trouble remembering the bug number."""))
    title = Title(
        title=_(u'Summary'), required=True,
        description=_(u"""A one-line summary of the problem."""))
    description = Text(
        title=_(u'Description'), required=True,
        description=_(u"""A detailed description of the problem,
        including the steps required to reproduce it."""),
        max_length=50000)
    owner = Object(schema=IPerson)
    duplicate_of = Object(schema=IBug)
    private = Bool(
        title=_(u"This bug report should be private"), required=False,
        description=_(
            u"Private bug reports are visible only to their subscribers."),
        default=False)
    date_made_private = Datetime(
        title=_(u'Date Made Private'), required=False)
    who_made_private = Object(schema=IPerson)
    security_related = Bool(
        title=_(u"This bug is a security vulnerability"), required=False,
        default=False)
    # We might not want to expose displayname
    displayname = TextLine(title=_(u"Text of the form 'Bug #X"),
        readonly=True)
    tags = List(
        title=_(u"Tags"), description=_(u"Separated by whitespace."),
        value_type=Tag(), required=False)
    is_complete = Bool(
        title=_(u"This bug is complete."),
        description = _(u"A bug is Launchpad is completely addressed "
                        "when there are no tasks that are still open "
                        "for the bug."))
    permits_expiration = Bool(
        title=_(u"Does the bug's state permit expiration? "
        "Expiration is permitted when the bug is not valid anywhere, "
        "a message was sent to the bug reporter, and the bug is associated "
        "with pillars that have enabled bug expiration."))
    can_expire = Bool(
        title=_(u"Can the Incomplete bug expire if it becomes inactive? "
        "Expiration may happen when the bug permits expiration, and a "
        "bugtask cannot be confirmed."))
    date_last_message = Datetime(
        title=_(u'Date of last bug message'), required=False, readonly=True)

    # Comment this out to demonstrate that inherited fields don't show
    # up.
    followup_subject = TextLine(
        title=_(u"The likely subject of the next message."))
    messages = CollectionField(value_type=Object(schema=IMessage))

    #initial_message = Object(schema=IMessage)
    # implement and include IMessageTargetEntry
    #activity = CollectionField(value_type=Object(schema=IActivity))
    #bugtasks = CollectionField(value_type=Object(schema=IBugTask))
    #affected_pillars = CollectionField(value_type=Object(schema=IPillar))
    #watches = CollectionField(value_type=Object(schema=IBugWatch))
    #cves = CollectionField(value_type=Object(schema=ICVE))
    #subscriptions = CollectionField(type="many_to_many",
    #                                value_type=Object(schema=IBugSubscription))
    duplicates = CollectionField(value_type=Object(schema=IBug))
    #attachments = CollectionField(value_type=Object(schema=IBugAttachment))
    #questions = CollectionField(value_type=Object(schema=IQuestion))
    #specifications = CollectionField(value_type=Object(schema=ISpecification))
    #branches = CollectionField(value_type=Object(schema=IBranch))


class BugEntry(Entry):
    """A bug."""

    adapts(IBug)
    decorates(IBugEntry)
    schema = IBugEntry

    parent_collection_name = 'bugs'

    def fragment(self):
        """See `IEntry`."""
        return str(self.context.id)

    @property
    def duplicate_of(self):
        return self.context.duplicateof

    @property
    def followup_subject(self):
        return self.context.followup_subject()


class BugCollection(Collection):
    """A collection of bugs."""

    def lookupEntry(self, name_or_id):
        """Find a Bug by name or ID."""
        return self.context.getByNameOrID(name_or_id)

    def find(self):
        """Return all the bugs on the site."""
        return self.context.searchAsUser(None)

