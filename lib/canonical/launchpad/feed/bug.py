# Copyright Canonical

__metaclass__ = type

__all__ = [
    'PersonBugsFeed',
    'ProductBugsFeed',
    ]

import cgi
from datetime import datetime
from zope.app.pagetemplate import ViewPageTemplateFile

from canonical.lazr.feed import (
    FeedBase, FeedEntry, FeedPerson, FeedTypedData, MINUTES)

from canonical.lp import dbschema
from canonical.launchpad import helpers
from canonical.launchpad.interfaces import (
    IPerson, IProduct)
from canonical.launchpad.webapp import canonical_url, LaunchpadFormView
from canonical.launchpad.webapp.tales import FormattersAPI
from zope.app.pagetemplate import ViewPageTemplateFile
from canonical.launchpad.webapp.publisher import LaunchpadView
from canonical.launchpad.browser.bugtask import BugTaskView
from canonical.launchpad.browser import (
    PersonRelatedBugsView, BugTasksAndNominationsView, PersonRelatedBugsView)

class BugFeedContentView(LaunchpadView):
    template = ViewPageTemplateFile('templates/bug.pt')

    def getBugCommentsForDisplay(self):
        bug_task_view = BugTaskView(self.context.bugtasks[0], self.request)
        return bug_task_view.getBugCommentsForDisplay()


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
        bugtask = item
        bug = bugtask.bug
        title = FeedTypedData('[%s] %s' % (bug.id, bug.title))
        url = canonical_url(bugtask, rootsite="bugs")
        content_view = BugFeedContentView(bug, self.request)
        entry = FeedEntry(title = title,
                          id_ = url,
                          link_alternate = url,
                          date_updated = bug.date_last_updated,
                          date_published = bugtask.datecreated,
                          authors = [FeedPerson(bug.owner)],
                          content = FeedTypedData(content_view.render(), 
                                                  content_type="xhtml"))
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
        content_view = BugFeedContentView(bug, self.request)
        entry = FeedEntry(title = title,
                          id_ = url,
                          link_alternate = url,
                          date_updated = bug.date_last_updated,
                          date_published = bugtask.datecreated,
                          authors = [FeedPerson(bug.owner)],
                          content = FeedTypedData(content_view.render(), 
                                                  content_type="xhtml"))
        return entry
