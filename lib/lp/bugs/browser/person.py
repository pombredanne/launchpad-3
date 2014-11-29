# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""IPerson browser views related to bugs."""

__metaclass__ = type

__all__ = [
    'PersonBugsMenu',
    'PersonCommentedBugTaskSearchListingView',
    'PersonAssignedBugTaskSearchListingView',
    'PersonRelatedBugTaskSearchListingView',
    'PersonReportedBugTaskSearchListingView',
    'PersonStructuralSubscriptionsView',
    'PersonSubscribedBugTaskSearchListingView',
    'PersonSubscriptionsView',
    ]

import copy
from operator import itemgetter
import urllib

from zope.component import getUtility

from lp.bugs.browser.buglisting import BugTaskSearchListingView
from lp.bugs.interfaces.bugtask import (
    BugTaskStatus,
    IBugTaskSet,
    UNRESOLVED_BUGTASK_STATUSES,
    )
from lp.registry.interfaces.person import IPerson
from lp.registry.model.milestone import (
    Milestone,
    milestone_sort_key,
    )
from lp.services.database.bulk import load_related
from lp.services.feeds.browser import FeedsMixin
from lp.services.propertycache import cachedproperty
from lp.services.webapp.batching import BatchNavigator
from lp.services.webapp.menu import (
    Link,
    NavigationMenu,
    )
from lp.services.webapp.publisher import (
    canonical_url,
    LaunchpadView,
    )


def get_package_search_url(dsp_bugs_url, extra_params=None):
    """Construct a default search URL for a distributionsourcepackage.

    Optional filter parameters can be specified as a dict with the
    extra_params argument.
    """
    params = {
        "search": "Search",
        "field.status": [
            status.title for status in UNRESOLVED_BUGTASK_STATUSES]}
    if extra_params is not None:
        # We must UTF-8 encode searchtext to play nicely with
        # urllib.urlencode, because it may contain non-ASCII characters.
        if 'field.searchtext' in extra_params:
            extra_params["field.searchtext"] = (
                extra_params["field.searchtext"].encode("utf8"))
        params.update(extra_params)
    return '%s?%s' % (
        dsp_bugs_url, urllib.urlencode(sorted(params.items()), doseq=True))


class PersonBugsMenu(NavigationMenu):

    usedfor = IPerson
    facet = 'bugs'
    links = ['affectingbugs', 'assignedbugs', 'commentedbugs', 'reportedbugs',
             'subscribedbugs', 'relatedbugs', 'softwarebugs']

    def relatedbugs(self):
        text = 'All related bugs'
        summary = ('All bug reports which %s reported, is assigned to, '
                   'or is subscribed to.' % self.context.displayname)
        return Link('', text, site='bugs', summary=summary)

    def assignedbugs(self):
        text = 'Assigned bugs'
        summary = 'Bugs assigned to %s.' % self.context.displayname
        return Link('+assignedbugs', text, site='bugs', summary=summary)

    def softwarebugs(self):
        text = 'Subscribed packages'
        summary = (
            'A summary report for packages where %s is a subscriber.'
            % self.context.displayname)
        return Link('+packagebugs', text, site='bugs', summary=summary)

    def reportedbugs(self):
        text = 'Reported bugs'
        summary = 'Bugs reported by %s.' % self.context.displayname
        enabled = not self.context.is_team
        return Link(
            '+reportedbugs', text, site='bugs', summary=summary,
            enabled=enabled)

    def subscribedbugs(self):
        text = 'Subscribed bugs'
        summary = ('Bug reports %s is subscribed to.'
                   % self.context.displayname)
        return Link('+subscribedbugs', text, site='bugs', summary=summary)

    def commentedbugs(self):
        text = 'Commented bugs'
        summary = ('Bug reports on which %s has commented.'
                   % self.context.displayname)
        enabled = not self.context.is_team
        return Link(
            '+commentedbugs', text, site='bugs', summary=summary,
            enabled=enabled)

    def affectingbugs(self):
        text = 'Affecting bugs'
        summary = ('Bugs affecting %s.' % self.context.displayname)
        enabled = not self.context.is_team
        return Link(
            '+affectingbugs', text, site='bugs', summary=summary,
            enabled=enabled)


class RelevantMilestonesMixin:
    """Mixin to narrow the milestone list to only relevant milestones."""

    def getMilestoneWidgetValues(self):
        """Return data used to render the milestone checkboxes."""
        tasks = self.searchUnbatched()
        milestones = sorted(
            load_related(Milestone, tasks, ['milestoneID']),
            key=milestone_sort_key, reverse=True)
        return [
            dict(title=milestone.title, value=milestone.id, checked=False)
            for milestone in milestones]


class BugSubscriberPackageBugsOverView(LaunchpadView):

    label = 'Subscribed packages'

    @cachedproperty
    def total_bug_counts(self):
        """Return the totals of each type of package bug count as a dict."""
        totals = {
            'open_bugs_count': 0,
            'critical_bugs_count': 0,
            'high_bugs_count': 0,
            'unassigned_bugs_count': 0,
            'inprogress_bugs_count': 0,
            }

        for package_counts in self.package_bug_counts:
            for key in totals.keys():
                totals[key] += int(package_counts[key])

        return totals

    @cachedproperty
    def package_bug_counts(self):
        """Return a list of dicts used for rendering package bug counts."""
        L = []
        package_counts = getUtility(IBugTaskSet).getBugCountsForPackages(
            self.user, self.context.getBugSubscriberPackages())
        for package_counts in package_counts:
            url = canonical_url(package_counts['package'], rootsite='bugs')
            L.append({
                'package_name': package_counts['package'].displayname,
                'package_search_url': get_package_search_url(url),
                'open_bugs_count': package_counts['open'],
                'open_bugs_url': get_package_search_url(url),
                'critical_bugs_count': package_counts['open_critical'],
                'critical_bugs_url': get_package_search_url(
                    url, {'field.importance': 'Critical'}),
                'high_bugs_count': package_counts['open_high'],
                'high_bugs_url': get_package_search_url(
                    url, {'field.importance': 'High'}),
                'unassigned_bugs_count': package_counts['open_unassigned'],
                'unassigned_bugs_url': get_package_search_url(
                    url, {'assignee_option': 'none'}),
                'inprogress_bugs_count': package_counts['open_inprogress'],
                'inprogress_bugs_url': get_package_search_url(
                    url, {'field.status': 'In Progress'}),
            })
        return sorted(L, key=itemgetter('package_name'))


class FilteredSearchListingViewMixin(RelevantMilestonesMixin,
                                     BugTaskSearchListingView):
    columns_to_show = ["id", "summary", "bugtargetdisplayname",
                       "importance", "status"]

    @property
    def page_title(self):
        return self.label

    def searchUnbatched(self, searchtext=None, context=None,
                        extra_params=None):
        context = context or self.context
        extra_params = extra_params or {}
        extra_params.update(self.getExtraParams(context))
        return super(FilteredSearchListingViewMixin, self).searchUnbatched(
            searchtext, context, extra_params)


class PersonAssignedBugTaskSearchListingView(FilteredSearchListingViewMixin):
    """All bugs assigned to someone."""

    label = 'Assigned bugs'
    view_name = '+assignedbugs'

    def getExtraParams(self, context):
        return {'assignee': context}

    def shouldShowAssigneeWidget(self):
        """Should the assignee widget be shown on the advanced search page?"""
        return False

    def shouldShowTeamPortlet(self):
        """Should the team assigned bugs portlet be shown?"""
        return True


class PersonCommentedBugTaskSearchListingView(FilteredSearchListingViewMixin):
    """All bugs commented on by a Person."""

    label = 'Commented bugs'
    view_name = '+commentedbugs'

    def getExtraParams(self, context):
        return {'bug_commenter': context}


class PersonAffectingBugTaskSearchListingView(FilteredSearchListingViewMixin):
    """All bugs affecting someone."""

    label = 'Bugs affecting'
    view_name = '+affectingbugs'

    def getExtraParams(self, context):
        return {'affected_user': context}

    def shouldShowAssigneeWidget(self):
        """Should the assignee widget be shown on the advanced search page?"""
        return False

    def shouldShowTeamPortlet(self):
        """Should the team assigned bugs portlet be shown?"""
        return True


class PersonRelatedBugTaskSearchListingView(FilteredSearchListingViewMixin,
                                            FeedsMixin):
    """All bugs related to someone."""

    label = 'Related bugs'
    view_name = '+bugs'

    def searchUnbatched(self, searchtext=None, context=None,
                        extra_params=None):
        """Return the open bugs related to a person.

        :param extra_params: A dict that provides search params added to
            the search criteria taken from the request. Params in
            `extra_params` take precedence over request params.
        """
        if context is None:
            context = self.context

        params = self.buildSearchParams(extra_params=extra_params)
        subscriber_params = copy.copy(params)
        subscriber_params.subscriber = context
        assignee_params = copy.copy(params)
        owner_params = copy.copy(params)
        commenter_params = copy.copy(params)

        # Only override the assignee, commenter and owner if they were not
        # specified by the user.
        if assignee_params.assignee is None:
            assignee_params.assignee = context
        if owner_params.owner is None:
            # Specify both owner and bug_reporter to try to prevent the same
            # bug (but different tasks) being displayed.
            owner_params.owner = context
            owner_params.bug_reporter = context
        if commenter_params.bug_commenter is None:
            commenter_params.bug_commenter = context

        return context.searchTasks(
            assignee_params, subscriber_params, owner_params, commenter_params)


class PersonReportedBugTaskSearchListingView(FilteredSearchListingViewMixin):
    """All bugs reported by someone."""

    label = 'Reported bugs'
    view_name = '+reportedbugs'

    def getExtraParams(self, context):
        # Specify both owner and bug_reporter to try to prevent the same
        # bug (but different tasks) being displayed.
        return {'owner': context, 'bug_reporter': context}

    def shouldShowReporterWidget(self):
        """Should the reporter widget be shown on the advanced search page?"""
        return False


class PersonSubscribedBugTaskSearchListingView(FilteredSearchListingViewMixin):
    """All bugs someone is subscribed to."""

    label = 'Subscribed bugs'
    view_name = '+subscribedbugs'

    def getExtraParams(self, context):
        return {'subscriber': context}

    def shouldShowTeamPortlet(self):
        """Should the team subscribed bugs portlet be shown?"""
        return True


class PersonSubscriptionsView(LaunchpadView):
    """All the subscriptions for a person."""

    page_title = 'Subscriptions'

    def subscribedBugTasks(self):
        """
        Return a BatchNavigator for distinct bug tasks to which the person is
        subscribed.
        """
        bug_tasks = self.context.searchTasks(None, user=self.user,
            order_by='-date_last_updated',
            status=(BugTaskStatus.NEW,
                    BugTaskStatus.INCOMPLETE,
                    BugTaskStatus.CONFIRMED,
                    BugTaskStatus.TRIAGED,
                    BugTaskStatus.INPROGRESS,
                    BugTaskStatus.FIXCOMMITTED,
                    BugTaskStatus.INVALID),
            bug_subscriber=self.context)

        sub_bug_tasks = []
        sub_bugs = set()

        # XXX: GavinPanella 2010-10-08 bug=656904: This materializes the
        # entire result set. It would probably be more efficient implemented
        # with a pre_iter_hook on a DecoratedResultSet.
        for task in bug_tasks:
            # We order the bugtasks by date_last_updated but we always display
            # the default task for the bug. This is to avoid ordering issues
            # in tests and also prevents user confusion (because nothing is
            # more confusing than your subscription targets changing seemingly
            # at random).
            if task.bug not in sub_bugs:
                # XXX: GavinPanella 2010-10-08 bug=656904: default_bugtask
                # causes a query to be executed. It would be more efficient to
                # get the default bugtask in bulk, in a pre_iter_hook on a
                # DecoratedResultSet perhaps.
                sub_bug_tasks.append(task.bug.default_bugtask)
                sub_bugs.add(task.bug)

        return BatchNavigator(sub_bug_tasks, self.request)

    def canUnsubscribeFromBugTasks(self):
        """Can the current user unsubscribe from the bug tasks shown?"""
        return (self.user is not None and
                self.user.inTeam(self.context))

    @property
    def label(self):
        """The header for the subscriptions page."""
        return "Subscriptions for %s" % self.context.displayname


class PersonStructuralSubscriptionsView(LaunchpadView):
    """All the structural subscriptions for a person."""

    page_title = 'Structural subscriptions'

    def canUnsubscribeFromBugTasks(self):
        """Can the current user modify subscriptions for the context?"""
        return (self.user is not None and
                self.user.inTeam(self.context))

    @property
    def label(self):
        """The header for the structural subscriptions page."""
        return "Structural subscriptions for %s" % self.context.displayname
