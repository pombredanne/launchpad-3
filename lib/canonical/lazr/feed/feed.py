# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Base classes for feeds.

Supported feeds include Atom, Javascript, and HTML-snippets.
Future support may include feeds such as sparklines.
"""

__metaclass__ = type

__all__ = [
    'FeedBase',
    'FeedEntry',
    'MINUTES',
    ]

from zope.app.pagetemplate import ViewPageTemplateFile

# XXX - bac - 20 Sept 2007, modules in canonical.lazr should not import from
# canonical.launchpad, but we're doing it here as an expediency to get a
# working prototype.
from canonical.launchpad.webapp.publisher import LaunchpadView


MINUTES = 60


class FeedBase(LaunchpadView):
    """Base class for feeds.

    - context
    - request
    - initialize()  <-- subclass this for specific initialization
    - getId()
    - getUpdated()
    - getTitle()
    - getURL()
    - getItems()
    - itemToAtomFeedEntry
    """

    max_age = 60 * MINUTES
    items = []
    template_file = 'feed.pt'

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def initialize(self):
        """Override this in subclasses.

        Default implementation does nothing.
        """
        pass

    def getTitle(self):
        raise NotImplementedError

    def getURL(self):
        raise NotImplementedError

    def getItems(self):
        raise NotImplementedError

    def itemToFeedEntry(self, item):
        raise NotImplementedError

    @property
    def template(self):
        return ViewPageTemplateFile(self.template_file)

    def render(self):
        print "template file: ", self.template_file
        t = ViewPageTemplateFile(self.template_file)
        print "t: ", t
        return t(self)


class FeedEntry:
    pass
