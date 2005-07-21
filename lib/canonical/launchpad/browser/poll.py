# Copyright 2004 Canonical Ltd

__metaclass__ = type

__all__ = ['PollListView', 'PollView', 'PollAddView', 'PollOptionListView',
           'PollOptionAddView']

from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.app.form.browser.add import AddView

from canonical.launchpad.webapp import canonical_url


class PollListView:
    """A view class to display all polls of a given team."""
    
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.openpolls = self.context.getOpenPolls()
        self.closedpolls = self.context.getClosedPolls()
        self.notyetopenedpolls = self.context.getNotYetOpenedPolls()

    def hasCurrentPolls(self):
        """Return True if this team has any poll that is already open or that
        is not yet opened."""
        return bool(len(self.openpolls) or len(self.notyetopenedpolls))


class PollView:
    """A view class to display the poll itself.

    It gives you (if you're a member of the team this poll is in) the option
    to vote if the poll is not closed or the results of the poll if it's
    already closed.
    """
    pass


class PollAddView(AddView):
    """The view class to create a new poll in a given team."""

    _nextURL = '.'

    def nextURL(self):
        return self._nextURL

    def createAndAdd(self, data):
        kw = {}
        for key, value in data.items():
            kw[str(key)] = value

        poll = self.context.new(
            kw['name'], kw['title'], kw['proposition'], kw['dateopens'],
            kw['datecloses'], kw['type'], kw['secrecy'], kw['allowspoilt'])
        self._nextURL = canonical_url(poll)
        notify(ObjectCreatedEvent(poll))


class PollOptionListView:
    """A view class to display all options of a given poll."""
    pass


class PollOptionAddView(AddView):
    """The view class to create a new option in a given poll."""

    _nextURL = '.'

    def nextURL(self):
        return self._nextURL

    def createAndAdd(self, data):
        kw = {}
        for key, value in data.items():
            kw[str(key)] = value

        polloption = self.context.new(kw['name'], kw['shortname'])
        self._nextURL = canonical_url(polloption.poll)
        notify(ObjectCreatedEvent(polloption))

