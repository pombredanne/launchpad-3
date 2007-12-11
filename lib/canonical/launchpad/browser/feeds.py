# Copyright 2007 Canonical Ltd.  All rights reserved.

"""View support classes for feeds."""

__metaclass__ = type

__all__ = [
    'BugFeedLink',
    'FeedLinkBase',
    'FeedsMixin',
    'FeedsNavigation',
    'FeedsRootUrlData',
    'BugTargetLatestBugsFeedLink',
    'PersonLatestBugsFeedLink',
    ]

from zope.component import getUtility
from zope.interface import implements
from zope.security.interfaces import Unauthorized

from canonical.config import config
from canonical.launchpad.interfaces import (
    IBugSet, IBugTaskSet, IFeedsApplication, IPersonSet, IPillarNameSet,
    NotFoundError)
from canonical.launchpad.interfaces import IBugTask, IBugTarget, IPerson
from canonical.launchpad.layers import FeedsLayer
from canonical.launchpad.webapp import (
    canonical_name, canonical_url, Navigation, stepto)
from canonical.launchpad.webapp.publisher import RedirectionView
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData
from canonical.launchpad.webapp.vhosts import allvhosts


class FeedsRootUrlData:
    """`ICanonicalUrlData` for Feeds."""

    implements(ICanonicalUrlData)

    path = ''
    inside = None
    rootsite = 'feeds'

    def __init__(self, context):
        self.context = context


class FeedsNavigation(Navigation):
    """Navigation for `IFeedsApplication`."""

    usedfor = IFeedsApplication

    newlayer = FeedsLayer

    @stepto('+index')
    def redirect_index(self):
        """Redirect /+index to help.launchpad.net/Feeds site.

        This provides a useful destination for users who visit
        http://feeds.launchpad.net in their browser.  It is also useful to
        avoid OOPSes when some RSS feeders (e.g. Safari) that make a request
        to the default site.
        """
        return self.redirectSubTree(
            'https://help.launchpad.net/Feeds', status=301)

    def traverse(self, name):
        """Traverse the paths of a feed.

        If a query string is provided it is normalized.  'bugs' paths and
        persons ('~') are special cased.
        """
        # XXX: statik 2007-10-09 bug 150941
        # Need to block pages not registered on the FeedsLayer

        # Normalize the query string so caching is more effective.  This is
        # done by simply sorting the entries.

        # XXX bac 20071019, we would like to normalize with respect to case
        # too but cannot due to a problem with the bug search requiring status
        # values to be of a particular case.  See bug 154562.
        query_string = self.request.get('QUERY_STRING', '')
        fields = sorted(query_string.split('&'))
        normalized_query_string = '&'.join(fields)
        if query_string != normalized_query_string:
            # We must consume the stepstogo to prevent an error
            # trying to call RedirectionView.publishTraverse().
            while self.request.stepstogo.consume():
                pass
            target = "%s%s?%s" % (self.request.getApplicationURL(),
                                  self.request['PATH_INFO'],
                                  normalized_query_string)
            redirect = RedirectionView(target, self.request, 301)
            return redirect

        # Handle the two formats of urls:
        # http://feeds.launchpad.net/bugs/+bugs.atom?...
        # http://feeds.launchpad.net/bugs/1/bug.atom
        if name == 'bugs':
            stack = self.request.getTraversalStack()
            bug_id = stack.pop()
            if bug_id.startswith('+'):
                if config.launchpad.is_bug_search_feed_active:
                    return getUtility(IBugTaskSet)
                else:
                    raise Unauthorized("Bug search feed deactivated")
            else:
                self.request.stepstogo.consume()
                return getUtility(IBugSet).getByNameOrID(bug_id)

        # Handle persons and teams.
        # http://feeds.launchpad.net/~salgado/latest-bugs.html
        if name.startswith('~'):
            # Redirect to the canonical name before doing the lookup.
            if canonical_name(name) != name:
                return self.redirectSubTree(
                    canonical_url(self.context) + canonical_name(name),
                    status=301)
            else:
                person = getUtility(IPersonSet).getByName(name[1:])
                return person

        try:
            # Redirect to the canonical name before doing the lookup.
            if canonical_name(name) != name:
                return self.redirectSubTree(
                    canonical_url(self.context) + canonical_name(name),
                    status=301)
            else:
                return getUtility(IPillarNameSet)[name]

        except NotFoundError:
            return None


class FeedLinkBase:
    """Base class for formatting an Atom <link> tag.

    Subclasses must override:
        href: Url pointing to atom feed.

    Subclasses can override:
        title: The name of the feed as it appears in a browser.
    """
    title = 'Atom Feed'
    href = None
    rooturl = allvhosts.configs['feeds'].rooturl

    def __init__(self, context):
        self.context = context
        if not self.usedfor.providedBy(self.context):
            raise AssertionError("Context %r does not provide interface %r"
                                 % (self.context, self.usedfor))

    def render(self):
        return ('<link rel="alternate" type="application/atom+xml"'
                '      title="%s" href="%s"/>\n' % (self.title, self.href))


class BugFeedLink(FeedLinkBase):
    usedfor = IBugTask

    @property
    def title(self):
        return 'Bug %s Feed' % self.context.id

    @property
    def href(self):
        return self.rooturl + 'bugs/' + str(self.context.bug.id) + '/bug.atom'


class BugTargetLatestBugsFeedLink(FeedLinkBase):
    usedfor = IBugTarget

    @property
    def title(self):
        return 'Latest Bugs for %s' % self.context.name

    @property
    def href(self):
        if IBugTarget.providedBy(self.context):
            return self.rooturl + self.context.name + '/latest-bugs.atom'
        else:
            raise AssertionError("Invalid context=%r for LatestBugsFeedLink"
                                 % self.context)


class PersonLatestBugsFeedLink(FeedLinkBase):
    usedfor = IPerson

    @property
    def title(self):
        return 'Latest Bugs for %s' % self.context.name

    @property
    def href(self):
        if IPerson.providedBy(self.context):
            return (self.rooturl + '~' + self.context.name 
                    + '/latest-bugs.atom')
        else:
            raise AssertionError("Invalid context=%r for LatestBugsFeedLink"
                                 % self.context)


class FeedsMixin:
    """Mixin which adds the feed_links attribute to a view object.

    feed_types: This class attribute can be overridden to reduce the
        feed links that are added to the page.

    feed_links: Returns a list of objects subclassed from FeedLinkBase.
    """
    feed_types = [
        BugFeedLink,
        BugTargetLatestBugsFeedLink,
        PersonLatestBugsFeedLink,
        ]

    @property
    def feed_links(self):
        try:
            x = [feed_type(self.context)
                    for feed_type in self.feed_types
                    if feed_type.usedfor.providedBy(self.context)]
        except:
            import traceback
            traceback.print_exc()
            raise
        else:
            y = 1
        return x

