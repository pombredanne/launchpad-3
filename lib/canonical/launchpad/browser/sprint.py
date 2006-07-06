# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Sprint views."""

__metaclass__ = type
__all__ = [
    'SprintFacets',
    'SprintNavigation',
    'SprintOverviewMenu',
    'SprintSpecificationsMenu',
    'SprintSetContextMenu',
    'SprintSetNavigation',
    'SprintView',
    'SprintAddView',
    'SprintEditView',
    'SprintTopicSetView',
    'SprintMeetingExportView',
    ]

import pytz

from zope.component import getUtility

from zope.app.form.interfaces import WidgetsError

from canonical.launchpad.interfaces import ILaunchBag, ISprint, ISprintSet

from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.browser.specificationtarget import (
    HasSpecificationsView)

from canonical.lp.dbschema import (
    SprintSpecificationStatus, SpecificationFilter, SpecificationStatus,
    SpecificationPriority)

from canonical.database.sqlbase import flush_database_updates

from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, GeneralFormView, GetitemNavigation,
    Navigation, ApplicationMenu, StandardLaunchpadFacets, LaunchpadView)

from canonical.launchpad.browser.specificationtarget import (
    HasSpecificationsView)
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


class SprintNavigation(Navigation):

    usedfor = ISprint

    def breadcrumb(self):
        return self.context.title


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

    def breadcrumb(self):
        return 'Meetings'


class SprintSetContextMenu(ContextMenu):

    usedfor = ISprintSet
    links = ['new']

    def new(self):
        text = 'Register New Meeting'
        return Link('+new', text, icon='add')


class SprintView(HasSpecificationsView, LaunchpadView):

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


class SprintAddView(GeneralFormView):

    def initialize(self):
        self.top_of_page_errors = []

    def validate(self, form_data):
        time_starts = form_data['time_starts']
        time_ends = form_data['time_ends']
        if time_starts >= time_ends:
            self.top_of_page_errors.append(
                "Sprint can't start after it ends")
            raise WidgetsError(self.top_of_page_errors)

    def process(self, name, title, time_zone, time_starts, time_ends,
        summary=None, home_page=None):
        """Create a new Sprint."""
        # Replace the timezone with the one entered by the user.
        time_starts = time_starts.replace(tzinfo=pytz.timezone(time_zone))
        time_ends = time_ends.replace(tzinfo=pytz.timezone(time_zone))
        sprint = getUtility(ISprintSet).new(self.user, name, title,
            time_zone, time_starts, time_ends, summary=summary,
            home_page=home_page)
        self._nextURL = canonical_url(sprint)


class SprintEditView(SQLObjectEditView):

    def changed(self):
        self.request.response.redirect(canonical_url(self.context))


class SprintTopicSetView(HasSpecificationsView, LaunchpadView):
    """Custom view class to process the results of this unusual page.

    It is unusual because we want to display multiple objects with
    checkboxes, then process the selected items, which is not the usual
    add/edit metaphor."""
    # XXX: SteveAlexander, 2006-03-06, this class and its
    #      associated templates are not tested.

    def initialize(self):
        self.status_message = None
        self.process_form()

    @cachedproperty
    def spec_filter(self):
        """Return the specification links with PROPOSED status for this
        sprint.
        """
        return [SpecificationFilter.PROPOSED]

    @cachedproperty
    def spec_links(self):
        filter = self.spec_filter
        return self.context.specificationLinks(filter=filter)

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
            action_fn = self.context.acceptSpecificationLinks
        else:
            action_fn = self.context.declineSpecificationLinks
        leftover = action_fn(selected_specs)

        # Status message like: "Accepted 27 specification(s)."
        self.status_message = '%s %d specification(s).' % (
            action, len(selected_specs))

        if leftover == 0:
            # they are all done, so redirect back to the spec listing page
            self.request.response.redirect(
                canonical_url(self.context)+'/+specs')


class SprintMeetingExportView(LaunchpadView):
    """View to provide information used the sprint meeting XML export view."""

    def initialize(self):
        self.attendees = []
        attendee_set = set()
        for attendance in self.context.attendances:
            self.attendees.append(dict(
                name=attendance.attendee.name,
                displayname=attendance.attendee.displayname,
                start=attendance.time_starts.strftime('%Y-%m-%dT%H:%M:%SZ'),
                end=attendance.time_ends.strftime('%Y-%m-%dT%H:%M:%SZ')))
            attendee_set.add(attendance.attendee)

        self.specifications = []
        for speclink in self.context.specificationLinks(
            filter=[SpecificationFilter.ACCEPTED]):
            spec = speclink.specification

            # skip sprints with no priority or less than low:
            if (spec.priority is None or
                spec.priority < SpecificationPriority.LOW):
                continue

            if spec.status not in [SpecificationStatus.BRAINDUMP,
                                   SpecificationStatus.DRAFT]:
                continue

            # get the list of attendees that will attend the sprint
            interested = set(sub.person for sub in spec.subscriptions)
            interested = interested.intersection(attendee_set)
            if spec.assignee is not None:
                interested.add(spec.assignee)
            if spec.drafter is not None:
                interested.add(spec.drafter)

            self.specifications.append(dict(
                spec=spec,
                interested=interested))

    def render(self):
        self.request.response.setHeader('content-type',
                                        'application/xml;charset=utf-8')
        body = LaunchpadView.render(self)
        return body.encode('utf-8')
