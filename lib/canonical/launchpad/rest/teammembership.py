# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad team memberships."""

__metaclass__ = type
__all__ = [
    'ITeamMembershipEntry',
    'TeamMembershipEntry',
    ]

from zope.component import adapts
from zope.interface import classProvides
from zope.schema import Object, Text

from canonical.lazr import decorates
from canonical.lazr.rest import Entry
from canonical.lazr.interfaces import IEntry, IEntryWADLSpecification

from canonical.launchpad.interfaces import IPerson, ITeamMembership


class ITeamMembershipEntry(IEntry):
    """The part of a team membership exposed through the web service."""

    # XXX leonardr 2008-01-28 bug=186702 A much better solution would
    # let us reuse or copy fields from IPerson.
    team = Object(schema=IPerson)
    member = Object(schema=IPerson)
    last_changed_by = Object(schema=IPerson)

    date_joined = Text(title=u"Date Joined", required=True, readonly=True)
    date_expires = Text(title=u"Date Expires", required=False, readonly=False)
    last_change_comment = Text(
        title=u"Comment on the last change", required=False, readonly=False)
    status = Text(title=u"Status of the membership", required=True)


class TeamMembershipEntry(Entry):
    """A proposed or actual membership in a team."""
    adapts(ITeamMembership)
    decorates(ITeamMembershipEntry)
    schema = ITeamMembershipEntry
    classProvides(IEntryWADLSpecification)

    @property
    def member(self):
        """See `ITeamMembershipEntry`."""
        return self.context.person

    @property
    def date_joined(self):
        """See `ITeamMembershipEntry`."""
        return self.context.datejoined

    @property
    def date_expires(self):
        """See `ITeamMembershipEntry`."""
        return self.context.dateexpires

    @property
    def last_change_comment(self):
        """See `ITeamMembershipEntry`."""
        return self.context.last_change_comment

