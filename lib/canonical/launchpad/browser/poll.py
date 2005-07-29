# Copyright 2004 Canonical Ltd

__metaclass__ = type

__all__ = ['PollView', 'PollAddView', 'PollOptionAddView']

from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.app.form.browser.add import AddView

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.interfaces import IPollSubset, IPollOptionSubset


class PollView:
    """A view class to display the poll itself.

    It gives you (if you're a member of the team this poll is in) the option
    to vote if the poll is not closed or the results of the poll if it's
    already closed.
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request


class PollAddView(AddView):
    """The view class to create a new poll in a given team."""

    _nextURL = '.'

    def nextURL(self):
        return self._nextURL

    def createAndAdd(self, data):
        pollsubset = IPollSubset(self.context)
        poll = pollsubset.new(
            data['name'], data['title'], data['proposition'],
            data['dateopens'], data['datecloses'], data['type'],
            data['secrecy'], data['allowspoilt'])
        self._nextURL = canonical_url(poll)
        notify(ObjectCreatedEvent(poll))


class PollOptionAddView(AddView):
    """The view class to create a new option in a given poll."""

    _nextURL = '.'

    def nextURL(self):
        return self._nextURL

    def createAndAdd(self, data):
        optionsubset = IPollOptionSubset(self.context)
        polloption = optionsubset.new(data['name'], data['shortname'])
        self._nextURL = canonical_url(polloption.poll)
        notify(ObjectCreatedEvent(polloption))

