# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad bugs."""

__metaclass__ = type
__all__ = [
    'BugEntry',
    'BugCollection',
    'IBugEntry',
    'bugcomment_to_entry',
    ]

from zope.component import adapts, getUtility
from zope.schema import Bool, Datetime, Int, List, Object, Text

from canonical.lazr.rest import Collection, Entry
from canonical.lazr.interfaces.rest import IEntry
from canonical.lazr.rest.schema import CollectionField

from canonical.launchpad.rest.messagetarget import IMessageTargetEntry
from canonical.launchpad.interfaces import IBug, IBugSet, IBugTask, IPerson
from canonical.launchpad.fields import (
    ContentNameField, Tag, Title)
from canonical.lazr import decorates


class IBugEntry(IMessageTargetEntry):
    """The part of a bug that we expose through the web service."""

    id = Int(title=u'Bug ID', required=True, readonly=True)
    datecreated = Datetime(
        title=u'Date Created', required=True, readonly=True)
    date_last_updated = Datetime(
        title=u'Date Last Updated', required=True, readonly=True)
    name = ContentNameField(
        title=u'Nickname', required=False,
        description=u"""A short and unique name.
        Add one only if you often need to retype the URL
        but have trouble remembering the bug number.""")
    title = Title(
        title=u'Summary', required=True,
        description=u"""A one-line summary of the problem.""")
    description = Text(
        title=u'Description', required=True,
        description=u"""A detailed description of the problem,
        including the steps required to reproduce it.""",
        max_length=50000)
    owner = Object(schema=IPerson)
    duplicate_of = Object(schema=IBug)
    private = Bool(
        title=u"This bug report should be private", required=False,
        description=
            u"Private bug reports are visible only to their subscribers.",
        default=False)
    date_made_private = Datetime(
        title=u'Date Made Private', required=False)
    who_made_private = Object(schema=IPerson)
    security_related = Bool(
        title=u"This bug is a security vulnerability", required=False,
        default=False)
    tags = List(
        title=u"Tags", description=u"Separated by whitespace.",
        value_type=Tag(), required=False)
    is_complete = Bool(
        title=u"This bug is complete.",
        description = u"A bug is Launchpad is completely addressed "
                        "when there are no tasks that are still open "
                        "for the bug.",
        readonly=True)
    permits_expiration = Bool(
        title=u"Does the bug's state permit expiration? "
        "Expiration is permitted when the bug is not valid anywhere, "
        "a message was sent to the bug reporter, and the bug is associated "
        "with pillars that have enabled bug expiration.",
        readonly=True)
    can_expire = Bool(
        title=u"Can the Incomplete bug expire if it becomes inactive? "
        "Expiration may happen when the bug permits expiration, and a "
        "bugtask cannot be confirmed.",
        readonly=True)
    date_last_message = Datetime(
        title=u'Date of last bug message', required=False, readonly=True)

    #initial_message = Object(schema=IMessage)
    # implement and include IMessageTargetEntry
    #activity = CollectionField(value_type=Object(schema=IActivity))
    bugtasks = CollectionField(value_type=Object(schema=IBugTask))
    #affected_pillars = CollectionField(value_type=Object(schema=IPillar))
    #watches = CollectionField(value_type=Object(schema=IBugWatch))
    #cves = CollectionField(value_type=Object(schema=ICVE))
    #subscriptions = CollectionField(type="many_to_many",
    #    value_type=Object(schema=IBugSubscription))
    duplicates = CollectionField(value_type=Object(schema=IBug))
    #attachments = CollectionField(value_type=Object(schema=IBugAttachment))


class BugEntry(Entry):
    """A bug, as exposed through the web service."""

    adapts(IBug)
    decorates(IBugEntry)
    schema = IBugEntry

    @property
    def duplicate_of(self):
        """See `IBug`."""
        return self.context.duplicateof

    @property
    def followup_subject(self):
        """See `IBug`."""
        return self.context.followup_subject()


class BugCollection(Collection):
    """A collection of bugs, as exposed through the web service."""

    entry_type = BugEntry

    def find(self):
        """Return all the bugs on the site."""
        # Our context here is IMaloneApplication, that's why
        # we need getUtility.
        return getUtility(IBugSet).searchAsUser(None)


def bugcomment_to_entry(comment):
    """Will adapt to the bugcomment to the real IMessage.

    This is needed because navigation to comments doesn't return
    real IMessage instances but IBugComment.
    """
    return IEntry(comment.bugtask.bug.messages[comment.index])
