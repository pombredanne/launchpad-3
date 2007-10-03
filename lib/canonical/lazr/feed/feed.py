# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Base classes for feeds.

Supported feeds include Atom, Javascript, and HTML-snippets.
Future support may include feeds such as sparklines.
"""

__metaclass__ = type

__all__ = [
    'FeedBase',
    'FeedEntry',
    'FeedPerson',
    'FeedTypedData',
    'MINUTES',
    ]

from datetime import datetime
import time

from zope.app.pagetemplate import ViewPageTemplateFile
from zope.app.datetimeutils import rfc1123_date 

# XXX - bac - 20 Sept 2007, modules in canonical.lazr should not import from
# canonical.launchpad, but we're doing it here as an expediency to get a
# working prototype.
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp import LaunchpadFormView
from canonical.launchpad.webapp.publisher import LaunchpadView


MINUTES = 60


class FeedBase(LaunchpadFormView):
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
    # XXX - bac 2-Oct-2007 - this should be in a config file
    quantity = 25
    items = None
    template_files = {'atom': 'templates/feed-atom.pt',
                      'html': 'templates/feed-html.pt'}

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
        return self.request.getApplicationURL()

    def getItems(self):
        raise NotImplementedError

    def itemToFeedEntry(self, item):
        raise NotImplementedError

    def getLogo(self):
        """Get the URL for the feed logo."""
        raise NotImplementedError

    def getIcon(self):
        """Get the icon for the feed."""
        return "%s/@@/launchpad" % self.getSiteURL()

    def getUpdated(self):
        """Get the update time for the feed.

        By default this is set to the most recent update of the entries in the
        feed.
        """
        if self.items is None:
            items = self.getItems()
        if len(self.items) == 0:
            return None
        return self.items[0].date_updated

    def getNow(self):
        # isoformat returns the seconds to six decimal places
        # which confuses Atom readers
        #return "%sZ" % datetime.utcnow().isoformat()
        return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


    def render(self):
        expires = rfc1123_date(time.time() + self.max_age)
        # self.getUpdated() can't run until after initialize() runs
        last_modified = rfc1123_date(
                            time.mktime(self.getUpdated().timetuple()))
        response = self.request.response
        response.setHeader('Expires', expires)
        response.setHeader('Cache-Control', 'max-age=%d' % self.max_age)
        response.setHeader('X-Cache-Control', 'max-age=%d' % self.max_age)
        response.setHeader('Last-Modified', last_modified)

        if self.format == 'atom':
            return self.renderAtom()
        elif self.format == 'html':
            return self.renderHTML()
        else:
            raise NotImplementedError, "Format %s is not implemented" % self.format

    def renderAtom(self):
        '''Render the object as an Atom feed.
        Override this as opposed to overriding render().'''
        # XXX, bac - This call looks funny, but the callable template must be
        # passed a reference to the view.  The first use of self is to
        # reference the property.
        return ViewPageTemplateFile(self.template_files['atom'])(self)

    def renderHTML(self):
        '''Render the object as an html feed.
        Override this as opposed to overriding render().'''
        # XXX, bac - This call looks funny, but the callable template must be
        # passed a reference to the view.  The first use of self is to
        # reference the property.
        return ViewPageTemplateFile(self.template_files['html'])(self)

class FeedEntry:
    """An entry for a feed.

    """
    def __init__(self,
                 title,
                 id_,
                 link_alternate,
                 date_updated=None,
                 date_published=None,
                 authors=None,
                 contributors=None,
                 content=None,
                 generator=None,
                 logo=None,
                 icon=None):
        self.title = title
        self.link_alternate = link_alternate
        self.content = content
        self.date_published = date_published
        self.date_updated = date_updated
        if authors is None:
            authors = []
        self.authors = authors
        if contributors is None:
            contribuors = []
        self.contributors = contributors
        self.id = id_

class FeedTypedData:

    content_types = ['text', 'html', 'xhtml']
    def __init__(self, content, content_type='text'):
        self.content = content
        if content_type not in self.content_types:
            raise ValueError, "%s: is not valid" % content_type
        self.content_type = content_type

class FeedPerson:
    def __init__(self, person):
        self.name = person.displayname
        # We don't want to disclose email addresses in public feeds.
        self.email = None
        self.uri = canonical_url(person)
