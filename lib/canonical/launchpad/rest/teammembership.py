# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad team memberships."""

__metaclass__ = type
__all__ = [
    'ITeamMembershipEntry',
    'TeamMembershipEntry',
    'PersonTeamMembershipCollection'
    ]

from zope.component import adapts, getUtility
from zope.schema import Object, Text

from canonical.lazr.rest import Collection, Entry, ScopedCollection
from canonical.lazr.interfaces import IEntry
from canonical.lazr.rest.schema import CollectionField

from canonical.launchpad.interfaces import (
    IPerson, ITeamMembership, make_person_name_field)

from canonical.lp import decorates

class ITeamMembershipEntry(IEntry):
    """The part of a team membership that we expose through the web service."""

    # XXX leonardr 2008-01-28 bug=186702 A much better solution would
    # let us reuse or copy fields from IPerson.
    team = Object(schema=IPerson)
    member = Object(schema=IPerson)
    reviewer = Object(schema=IPerson)

    date_joined = Text(title=u"Date Joined", required=True, readonly=True)
    date_expires = Text(title=u"Date Expires", required=False, readonly=False)
    reviewer_comment = Text(title=u"Reviewer Comment", required=False,
                           readonly=False)
    status = Text(title=u"Status of the membership", required=True)


class TeamMembershipEntry(Entry):
    """A proposed or actual membership in a team."""
    adapts(ITeamMembership)
    decorates(ITeamMembershipEntry)
    schema = ITeamMembershipEntry

    parent_collection_name = 'people'

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
    def reviewer_comment(self):
        """See `ITeamMembershipEntry`."""
        return self.context.reviewercomment


class PersonTeamMembershipCollection(ScopedCollection):
    """A collection of team memberships for a person.

    There will be one membership for each team of which the person is
    a member.
    """

    def getEntryPath(self, entry):
        """See `ICollection`."""
        if self.relationship.relationship_name == 'teams':
            return entry.team.name
        else:
            return entry.member.name

    def lookupEntry(self, name):
        """Find a membership by team name."""
        for membership in self.collection:
            if self.relationship.relationship_name == 'teams':
                if membership.team.name == name:
                    return membership
            else:
                if membership.team.name == name:
                    return membership
        else:
            return None


class TeamTeamMembershipCollection(ScopedCollection):
    """A collection of team memberships for a team.

    There will be one membership for each person who's a member of the
    team.
    """

    def getEntryPath(self, entry):
        """See `ICollection`."""
        return entry.member.name

    def lookupEntry(self, name):
        """Find a membership by member name."""
        membership = [membership for membership in self.context
                      if membership.member.name == name]
        if len(memberships) == 0:
            return None
        else:
            return memberships[0]
