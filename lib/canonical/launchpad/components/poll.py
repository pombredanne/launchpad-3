# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['PollSubset', 'PollOptionSubset']

# Zope interfaces
from zope.interface import implements
from zope.component import getUtility

# canonical imports
from canonical.launchpad.interfaces import (
    IPollSubset, IPollSet, IPollOptionSubset, IPollOptionSet,
    PollStatus)


class PollSubset:

    implements(IPollSubset)

    title = 'Team polls'

    def __init__(self, team=None):
        self.team = team

    def new(self, name, title, proposition, dateopens, datecloses,
            type, secrecy, allowspoilt):
        """See IPollSubset."""
        assert self.team is not None
        return getUtility(IPollSet).new(
            self.team, name, title, proposition, dateopens,
            datecloses, type, secrecy, allowspoilt)

    def getByName(self, name, default=None):
        """See IPollSubset."""
        assert self.team is not None
        pollset = getUtility(IPollSet)
        return pollset.getByTeamAndName(self.team, name, default)

    def getAll(self):
        """See IPollSubset."""
        assert self.team is not None
        return getUtility(IPollSet).selectByTeam(self.team)

    def getOpenPolls(self, when=None):
        """See IPollSubset."""
        assert self.team is not None
        return getUtility(IPollSet).selectByTeam(
            self.team, set([PollStatus.OPEN_POLLS]),
            orderBy='datecloses', when=when)

    def getClosedPolls(self, when=None):
        """See IPollSubset."""
        assert self.team is not None
        return getUtility(IPollSet).selectByTeam(
            self.team, set([PollStatus.CLOSED_POLLS]),
            orderBy='datecloses', when=when)

    def getNotYetOpenedPolls(self, when=None):
        """See IPollSubset."""
        assert self.team is not None
        return getUtility(IPollSet).selectByTeam(
            self.team, set([PollStatus.NOT_YET_OPENED_POLLS]),
            orderBy='dateopens', when=when)


class PollOptionSubset:

    implements(IPollOptionSubset)

    title = 'Poll options'

    def __init__(self, poll=None):
        self.poll = poll

    def new(self, name, shortname=None, active=True):
        """See IPollOptionSubset."""
        assert self.poll is not None
        # We don't want shortname to be an empty string. That's why we're not
        # testing if it's not None.
        if not shortname:
            shortname = name
        return getUtility(IPollOptionSet).new(
            self.poll, name, shortname, active)

    def get_default(self, id, default=None):
        """See IPollOptionSubset."""
        assert self.poll is not None
        option = getUtility(IPollOptionSet).getByPollAndId(self.poll, id)
        if not option:
            return default
        return option

    def getByName(self, name, default=None):
        """See IPollOptionSubset."""
        assert self.poll is not None
        optionset = getUtility(IPollOptionSet)
        return optionset.getByPollAndName(self.poll, name, default)

    def getAll(self):
        """See IPollOptionSubset."""
        assert self.poll is not None
        return getUtility(IPollOptionSet).selectByPoll(self.poll)

    def getActive(self):
        """See IPollOptionSubset."""
        assert self.poll is not None
        return getUtility(IPollOptionSet).selectByPoll(
                self.poll, only_active=True)

