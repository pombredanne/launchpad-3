# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Bug tracker views."""

__metaclass__ = type

__all__ = [
    'BugTrackerSetView',
    'BugTrackerView',
    ]

from zope.app.publisher.browser import BrowserView
from zope.component import getUtility

from canonical.lp.dbschema import BugTrackerType
from canonical.launchpad.interfaces import IPerson, IBugTrackerSet
from canonical.launchpad.webapp import canonical_url

def newBugTracker(form, owner):
    """Process a form to create a new BugTracker Bug Tracking instance
    object."""
    # Verify that the form was in fact submitted, and that it looks like
    # the right form (by checking the contents of the submit button
    # field, called "Update").
    if not form.has_key('Register'):
        return
    if not form['Register'] == 'Register Bug Tracker':
        return
    # extract the BugTracker details, which are in self.form
    name = form['name']
    title = form['title']
    summary = form['summary']
    baseurl = form['baseurl']
    contactdetails = form['contactdetails']
    # XXX Mark Shuttleworth 05/10/04 Hardcoded Bugzilla for the moment
    bugtrackertype = BugTrackerType.BUGZILLA
    # create the new BugTracker
    btset = getUtility(IBugTrackerSet)
    bugtracker = btset.ensureBugTracker(name=name,
                          bugtrackertype=bugtrackertype,
                          title=title,
                          summary=summary,
                          baseurl=baseurl,
                          contactdetails=contactdetails,
                          owner=owner)
    # return the bugtracker
    return bugtracker


class BugTrackerSetView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = request.form

    def newBugTracker(self):
        """This method is triggered by a tal:dummy element in the page
        template, so it is run even when the page is first displayed. It
        calls newBugTracker which will check if a form has been submitted,
        and if so it creates one accordingly and redirects back to its
        display page."""
        #
        # The person who is logged in needs to end up owning this bug
        # tracking instance.
        #
        owner = IPerson(self.request.principal).id
        #
        # Try to process the form
        #
        bugtracker = newBugTracker(self.form, owner)
        if not bugtracker: return
        # Now redirect to view it again
        self.request.response.redirect(self.request.URL[-1])

class BugTrackerView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = request.form

    def edit(self):
        """Process a form to update or edit the details of a BugTracker
        object. This method is triggered by a tal:dummy element in the page
        template, so it is run even when the page is first displayed. It
        determines whether or not a form has been submitted, and if so it
        updates itself accordingly and redirects back to its display
        page."""
        #
        # Verify that the form was in fact submitted, and that it looks like
        # the right form (by checking the contents of the submit button
        # field, called "Update").
        #
        if not self.form.has_key('Update'): return
        if not self.form['Update'] == 'Update Bug Tracker': return
        #
        # Update the BugTracker, which is in self.context
        #
        self.context.title = self.form['title']
        self.context.summary = self.form['summary']
        self.context.baseurl = self.form['baseurl']
        self.context.contactdetails = self.form['contactdetails']
        #
        # Now redirect to view it again
        #
        self.request.response.redirect(self.request.URL[-1])

