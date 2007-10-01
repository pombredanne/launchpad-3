# Copyright Canonical

__metaclass__ = type

__all__ = [
    'PersonBugsFeed',
    'ProductBugsFeed',
    'SearchBugs',
    ]

import cgi
from datetime import datetime
from zope.app.pagetemplate import ViewPageTemplateFile

from canonical.lazr.feed import (
    FeedBase,FeedEntry, FeedPerson, FeedTypedData, MINUTES)

from canonical.lp import dbschema
from canonical.launchpad import helpers
from canonical.launchpad.interfaces import (
    IPerson, IProduct)
from canonical.launchpad.webapp import canonical_url, LaunchpadFormView
from canonical.launchpad.webapp.tales import FormattersAPI
from canonical.launchpad.browser import (
    BugTasksAndNominationsView, BugsBugTaskSearchListingView,
    BugTaskSearchListingView,
    PersonRelatedBugsView)

def get_sortorder_from_request(request):
    """Get the sortorder from the request.

    >>> from zope.publisher.browser import TestRequest
    >>> get_sortorder_from_request(TestRequest(form={}))
    ['-importance']
    >>> get_sortorder_from_request(TestRequest(form={'orderby': '-status'}))
    ['-status']
    >>> get_sortorder_from_request(
    ...     TestRequest(form={'orderby': 'status,-severity,importance'}))
    ['status', 'importance']
    >>> get_sortorder_from_request(
    ...     TestRequest(form={'orderby': 'priority,-severity'}))
    ['-importance']
    """
    order_by_string = request.get("orderby", '')
    if order_by_string:
        if not zope_isinstance(order_by_string, list):
            order_by = order_by_string.split(',')
        else:
            order_by = order_by_string
    else:
        order_by = []
    # Remove old order_by values that people might have in bookmarks.
    for old_order_by_column in ['priority', 'severity']:
        if old_order_by_column in order_by:
            order_by.remove(old_order_by_column)
        if '-' + old_order_by_column in order_by:
            order_by.remove('-' + old_order_by_column)
    if order_by:
        return order_by
    else:
        # No sort ordering specified, so use a reasonable default.
        return ["-importance"]


class ProductBugsFeed(FeedBase):

    # XXX, bac - This variable is currently not used.
    usedfor = IProduct

    # Will be served as:
    #     $product/latest-bugs.atom, and as
    # XXX    $product/latest-bugs.html, and as
    # XXX    $product/latest-bugs.js
    #feed_name = 'latest-bugs'
    feed_name = 'latest-bugs.atom'

    max_age = 30 * MINUTES

    def getTitle(self):
        # Title of the whole feed.
        return "Bugs in %s" % self.context.displayname

    def getURL(self):
        # URL to the homepage of the object represented by the feed.
        #return canonical_url(self.context, rootsite = "bugs")
        return "%s/%s" % (canonical_url(self.context), self.feed_name)

    def getItems(self, quantity=5):
        # Items in the feed.  The number of items is configured separately,
        # either globally for Launchpad as a whole, or in the ZCML.
        # If we find we have a requirement for different numbers of items per
        # feed, we'll include it in the class definition.
        if self.items is None:
            items = self.context.getLatestBugTasks(quantity=quantity)
            self.items = [self.itemToFeedEntry(item) for item in items]
        return self.items

    def getLogo(self):
        return "http://launchpad.dev/+icing/app-bugs.gif"

    def itemToFeedEntry(self, item):

        def unescape(s):
            s = s.replace("&lt;", "<")
            s = s.replace("&gt;", ">")
            # this has to be last:
            s = s.replace("&amp;", "&")
            return s

        bugtask = item
        bug = bugtask.bug
        self.bug = bug
        title = FeedTypedData('[%s] %s' % (bug.id, bug.title))
        url = canonical_url(bugtask, rootsite="bugs")
        formatter = FormattersAPI(bug.description)
        # XXX bac, The Atom spec says all content is to be escaped.  When it
        # is escaped Safari and Firefox do not display the HTML correctly.
        #entry.content = cgi.escape(formatter.text_to_html())
        content = formatter.text_to_html()
        template = ViewPageTemplateFile('templates/bug.pt')
        #import pdb; pdb.set_trace(); # DO NOT COMMIT
        content = template(self)
        entry = FeedEntry(title = title,
                          id_ = url,
                          link_alternate = url,
                          date_updated = bug.date_last_updated,
                          date_published = bugtask.datecreated,
                          authors = [FeedPerson(bug.owner)],
                          content = FeedTypedData(content, content_type="xhtml"))
        return entry

    def getBugTasksAndNominations(self):
        """Stolen from BugTasksAndNominationsView."""
        #import pdb; pdb.set_trace(); # DO NOT COMMIT
        bug = self.bug
        bugtasks = helpers.shortlist(bug.bugtasks)

        upstream_tasks = [
            bugtask for bugtask in bugtasks
            if bugtask.product or bugtask.productseries]

        distro_tasks = [
            bugtask for bugtask in bugtasks
            if bugtask.distribution or bugtask.distroseries]

        #upstream_tasks.sort(key=_by_targetname)
        #distro_tasks.sort(key=_by_targetname)

        all_bugtasks = upstream_tasks + distro_tasks

        # Insert bug nominations in between the appropriate tasks.
        bugtasks_and_nominations = []
        for bugtask in all_bugtasks:
            bugtasks_and_nominations.append(bugtask)

            target = bugtask.product or bugtask.distribution
            if not target:
                continue

            bugtasks_and_nominations += [
                nomination for nomination in bug.getNominations(target)
                if (nomination.status !=
                    dbschema.BugNominationStatus.APPROVED)
                ]

        return bugtasks_and_nominations

class PersonBugsFeed(FeedBase, PersonRelatedBugsView):

    usedfor = IPerson

    # Will be served as:
    #     $product/latest-bugs.atom, and as
    # XXX    $product/latest-bugs.html, and as
    # XXX    $product/latest-bugs.js
    #feed_name = 'latest-bugs'
    feed_name = 'latest-bugs.atom'

    max_age = 30 * MINUTES

    def getTitle(self):
        # Title of the whole feed.
        return "Bugs for %s" % self.context.displayname

    def getURL(self):
        # URL to the homepage of the object represented by the feed.
        #return canonical_url(self.context, rootsite = "bugs")
        return "%s/%s" % (canonical_url(self.context), self.feed_name)

    def getItems(self, quantity=5):
        # Items in the feed.  The number of items is configured separately,
        # either globally for Launchpad as a whole, or in the ZCML.
        # If we find we have a requirement for different numbers of items per
        # feed, we'll include it in the class definition.
        if self.items is None:
            #items = self.context.getLatestBugs(quantity=quantity)
            items = self.search()
            self.items = [self.itemToFeedEntry(item) for item in items]
        return self.items

    def getLogo(self):
        return "http://launchpad.dev/+icing/app-bugs.gif"

    def itemToFeedEntry(self, item):
        bugtask = item
        bug = bugtask.bug
        title = FeedTypedData('[%s] %s' % (bug.id, bug.title))
        url = canonical_url(bugtask, rootsite="bugs")
        formatter = FormattersAPI(bug.description)
        # XXX bac, The Atom spec says all content is to be escaped.  When it
        # is escaped Safari and Firefox do not display the HTML correctly.
        #entry.content = cgi.escape(formatter.text_to_html())
        content = formatter.text_to_html()
        entry = FeedEntry(title = title,
                          id_ = url,
                          link_alternate = url,
                          date_updated = bug.date_last_updated,
                          date_published = bugtask.datecreated,
                          authors = [FeedPerson(bug.owner)],
                          content = FeedTypedData(content, content_type="html"))
        return entry


class SearchBugs(FeedBase):

    # Will be served as:
    #     $product/latest-bugs.atom, and as
    # XXX    $product/latest-bugs.html, and as
    # XXX    $product/latest-bugs.js
    #feed_name = 'latest-bugs'
    feed_name = 'search-bugs.atom'

    max_age = 30 * MINUTES

    def initialize(self):
        self.task_search_listing_view = BugsBugTaskSearchListingView(self.context, self.request)
        self.task_search_listing_view.initialize()
        query_string = self.request.get('QUERY_STRING')

    def search(self, searchtext=None, context=None, extra_params=None):
        """Return an ITableBatchNavigator for the GET search criteria.

        If :searchtext: is None, the searchtext will be gotten from the
        request.

        :extra_params: is a dict that provides search params added to the
        search criteria taken from the request. Params in :extra_params: take
        precedence over request params.
        """
        import pdb; pdb.set_trace(); # DO NOT COMMIT
        #search_params = self.task_search_listing_view._getDefaultSearchParams()
        #tasks =  self.task_search_listing_view.
        results =  self.task_search_listing_view.search(searchtext, context, extra_params)
        items = results.getBugListingItems()
        return items

    def getTitle(self):
        # Title of the whole feed.
        return "Bugs from custom search."

    def getURL(self):
        # URL to the homepage of the object represented by the feed.
        #return canonical_url(self.context, rootsite = "bugs")
        return "%s/%s" % (canonical_url(self.context), self.feed_name)

    def getItems(self, quantity=5):
        # Items in the feed.  The number of items is configured separately,
        # either globally for Launchpad as a whole, or in the ZCML.
        # If we find we have a requirement for different numbers of items per
        # feed, we'll include it in the class definition.
        if self.items is None:
            #items = self.context.getLatestBugs(quantity=quantity)
            items = self.search()
            self.items = [self.itemToFeedEntry(item) for item in items]
        return self.items

    def getLogo(self):
        return "http://launchpad.dev/+icing/app-bugs.gif"

    def itemToFeedEntry(self, item):
        bugtask = item
        bug = bugtask.bug
        self.bug = bug
        title = FeedTypedData('[%s] %s' % (bug.id, bug.title))
        url = canonical_url(bugtask, rootsite="bugs")
        formatter = FormattersAPI(bug.description)
        template = ViewPageTemplateFile('templates/bug.pt')
        content = template(self)
        entry = FeedEntry(title = title,
                          id_ = url,
                          link_alternate = url,
                          date_updated = bug.date_last_updated,
                          date_published = bugtask.datecreated,
                          authors = [FeedPerson(bug.owner)],
                          content = FeedTypedData(content, content_type="html"))
        return entry

    def getBugTasksAndNominations(self):
        """Stolen from BugTasksAndNominationsView."""
        #import pdb; pdb.set_trace(); # DO NOT COMMIT
        bug = self.bug
        bugtasks = helpers.shortlist(bug.bugtasks)

        upstream_tasks = [
            bugtask for bugtask in bugtasks
            if bugtask.product or bugtask.productseries]

        distro_tasks = [
            bugtask for bugtask in bugtasks
            if bugtask.distribution or bugtask.distroseries]

        #upstream_tasks.sort(key=_by_targetname)
        #distro_tasks.sort(key=_by_targetname)

        all_bugtasks = upstream_tasks + distro_tasks

        # Insert bug nominations in between the appropriate tasks.
        bugtasks_and_nominations = []
        for bugtask in all_bugtasks:
            bugtasks_and_nominations.append(bugtask)

            target = bugtask.product or bugtask.distribution
            if not target:
                continue

            bugtasks_and_nominations += [
                nomination for nomination in bug.getNominations(target)
                if (nomination.status !=
                    dbschema.BugNominationStatus.APPROVED)
                ]

        return bugtasks_and_nominations
