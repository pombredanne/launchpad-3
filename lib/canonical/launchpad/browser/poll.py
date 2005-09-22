# Copyright 2004 Canonical Ltd

__metaclass__ = type

__all__ = ['BasePollView', 'PollView', 'PollVoteView', 'PollAddView',
           'PollOptionAddView']

from zope.event import notify
from zope.component import getUtility
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.app.form.browser.add import AddView

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.interfaces import (
    IPollSubset, ILaunchBag, IVoteSet, IPollOptionSet)
from canonical.lp.dbschema import PollAlgorithm, PollSecrecy


class BasePollView:
    """A base view class to be used in other poll views."""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user
        self.token = None
        self.gotTokenAndVotes = False
        self.feedback = ""

    def setUpTokenAndVotesForNonSecretPolls(self):
        """Get the votes of the logged in user in this poll.

        Set the votes in instance variables and also set self.gotTokenAndVotes
        to True, so the templates know they can display the vote.

        This method should be used only on non-secret polls and if the logged
        in user has voted on this poll.
        """
        assert not self.isSecret() and self.userVoted()
        votes = self.context.getVotesByPerson(self.user)
        assert votes, (
            "User %r hasn't voted on poll %r" % (self.user, self.context))
        if self.isSimple():
            # Here we have only one vote.
            self.currentVote = votes[0]
            self.token = self.currentVote.token
        elif self.isCondorcet():
            # Here we have multiple votes, and the token is the same in
            # all of them.
            self.currentVotes = sorted(votes, key=lambda v: v.preference)
            self.token = self.currentVotes[0].token
        self.gotTokenAndVotes = True

    def setUpTokenAndVotesForSecretPolls(self):
        """Get the votes with the token provided in the form.
        
        Set the votes, together with the token in instance variables. Also
        set self.gotTokenAndVotes to True, so the templates know they can
        display the vote.

        Return True if there's any vote with the given token and the votes
        are on this poll.

        This method should be used only on secret polls and if the logged
        in user has voted on this poll.
        """
        assert self.isSecret() and self.userVoted()
        self.token = self.request.form.get('token')
        votes = getUtility(IVoteSet).getByToken(self.token)
        if not votes:
            self.feedback = ("There's no vote associated with the token %s"
                             % self.token)
            return False

        # All votes with a given token must be on the same poll. That means
        # checking the poll of the first vote is enough.
        if votes[0].poll != self.context:
            self.feedback = ("The vote associated with the token %s is not "
                             "a vote on this poll." % self.token)
            return False

        if self.isSimple():
            # A simple poll has only one vote, because you can choose only one
            # option.
            self.currentVote = votes[0]
        elif self.isCondorcet():
            self.currentVotes = sorted(votes, key=lambda v: v.preference)
        self.gotTokenAndVotes = True
        return True

    def userCanVote(self):
        """Return True if the user is/was eligible to vote on this poll."""
        return (self.user and self.user.inTeam(self.context.team))

    def userVoted(self):
        """Return True if the user voted on this poll."""
        return (self.user and self.context.personVoted(self.user))

    def isCondorcet(self):
        """Return True if this poll's type is Condorcet."""
        return self.context.type == PollAlgorithm.CONDORCET

    def isSimple(self):
        """Return True if this poll's type is Simple."""
        return self.context.type == PollAlgorithm.SIMPLE

    def isSecret(self):
        """Return True if this is a secret poll."""
        return self.context.secrecy == PollSecrecy.SECRET


class PollView(BasePollView):
    """A view class to display the results of a poll."""

    def __init__(self, context, request):
        BasePollView.__init__(self, context, request)
        if (self.userCanVote() and context.isOpen() and
            context.getActiveOptions()):
            context_url = canonical_url(context)
            if self.isSimple():
                request.response.redirect("%s/+vote-simple" % context_url)
            elif self.isCondorcet():
                request.response.redirect("%s/+vote-condorcet" % context_url)

    def setUpTokenAndVotes(self):
        """Set up the token and votes to be displayed."""
        if not self.userVoted():
            return

        # For secret polls we can only display the votes after the token
        # is submitted.
        if self.request.method == 'POST' and self.isSecret():
            self.setUpTokenAndVotesForSecretPolls()
        elif not self.isSecret():
            self.setUpTokenAndVotesForNonSecretPolls()

    def getVotesByOption(self, option):
        """Return the number of votes the given option received."""
        return getUtility(IVoteSet).getVotesByOption(option)

    def getPairwiseMatrixWithHeaders(self):
        """Return the pairwise matrix with headers being the option's names."""
        # Get a mutable matrix.
        pairwise_matrix = list(self.context.getPairwiseMatrix())
        headers = [None]
        for idx, option in enumerate(self.context.getAllOptions()):
            headers.append(option.shortname)
            # Get a mutable row.
            row = list(pairwise_matrix[idx])
            row.insert(0, option.shortname)
            pairwise_matrix[idx] = row
        pairwise_matrix.insert(0, headers)
        return pairwise_matrix


class PollVoteView(BasePollView):
    """A view class to where the user can vote on a poll.

    If the user already voted, the current vote is displayed and the user can
    change it. Otherwise he can register his vote.
    """

    def processForm(self):
        """Process the form, if it was submitted."""
        if not self.isSecret():
            # For non-secret polls, the user's vote is always displayed
            self.setUpTokenAndVotesForNonSecretPolls()

        if self.request.method != 'POST':
            return

        if self.isSecret() and self.userVoted():
            if not self.setUpTokenAndVotesForSecretPolls():
                # Not possible to get the votes. Probably the token was wrong.
                return
            
        if 'showvote' in self.request.form:
            # The user only wants to see the vote.
            return
        
        if not self.context.isOpen():
            self.feedback = "This poll is not open. You can't vote anymore."

        if self.isSimple():
            self.processSimpleVotingForm()
        else:
            self.processCondorcetVotingForm()

    def processSimpleVotingForm(self):
        """Process the simple-voting form to change a user's vote or register
        a new one."""
        context = self.context
        newoption_id = self.request.form.get('newoption')
        if newoption_id == 'donotchange':
            return
        elif newoption_id == 'none':
            newoption = None
        else:
            newoption = getUtility(IPollOptionSet).getByPollAndId(
                context, newoption_id)

        if self.userVoted():
            self.currentVote.option = newoption
            self.feedback = "Your vote was changed successfully."
        else:
            self.currentVote = context.storeSimpleVote(self.user, newoption)
            self.token = self.currentVote.token
            self.currentVote = self.currentVote
            if self.isSecret():
                self.feedback = (
                    "Your vote has been recorded. If you want to view or "
                    "change it later you must write down this key: %s"
                    % self.token)
            else:
                self.feedback = (
                    "Your vote was stored successfully. You can come back to "
                    "this page at any time before this poll closes to view "
                    "or change your vote, if you want.")

    def processCondorcetVotingForm(self):
        """Process the condorcet-voting form to change a user's vote or 
        register a new one."""
        form = self.request.form
        activeoptions = self.context.getActiveOptions()
        newvotes = {}
        for option in activeoptions:
            try:
                preference = int(form.get('option_%d' % option.id))
            except ValueError:
                # XXX: User tried to specify a value which we can't convert to
                # an integer. Better thing to do would be to notify the user
                # and ask him to fix it. -- Guilherme Salgado 2005-09-14
                preference = None
            newvotes[option] = preference
        
        if self.userVoted():
            # This is a vote change.
            # For now it's not possible to have votes in an inactive option,
            # but it'll be in the future as we'll allow people to make options
            # inactive after a poll opens.
            assert len(activeoptions) == len(self.currentVotes)
            for vote in self.currentVotes:
                vote.preference = newvotes.get(vote.option)
            self.currentVotes.sort(key=lambda v: v.preference)
            self.feedback = "Your vote was changed successfully."
        else:
            # This is a new vote.
            votes = self.context.storeCondorcetVote(self.user, newvotes)
            self.token = votes[0].token
            self.currentVotes = sorted(votes, key=lambda v: v.preference)
            if self.isSecret():
                self.feedback = (
                    "Your vote has been recorded. If you want to view or "
                    "change it later you must write down this key: %s"
                    % self.token)
            else:
                self.feedback = (
                    "Your vote was stored successfully. You can come back to "
                    "this page at any time before this poll closes to view "
                    "or change your vote, if you want.")


class PollAddView(AddView):
    """The view class to create a new poll in a given team."""

    _nextURL = '.'

    def nextURL(self):
        return self._nextURL

    def createAndAdd(self, data):
        pollsubset = IPollSubset(self.context)
        poll = pollsubset.new(
            data['name'], data['title'], data['proposition'],
            data['dateopens'], data['datecloses'],
            data['secrecy'], data['allowspoilt'])
        self._nextURL = canonical_url(poll)
        notify(ObjectCreatedEvent(poll))


class PollOptionAddView(AddView):
    """The view class to create a new option in a given poll."""

    _nextURL = '.'

    def nextURL(self):
        return self._nextURL

    def createAndAdd(self, data):
        polloption = self.context.newOption(data['name'], data['shortname'])
        self._nextURL = canonical_url(self.context)
        notify(ObjectCreatedEvent(polloption))

