# Copyright 2007 Canonical Ltd.  All rights reserved.

"""View support classes for feeds."""

__metaclass__ = type

__all__ = [
    'FeedsNavigation',
    'FeedsRootUrlData'
    ]

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces import (
    IBugSet, IBugTaskSet, IFeedsApplication, IPersonSet, IPillarNameSet,
    NotFoundError)
from canonical.launchpad.layers import FeedsLayer
from canonical.launchpad.webapp import (
    canonical_name, canonical_url, Navigation, stepto)
from canonical.launchpad.webapp.publisher import RedirectionView
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData


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
        # http://feeds.launchpad.net/bugs/+search-bugs.atom?...
        # http://feeds.launchpad.net/bugs/1/bug.atom
        if name == 'bugs':
            stack = self.request.getTraversalStack()
            bug_id = stack.pop()
            if bug_id.startswith('+'):
                return getUtility(IBugTaskSet)
            else:
                self.request.stepstogo.consume()
                return getUtility(IBugSet).getByNameOrID(bug_id)

        # Handle persons and teams.
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
