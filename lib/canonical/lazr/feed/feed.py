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

from datetime import datetime

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

    # XXX bac - need caching headers, including expiration, etc.

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

    def getSiteURL(self):
        raise NotImplementedError

    def getItems(self):
        raise NotImplementedError

    def itemToFeedEntry(self, item):
        raise NotImplementedError

    def getLogo(self):
        """Get the URL for the feed logo."""
        raise NotImplementedError

    def getUpdated(self):
        """Get the update time for the feed.

        By default this is set to the most recent update of the entries in the
        feed.
        """
        items = self.getItems()
        return items[0].date_updated

    def getNow(self):
        # isoformat returns the seconds to six decimal places
        # which confuses Atom readers
        #return "%sZ" % datetime.utcnow().isoformat()
        return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    @property
    def template(self):
        return ViewPageTemplateFile(self.template_file)

    def render(self):
        # XXX, bac - This call looks funny, but the callable template must be
        # passed a reference to the view.  The first use of self is to
        # reference the property.
        return self.template(self)

class FeedEntry:
    # XXX bac, This needs to be cleaned up.  Have an __init__ with the
    # required elements with no default and optional defined elements with
    # defaults.  Extension elements should go in a dictionary.  How will
    # output format be specified?
    title = None
    URL = None
    content = None
    date_published = None
    date_updated = None
    author = None
    id_ = None
