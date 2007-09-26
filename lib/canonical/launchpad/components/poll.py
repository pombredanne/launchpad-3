# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['PollSubset', 'PollOptionSubset']

from zope.interface import implements
from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IPollSubset, IPollSet, PollAlgorithm, PollStatus)


class PollSubset:

    implements(IPollSubset)

    title = 'Team polls'

    def __init__(self, team=None):
        self.team = team

    def new(self, name, title, proposition, dateopens, datecloses,
            secrecy, allowspoilt, poll_type=PollAlgorithm.SIMPLE):
        """See IPollSubset."""
        assert self.team is not None
        return getUtility(IPollSet).new(
            self.team, name, title, proposition, dateopens,
            datecloses, secrecy, allowspoilt, poll_type)

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
            self.team, [PollStatus.OPEN], orderBy='datecloses', when=when)

    def getClosedPolls(self, when=None):
        """See IPollSubset."""
        assert self.team is not None
        return getUtility(IPollSet).selectByTeam(
            self.team, [PollStatus.CLOSED], orderBy='datecloses', when=when)

    def getNotYetOpenedPolls(self, when=None):
        """See IPollSubset."""
        assert self.team is not None
        return getUtility(IPollSet).selectByTeam(
            self.team, [PollStatus.NOT_YET_OPENED],
            orderBy='dateopens', when=when)

