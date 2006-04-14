# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Sprint views."""

__metaclass__ = type
__all__ = [
    'SprintFacets',
    'SprintOverviewMenu',
    'SprintSpecificationsMenu',
    'SprintSetContextMenu',
    'SprintSetNavigation',
    'SprintView',
    'SprintAddView',
    'SprintEditView',
    'SprintTopicSetView',
    ]

from zope.component import getUtility

from canonical.launchpad.interfaces import ILaunchBag, ISprint, ISprintSet

from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.browser.specificationtarget import (
    HasSpecificationsView)

from canonical.lp.dbschema import (
    SprintSpecificationStatus, SpecificationFilter)

from canonical.database.sqlbase import flush_database_updates

from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, GetitemNavigation,
    ApplicationMenu, StandardLaunchpadFacets, LaunchpadView)

from canonical.launchpad.helpers import shortlist
from canonical.cachedproperty import cachedproperty


class SprintFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for an ISprint."""

    usedfor = ISprint
    enable_only = ['overview', 'specifications']

    def specifications(self):
        text = 'Specifications'
        summary = 'Topics for discussion at %s' % self.context.title
        return Link('+specs', text, summary)


class SprintOverviewMenu(ApplicationMenu):

    usedfor = ISprint
    facet = 'overview'
    links = ['attendance', 'registration', 'edit']

    def attendance(self):
        text = 'Register Yourself'
        summary = 'Register as an attendee of the meeting'
        return Link('+attend', text, summary, icon='add')

    def registration(self):
        text = 'Register Someone'
        summary = 'Register someone else to attend the meeting'
        return Link('+register', text, summary, icon='add')

    def edit(self):
        text = 'Edit Details'
        summary = 'Modify the meeting description, dates or title'
        return Link('+edit', text, summary, icon='edit')


class SprintSpecificationsMenu(ApplicationMenu):

    usedfor = ISprint
    facet = 'specifications'
    links = ['assignments', 'declined', 'settopics', 'roadmap']

    def assignments(self):
        text = 'Assignments'
        summary = 'View the specification assignments'
        return Link('+assignments', text, summary, icon='info')

    def declined(self):
        text = 'Declined Topics'
        summary = 'Show topics that were not accepted for discussion'
        return Link('+specs?acceptance=declined', text, summary, icon='info')

    def settopics(self):
        text = 'Set Topics'
        summary = 'Approve or defer topics for discussion'
        return Link('+settopics', text, summary, icon='edit')

    def roadmap(self):
        text = 'Roadmap'
        summary = 'Suggest a sequence of implementation for these features'
        return Link('+roadmap', text, summary, icon='info')


class SprintSetNavigation(GetitemNavigation):

    usedfor = ISprintSet


class SprintSetContextMenu(ContextMenu):

    usedfor = ISprintSet
    links = ['new']

    def new(self):
        text = 'Register New Meeting'
        return Link('+new', text, icon='add')


class SprintView(LaunchpadView):

    __used_for__ = ISprint

    def initialize(self):
        self.notices = []

    def attendance(self):
        """establish if this user is attending"""
        if self.user is None:
            return None
        for subscription in self.context.subscriptions:
            if subscription.person.id == self.user.id:
                return subscription
        return None

    @cachedproperty
    def spec_links(self):
        """List all of the SprintSpecifications appropriate for this view."""
        filter = self.spec_filter
        return shortlist(self.context.specificationLinks(filter=filter))

    @cachedproperty
    def count(self):
        return len(self.spec_links)

    @cachedproperty
    def proposed_count(self):
        filter = [SpecificationFilter.PROPOSED]
        return self.context.specificationLinks(filter=filter).count()


class SprintAddView(SQLObjectAddView):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self._nextURL = '.'
        SQLObjectAddView.__init__(self, context, request)

    def create(self, owner, name, title, time_zone, time_starts, time_ends,
        summary=None, home_page=None):
        """Create a new Sprint."""
        # clean up name
        name = name.strip().lower()
        sprint = getUtility(ISprintSet).new(owner, name, title, 
            time_zone, time_starts, time_ends, summary=summary,
            home_page=home_page)
        self._nextURL = canonical_url(sprint)
        return sprint

    def nextURL(self):
        return self._nextURL


class SprintEditView(SQLObjectEditView):

    def changed(self):
        self.request.response.redirect(canonical_url(self.context))


class SprintTopicSetView(LaunchpadView):
    """Custom view class to process the results of this unusual page.

    It is unusual because we want to display multiple objects with
    checkboxes, then process the selected items, which is not the usual
    add/edit metaphor."""
    # XXX: SteveAlexander, 2006-03-06, this class and its
    #      associated templates are not tested.

    def initialize(self):
        self.status_message = None
        self.process_form()

    def speclinks(self):
        """Return the specification links with PROPOSED status for this
        sprint.
        """
        return self.context.specificationLinks(
            status=SprintSpecificationStatus.PROPOSED)

    def process_form(self):
        """Largely copied from webapp/generalform.py, without the
        schema processing bits because we are not rendering the form in the
        usual way. Instead, we are creating our own form in the page
        template and interpreting it here.
        """
        form = self.request.form

        if 'SUBMIT_CANCEL' in form:
            self.status_message = 'Cancelled'
            self.request.response.redirect(
                canonical_url(self.context)+'/+specs')
            return

        if 'SUBMIT_ACCEPT' not in form and 'SUBMIT_DECLINE' not in form:
            self.status_message = ''
            return

        if self.request.method == 'POST':
            if 'speclink' not in form:
                self.status_message = (
                    'Please select specifications to accept or decline.')
                return
            # determine if we are accepting or declining
            if 'SUBMIT_ACCEPT' in form:
                assert 'SUBMIT_DECLINE' not in form
                action = 'Accepted'
            else:
                assert 'SUBMIT_DECLINE' in form
                action = 'Declined'

        selected_specs = form['speclink']
        if isinstance(selected_specs, unicode):
            # only a single item was selected, but we want to deal with a
            # list for the general case, so convert it to a list
            selected_specs = [selected_specs]

        if action == 'Accepted':
            new_status = SprintSpecificationStatus.ACCEPTED
        else:
            new_status = SprintSpecificationStatus.DECLINED

        for sprintspec_id in selected_specs:
            sprintspec = self.context.getSpecificationLink(sprintspec_id)
            sprintspec.status = new_status

        flush_database_updates()

        # Status message like: "Accepted 27 specification(s)."
        self.status_message = '%s %d specification(s).' % (
            action, len(selected_specs))

        if self.speclinks().count() == 0:
            # they are all done, so redirect back to the spec listing page
            self.request.response.redirect(
                canonical_url(self.context)+'/+specs')

