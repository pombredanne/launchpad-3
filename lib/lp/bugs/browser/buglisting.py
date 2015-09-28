# Copyright 2009-2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""IBugTask-related browser views."""

__metaclass__ = type

__all__ = [
    'BugNominationsView',
    'BugListingBatchNavigator',
    'BugListingPortletInfoView',
    'BugListingPortletStatsView',
    'BugsBugTaskSearchListingView',
    'BugTargetView',
    'BugTaskExpirableListingView',
    'BugTaskListingItem',
    'BugTaskListingView',
    'BugTaskSearchListingView',
    'get_buglisting_search_filter_url',
    'get_sortorder_from_request',
    'TextualBugTaskSearchListingView',
    ]

import cgi
import os.path
import urllib
import urlparse

from lazr.delegates import delegate_to
from lazr.restful.interfaces import IJSONRequestCache
from lazr.uri import URI
import pystache
from simplejson import dumps
from simplejson.encoder import JSONEncoderForHTML
from z3c.pt.pagetemplate import ViewPageTemplateFile
from zope.authentication.interfaces import IUnauthenticatedPrincipal
from zope.component import (
    getAdapter,
    getUtility,
    queryMultiAdapter,
    )
from zope.formlib.interfaces import InputErrors
from zope.formlib.itemswidgets import RadioWidget
from zope.interface import (
    implementer,
    Interface,
    )
from zope.schema.vocabulary import getVocabularyRegistry
from zope.security.proxy import isinstance as zope_isinstance
from zope.traversing.interfaces import IPathAdapter

from lp import _
from lp.answers.interfaces.questiontarget import IQuestionTarget
from lp.app.browser.launchpad import iter_view_registrations
from lp.app.browser.launchpadform import (
    custom_widget,
    LaunchpadFormView,
    )
from lp.app.browser.tales import (
    BugTrackerFormatterAPI,
    DateTimeFormatterAPI,
    PersonFormatterAPI,
    )
from lp.app.enums import (
    InformationType,
    ServiceUsage,
    )
from lp.app.errors import (
    NotFoundError,
    UnexpectedFormData,
    )
from lp.app.interfaces.launchpad import (
    IHeadingContext,
    IPrivacy,
    IServiceUsage,
    )
from lp.app.vocabularies import InformationTypeVocabulary
from lp.app.widgets.itemswidgets import LabeledMultiCheckBoxWidget
from lp.app.widgets.popup import PersonPickerWidget
from lp.app.widgets.project import ProjectScopeWidget
from lp.bugs.browser.structuralsubscription import (
    expose_structural_subscription_data_to_js,
    )
from lp.bugs.browser.widgets.bug import BugTagsWidget
from lp.bugs.browser.widgets.bugtask import NewLineToSpacesWidget
from lp.bugs.interfaces.bug import IBugSet
from lp.bugs.interfaces.bugattachment import BugAttachmentType
from lp.bugs.interfaces.bugtask import (
    BugTaskImportance,
    BugTaskStatus,
    BugTaskStatusSearch,
    BugTaskStatusSearchDisplay,
    IBugTask,
    IBugTaskSet,
    UNRESOLVED_BUGTASK_STATUSES,
    )
from lp.bugs.interfaces.bugtasksearch import (
    BugBlueprintSearch,
    BugBranchSearch,
    BugTagsSearchCombinator,
    BugTaskSearchParams,
    DEFAULT_SEARCH_BUGTASK_STATUSES_FOR_DISPLAY,
    IBugTaskSearch,
    IFrontPageBugTaskSearch,
    IPersonBugTaskSearch,
    IUpstreamProductBugTaskSearch,
    )
from lp.bugs.interfaces.bugtracker import IHasExternalBugTracker
from lp.bugs.interfaces.malone import IMaloneApplication
from lp.bugs.model.bugtasksearch import orderby_expression
from lp.layers import FeedsLayer
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.projectgroup import IProjectGroup
from lp.registry.interfaces.sourcepackage import ISourcePackage
from lp.services.config import config
from lp.services.feeds.browser import (
    BugTargetLatestBugsFeedLink,
    FeedsMixin,
    )
from lp.services.helpers import shortlist
from lp.services.propertycache import cachedproperty
from lp.services.searchbuilder import (
    all,
    any,
    NULL,
    )
from lp.services.utils import obfuscate_structure
from lp.services.webapp import (
    canonical_url,
    enabled_with_permission,
    LaunchpadView,
    Link,
    NavigationMenu,
    )
from lp.services.webapp.authorization import check_permission
from lp.services.webapp.batching import (
    get_batch_properties_for_json_cache,
    TableBatchNavigator,
    )
from lp.services.webapp.interfaces import ILaunchBag


vocabulary_registry = getVocabularyRegistry()

DISPLAY_BUG_STATUS_FOR_PATCHES = {
    BugTaskStatus.NEW: True,
    BugTaskStatus.INCOMPLETE: True,
    BugTaskStatus.INVALID: False,
    BugTaskStatus.WONTFIX: False,
    BugTaskStatus.CONFIRMED: True,
    BugTaskStatus.TRIAGED: True,
    BugTaskStatus.INPROGRESS: True,
    BugTaskStatus.FIXCOMMITTED: True,
    BugTaskStatus.FIXRELEASED: False,
    BugTaskStatus.UNKNOWN: False,
    BugTaskStatus.EXPIRED: False,
    BugTaskStatusSearch.INCOMPLETE_WITHOUT_RESPONSE: True,
    BugTaskStatusSearch.INCOMPLETE_WITH_RESPONSE: True,
    }


def get_sortorder_from_request(request):
    """Get the sortorder from the request.

    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> get_sortorder_from_request(LaunchpadTestRequest(form={}))
    ['-importance']
    >>> get_sortorder_from_request(
    ...     LaunchpadTestRequest(form={'orderby': '-status'}))
    ['-status']
    >>> get_sortorder_from_request(LaunchpadTestRequest(
    ...     form={'orderby': 'status,-severity,importance'}))
    ['status', 'importance']
    >>> get_sortorder_from_request(
    ...     LaunchpadTestRequest(form={'orderby': 'priority,-severity'}))
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


def get_default_search_params(user):
    """Return a BugTaskSearchParams instance with default values.

    By default, a search includes any bug that is unresolved and not a
    duplicate of another bug.

    If this search will be used to display a list of bugs to the user
    it may be a good idea to set the orderby attribute using
    get_sortorder_from_request():

      params = get_default_search_params(user)
      params.orderby = get_sortorder_from_request(request)

    """
    return BugTaskSearchParams(
        user=user, status=any(*UNRESOLVED_BUGTASK_STATUSES), omit_dupes=True)


OLD_BUGTASK_STATUS_MAP = {
    'Unconfirmed': 'New',
    'Needs Info': 'Incomplete',
    'Rejected': 'Invalid',
    }


def rewrite_old_bugtask_status_query_string(query_string):
    """Return a query string with old status names replaced with new.

    If an old status string has been used in the query, construct a
    corrected query string for the search, else return the original
    query string.
    """
    query_elements = cgi.parse_qsl(
        query_string, keep_blank_values=True, strict_parsing=False)
    query_elements_mapped = []

    for name, value in query_elements:
        if name == 'field.status:list':
            value = OLD_BUGTASK_STATUS_MAP.get(value, value)
        query_elements_mapped.append((name, value))

    if query_elements == query_elements_mapped:
        return query_string
    else:
        return urllib.urlencode(query_elements_mapped, doseq=True)


def target_has_expirable_bugs_listing(target):
    """Return True or False if the target has the expirable-bugs listing.

    The target must be a Distribution, DistroSeries, Product, or
    ProductSeries, and the pillar must have enabled bug expiration.
    """
    if IDistribution.providedBy(target) or IProduct.providedBy(target):
        return target.enable_bug_expiration
    elif IProductSeries.providedBy(target):
        return target.product.enable_bug_expiration
    elif IDistroSeries.providedBy(target):
        return target.distribution.enable_bug_expiration
    else:
        # This context is not a supported bugtarget.
        return False


class BugTaskListingView(LaunchpadView):
    """A view designed for displaying bug tasks in lists."""
    # Note that this right now is only used in tests and to render
    # status in the CVEReportView. It may be a candidate for refactoring
    # or removal.
    @property
    def status(self):
        """Return an HTML representation of the bugtask status.

        The assignee is included.
        """
        bugtask = self.context
        assignee = bugtask.assignee
        status = bugtask.status
        status_title = status.title.capitalize()

        if not assignee:
            return status_title + ' (unassigned)'
        assignee_html = PersonFormatterAPI(assignee).link('+assignedbugs')

        if status in (BugTaskStatus.INVALID,
                      BugTaskStatus.FIXCOMMITTED):
            return '%s by %s' % (status_title, assignee_html)
        else:
            return '%s, assigned to %s' % (status_title, assignee_html)

    @property
    def status_elsewhere(self):
        """Return human-readable representation of the status of this bug
        in other contexts for which it's reported.
        """
        bugtask = self.context
        related_tasks = bugtask.related_tasks
        if not related_tasks:
            return "not filed elsewhere"

        fixes_found = len(
            [task for task in related_tasks
             if task.status in (BugTaskStatus.FIXCOMMITTED,
                                BugTaskStatus.FIXRELEASED)])
        if fixes_found:
            return "fixed in %d of %d places" % (
                fixes_found, len(bugtask.bug.bugtasks))
        elif len(related_tasks) == 1:
            return "filed in 1 other place"
        else:
            return "filed in %d other places" % len(related_tasks)

    def render(self):
        """Make rendering this template-less view not crash."""
        return u""


class BugsInfoMixin:
    """Contains properties giving URLs to bug information."""

    @property
    def bugs_fixed_elsewhere_url(self):
        """A URL to a list of bugs fixed elsewhere."""
        return "%s?field.status_upstream=resolved_upstream" % (
            canonical_url(self.context, view_name='+bugs'))

    @property
    def open_cve_bugs_url(self):
        """A URL to a list of open bugs linked to CVEs."""
        return "%s?field.has_cve=on" % (
            canonical_url(self.context, view_name='+bugs'))

    @property
    def open_cve_bugs_has_report(self):
        """Whether or not the context has a CVE report page."""
        return queryMultiAdapter(
            (self.context, self.request), name='+cve') is not None

    @property
    def pending_bugwatches_url(self):
        """A URL to a list of bugs that need a bugwatch.

        None is returned if the context is not an upstream product.
        """
        if not IProduct.providedBy(self.context):
            return None
        if self.context.bug_tracking_usage == ServiceUsage.LAUNCHPAD:
            return None
        return "%s?field.status_upstream=pending_bugwatch" % (
            canonical_url(self.context, view_name='+bugs'))

    @property
    def expirable_bugs_url(self):
        """A URL to a list of bugs that can expire, or None.

        If the bugtarget is not a supported implementation, or its pillar
        does not have enable_bug_expiration set to True, None is returned.
        The bugtarget may be an `IDistribution`, `IDistroSeries`, `IProduct`,
        or `IProductSeries`.
        """
        if target_has_expirable_bugs_listing(self.context):
            return canonical_url(self.context, view_name='+expirable-bugs')
        else:
            return None

    @property
    def new_bugs_url(self):
        """A URL to a page of new bugs."""
        return get_buglisting_search_filter_url(
            status=BugTaskStatus.NEW.title)

    @property
    def inprogress_bugs_url(self):
        """A URL to a page of inprogress bugs."""
        return get_buglisting_search_filter_url(
            status=BugTaskStatus.INPROGRESS.title)

    @property
    def open_bugs_url(self):
        """A URL to a list of open bugs."""
        return canonical_url(self.context, view_name='+bugs')

    @property
    def critical_bugs_url(self):
        """A URL to a list of critical bugs."""
        return get_buglisting_search_filter_url(
            status=[status.title for status in UNRESOLVED_BUGTASK_STATUSES],
            importance=BugTaskImportance.CRITICAL.title)

    @property
    def high_bugs_url(self):
        """A URL to a list of high priority bugs."""
        return get_buglisting_search_filter_url(
            status=[status.title for status in UNRESOLVED_BUGTASK_STATUSES],
            importance=BugTaskImportance.HIGH.title)

    @property
    def my_bugs_url(self):
        """A URL to a list of bugs assigned to the user, or None."""
        if self.user is None:
            return None
        else:
            return get_buglisting_search_filter_url(assignee=self.user.name)

    @property
    def my_affecting_bugs_url(self):
        """A URL to a list of bugs affecting the current user, or None if
        there is no current user.
        """
        if self.user is None:
            return None
        return get_buglisting_search_filter_url(
            affecting_me=True,
            orderby='-date_last_updated')

    @property
    def my_reported_bugs_url(self):
        """A URL to a list of bugs reported by the user, or None."""
        if self.user is None:
            return None
        return get_buglisting_search_filter_url(bug_reporter=self.user.name)


class BugsStatsMixin(BugsInfoMixin):
    """Contains properties giving bug stats.

    These can be expensive to obtain.
    """

    @cachedproperty
    def _bug_stats(self):
        # Circular fail.
        from lp.bugs.model.bugsummary import BugSummary
        bug_task_set = getUtility(IBugTaskSet)
        groups = (
            BugSummary.status, BugSummary.importance, BugSummary.has_patch)
        counts = bug_task_set.countBugs(self.user, [self.context], groups)
        # Sum the split out aggregates.
        new = 0
        open = 0
        inprogress = 0
        critical = 0
        high = 0
        with_patch = 0
        for metadata, count in counts.items():
            status = metadata[0]
            importance = metadata[1]
            has_patch = metadata[2]
            if status == BugTaskStatus.NEW:
                new += count
            elif status == BugTaskStatus.INPROGRESS:
                inprogress += count
            if importance == BugTaskImportance.CRITICAL:
                critical += count
            elif importance == BugTaskImportance.HIGH:
                high += count
            if has_patch and DISPLAY_BUG_STATUS_FOR_PATCHES[status]:
                with_patch += count
            open += count
        result = dict(
            new=new, open=open, inprogress=inprogress, high=high,
            critical=critical, with_patch=with_patch)
        return result

    @property
    def open_cve_bugs_count(self):
        """A count of open bugs linked to CVEs."""
        params = get_default_search_params(self.user)
        params.has_cve = True
        return self.context.searchTasks(params).count()

    @property
    def pending_bugwatches_count(self):
        """A count of bugs that need a bugwatch.

        None is returned if the context is not an upstream product.
        """
        if not IProduct.providedBy(self.context):
            return None
        if self.context.bug_tracking_usage == ServiceUsage.LAUNCHPAD:
            return None
        params = get_default_search_params(self.user)
        params.pending_bugwatch_elsewhere = True
        return self.context.searchTasks(params).count()

    @property
    def expirable_bugs_count(self):
        """A count of bugs that can expire, or None.

        If the bugtarget is not a supported implementation, or its pillar
        does not have enable_bug_expiration set to True, None is returned.
        The bugtarget may be an `IDistribution`, `IDistroSeries`, `IProduct`,
        or `IProductSeries`.
        """
        if target_has_expirable_bugs_listing(self.context):
            return getUtility(IBugTaskSet).findExpirableBugTasks(
                0, user=self.user, target=self.context).count()
        else:
            return None

    @property
    def new_bugs_count(self):
        """A count of new bugs."""
        return self._bug_stats['new']

    @property
    def open_bugs_count(self):
        """A count of open bugs."""
        return self._bug_stats['open']

    @property
    def inprogress_bugs_count(self):
        """A count of in-progress bugs."""
        return self._bug_stats['inprogress']

    @property
    def critical_bugs_count(self):
        """A count of critical bugs."""
        return self._bug_stats['critical']

    @property
    def high_bugs_count(self):
        """A count of high priority bugs."""
        return self._bug_stats['high']

    @property
    def my_bugs_count(self):
        """A count of bugs assigned to the user, or None."""
        if self.user is None:
            return None
        else:
            params = get_default_search_params(self.user)
            params.assignee = self.user
            return self.context.searchTasks(params).count()

    @property
    def my_reported_bugs_count(self):
        """A count of bugs reported by the user, or None."""
        if self.user is None:
            return None
        params = get_default_search_params(self.user)
        params.bug_reporter = self.user
        return self.context.searchTasks(params).count()

    @property
    def my_affecting_bugs_count(self):
        """A count of bugs affecting the user, or None."""
        if self.user is None:
            return None
        params = get_default_search_params(self.user)
        params.affects_me = True
        return self.context.searchTasks(params).count()

    @property
    def bugs_with_patches_count(self):
        """A count of unresolved bugs with patches."""
        return self._bug_stats['with_patch']


class BugListingPortletInfoView(LaunchpadView, BugsInfoMixin):
    """Portlet containing available bug listings without stats."""


class BugListingPortletStatsView(LaunchpadView, BugsStatsMixin):
    """Portlet containing available bug listings with stats."""


def get_buglisting_search_filter_url(
        assignee=None, importance=None, status=None, status_upstream=None,
        has_patches=None, bug_reporter=None,
        affecting_me=None,
        orderby=None):
    """Return the given URL with the search parameters specified."""
    search_params = []

    if assignee is not None:
        search_params.append(('field.assignee', assignee))
    if importance is not None:
        search_params.append(('field.importance', importance))
    if status is not None:
        search_params.append(('field.status', status))
    if status_upstream is not None:
        search_params.append(('field.status_upstream', status_upstream))
    if has_patches is not None:
        search_params.append(('field.has_patch', 'on'))
    if bug_reporter is not None:
        search_params.append(('field.bug_reporter', bug_reporter))
    if affecting_me is not None:
        search_params.append(('field.affects_me', 'on'))
    if orderby is not None:
        search_params.append(('orderby', orderby))

    query_string = urllib.urlencode(search_params, doseq=True)

    search_filter_url = "+bugs?search=Search"
    if query_string != '':
        search_filter_url += "&" + query_string

    return search_filter_url


@delegate_to(IBugTask, context='bugtask')
class BugTaskListingItem:
    """A decorated bug task.

    Some attributes that we want to display are too convoluted or expensive
    to get on the fly for each bug task in the listing.  These items are
    prefetched by the view and decorate the bug task.
    """

    def __init__(self, bugtask, has_bug_branch,
                 has_specification, has_patch, tags,
                 people, request=None, target_context=None):
        self.bugtask = bugtask
        self.review_action_widget = None
        self.has_bug_branch = has_bug_branch
        self.has_specification = has_specification
        self.has_patch = has_patch
        self.tags = tags
        self.people = people
        self.request = request
        self.target_context = target_context

    @property
    def last_significant_change_date(self):
        """The date of the last significant change."""
        return (self.bugtask.date_closed or self.bugtask.date_fix_committed or
                self.bugtask.date_inprogress or self.bugtask.date_left_new or
                self.bugtask.datecreated)

    @property
    def bug_heat_html(self):
        """Returns the bug heat flames HTML."""
        return (
            '<span class="sprite flame">%d</span>'
            % self.bugtask.bug.heat)

    @property
    def model(self):
        """Provide flattened data about bugtask for simple templaters."""
        age = DateTimeFormatterAPI(self.bug.datecreated).durationsince()
        age += ' old'
        date_last_updated = self.bug.date_last_message
        if (date_last_updated is None or
            self.bug.date_last_updated > date_last_updated):
            date_last_updated = self.bug.date_last_updated
        last_updated_formatter = DateTimeFormatterAPI(date_last_updated)
        last_updated = last_updated_formatter.displaydate()
        badges = getAdapter(self, IPathAdapter, 'image').badges()
        target_image = getAdapter(self.target, IPathAdapter, 'image')
        if self.bugtask.milestone is not None:
            milestone_name = self.bugtask.milestone.displayname
        else:
            milestone_name = None
        assignee = None
        if self.assigneeID is not None:
            assignee = self.people[self.assigneeID].displayname
        reporter = self.people[self.bug.ownerID]

        # the case that there is no target context (e.g. viewing bug that
        # are related to a user account) is intercepted
        if self.target_context is None:
            base_tag_url = "%s/?field.tag=" % canonical_url(
                self.bugtask.target,
                view_name="+bugs")
        else:
            base_tag_url = "%s/?field.tag=" % canonical_url(
                self.target_context,
                view_name="+bugs")

        flattened = {
            'age': age,
            'assignee': assignee,
            'bug_url': canonical_url(self.bugtask),
            'bugtarget': self.bugtargetdisplayname,
            'bugtarget_css': target_image.sprite_css(),
            'bug_heat_html': self.bug_heat_html,
            'badges': badges,
            'id': self.bug.id,
            'importance': self.importance.title,
            'importance_class': 'importance' + self.importance.name,
            'information_type': self.bug.information_type.title,
            'last_updated': last_updated,
            'milestone_name': milestone_name,
            'reporter': reporter.displayname,
            'status': self.status.title,
            'status_class': 'status' + self.status.name,
            'tags': [{'url': base_tag_url + urllib.quote(tag), 'tag': tag}
                for tag in self.tags],
            'title': self.bug.title,
            }

        # This is a total hack, but pystache will run both truth/false values
        # for an empty list for some reason, and it "works" if it's just a
        # flag like this. We need this value for the mustache template to be
        # able to tell that there are no tags without looking at the list.
        flattened['has_tags'] = True if len(flattened['tags']) else False
        return flattened


class BugListingBatchNavigator(TableBatchNavigator):
    """A specialised batch navigator to load smartly extra bug information."""

    def __init__(self, tasks, request, columns_to_show, size,
                 target_context=None):
        self.request = request
        self.target_context = target_context
        self.user = getUtility(ILaunchBag).user
        self.field_visibility_defaults = {
            'show_datecreated': False,
            'show_assignee': False,
            'show_targetname': True,
            'show_heat': True,
            'show_id': True,
            'show_importance': True,
            'show_information_type': False,
            'show_date_last_updated': False,
            'show_milestone_name': False,
            'show_reporter': False,
            'show_status': True,
            'show_tag': False,
        }
        self.field_visibility = None
        self._setFieldVisibility()
        TableBatchNavigator.__init__(
            self, tasks, request, columns_to_show=columns_to_show, size=size)

    @cachedproperty
    def bug_badge_properties(self):
        return getUtility(IBugTaskSet).getBugTaskBadgeProperties(
            self.currentBatch())

    @cachedproperty
    def tags_for_batch(self):
        """Return a dict matching bugtask to it's tags."""
        return getUtility(IBugTaskSet).getBugTaskTags(self.currentBatch())

    @cachedproperty
    def bugtask_people(self):
        """Return mapping of people related to this bugtask set."""
        return getUtility(IBugTaskSet).getBugTaskPeople(self.currentBatch())

    def getCookieName(self):
        """Return the cookie name used in bug listings js code."""
        cookie_name_template = '%s-buglist-fields'
        cookie_name = ''
        if self.user is not None:
            cookie_name = cookie_name_template % self.user.name
        else:
            cookie_name = cookie_name_template % 'anon'
        return cookie_name

    def _setFieldVisibility(self):
        """Set field_visibility for the page load.

        If a cookie of the form $USER-buglist-fields is found,
        we set field_visibility from this cookie; otherwise,
        field_visibility will match the defaults.
        """
        cookie_name = self.getCookieName()
        cookie = self.request.cookies.get(cookie_name)
        self.field_visibility = dict(self.field_visibility_defaults)
        # "cookie" looks like a URL query string, so we split
        # on '&' to get items, and then split on '=' to get
        # field/value pairs.
        if cookie is None:
            return
        for field, value in urlparse.parse_qsl(cookie):
            # Skip unsupported fields (from old cookies).
            if field not in self.field_visibility:
                continue
            # We only record True or False for field values.
            self.field_visibility[field] = (value == 'true')

    def _getListingItem(self, bugtask):
        """Return a decorated bugtask for the bug listing."""
        badge_property = self.bug_badge_properties[bugtask]
        tags = self.tags_for_batch.get(bugtask.id, ())
        if (IMaloneApplication.providedBy(self.target_context) or
            IPerson.providedBy(self.target_context)):
            # XXX Tom Berger bug=529846
            # When we have a specific interface for things that have bug heat
            # it would be better to use that for the check here instead.
            target_context = None
        else:
            target_context = self.target_context
        return BugTaskListingItem(
            bugtask,
            badge_property['has_branch'],
            badge_property['has_specification'],
            badge_property['has_patch'],
            tags,
            self.bugtask_people,
            request=self.request,
            target_context=target_context)

    def getBugListingItems(self):
        """Return a decorated list of visible bug tasks."""
        return [self._getListingItem(bugtask) for bugtask in self.batch]

    @cachedproperty
    def mustache_template(self):
        template_path = os.path.join(
            config.root, 'lib/lp/bugs/templates/buglisting.mustache')
        with open(template_path) as template_file:
            return template_file.read()

    @property
    def mustache_listings(self):
        return 'LP.mustache_listings = %s;' % dumps(
            self.mustache_template, cls=JSONEncoderForHTML)

    @property
    def mustache(self):
        """The rendered mustache template."""
        objects = IJSONRequestCache(self.request).objects
        if IUnauthenticatedPrincipal.providedBy(self.request.principal):
            objects = obfuscate_structure(objects)
        model = dict(objects['mustache_model'])
        model.update(self.field_visibility)
        return pystache.render(self.mustache_template, model)

    @property
    def model(self):
        items = [bugtask.model for bugtask in self.getBugListingItems()]
        return {'items': items}


class IBugTaskSearchListingMenu(Interface):
    """A marker interface for the search listing navigation menu."""


class BugTaskSearchListingMenu(NavigationMenu):
    """The search listing navigation menu."""
    usedfor = IBugTaskSearchListingMenu
    facet = 'bugs'

    @property
    def links(self):
        bug_target = self.context.context
        if IDistroSeries.providedBy(bug_target):
            return (
                'nominations',
                )
        if IProductSeries.providedBy(bug_target):
            return (
                'nominations',
                )
        else:
            return ()

    @enabled_with_permission('launchpad.Edit')
    def bugsupervisor(self):
        return Link('+bugsupervisor', 'Change bug supervisor', icon='edit')

    def nominations(self):
        return Link('+nominations', 'Review nominations', icon='bug')


# All sort orders supported by BugTaskSet.search() and a title for
# them.
SORT_KEYS = [
    ('importance', 'Importance', 'desc'),
    ('status', 'Status', 'asc'),
    ('information_type', 'Information Type', 'asc'),
    ('id', 'Number', 'desc'),
    ('title', 'Title', 'asc'),
    ('targetname', 'Package/Project/Series name', 'asc'),
    ('milestone_name', 'Milestone', 'asc'),
    ('date_last_updated', 'Date last updated', 'desc'),
    ('assignee', 'Assignee', 'asc'),
    ('reporter', 'Reporter', 'asc'),
    ('datecreated', 'Age', 'desc'),
    ('tag', 'Tags', 'asc'),
    ('heat', 'Heat', 'desc'),
    ('date_closed', 'Date closed', 'desc'),
    ('dateassigned', 'Date when the bug task was assigned', 'desc'),
    ('number_of_duplicates', 'Number of duplicates', 'desc'),
    ('latest_patch_uploaded', 'Date latest patch uploaded', 'desc'),
    ('message_count', 'Number of comments', 'desc'),
    ('milestone', 'Milestone ID', 'desc'),
    ('specification', 'Linked blueprint', 'asc'),
    ('task', 'Bug task ID', 'desc'),
    ('users_affected_count', 'Number of affected users', 'desc'),
    ]


@implementer(IBugTaskSearchListingMenu)
class BugTaskSearchListingView(LaunchpadFormView, FeedsMixin, BugsInfoMixin):
    """View that renders a list of bugs for a given set of search criteria."""

    related_features = {
        'bugs.dynamic_bug_listings.pre_fetch': False
        }

    # Only include <link> tags for bug feeds when using this view.
    feed_types = (
        BugTargetLatestBugsFeedLink,
        )

    # These widgets are customised so as to keep the presentation of this view
    # and its descendants consistent after refactoring to use
    # LaunchpadFormView as a parent.
    custom_widget('searchtext', NewLineToSpacesWidget)
    custom_widget('status_upstream', LabeledMultiCheckBoxWidget)
    custom_widget('tag', BugTagsWidget)
    custom_widget('tags_combinator', RadioWidget)
    custom_widget('component', LabeledMultiCheckBoxWidget)
    custom_widget('assignee', PersonPickerWidget)
    custom_widget('bug_reporter', PersonPickerWidget)
    custom_widget('bug_commenter', PersonPickerWidget)
    custom_widget('structural_subscriber', PersonPickerWidget)
    custom_widget('subscriber', PersonPickerWidget)

    _batch_navigator = None

    @cachedproperty
    def bug_tracking_usage(self):
        """Whether the context tracks bugs in Launchpad.

        :returns: ServiceUsage enum value
        """
        service_usage = IServiceUsage(self.context)
        return service_usage.bug_tracking_usage

    @cachedproperty
    def external_bugtracker(self):
        """External bug tracking system designated for the context.

        :returns: `IBugTracker` or None
        """
        has_external_bugtracker = IHasExternalBugTracker(self.context, None)
        if has_external_bugtracker is None:
            return None
        else:
            return has_external_bugtracker.getExternalBugTracker()

    @property
    def has_bugtracker(self):
        """Does the `IBugTarget` have a bug tracker or use Launchpad?"""
        usage = IServiceUsage(self.context)
        uses_lp = usage.bug_tracking_usage == ServiceUsage.LAUNCHPAD
        if self.external_bugtracker or uses_lp:
            return True
        return False

    @property
    def can_have_external_bugtracker(self):
        return (IProduct.providedBy(self.context)
                or IProductSeries.providedBy(self.context))

    @property
    def bugtracker(self):
        """Description of the context's bugtracker.

        :returns: str which may contain HTML.
        """
        if self.bug_tracking_usage == ServiceUsage.LAUNCHPAD:
            return 'Launchpad'
        elif self.external_bugtracker:
            return BugTrackerFormatterAPI(self.external_bugtracker).link(None)
        else:
            return 'None specified'

    @cachedproperty
    def upstream_project(self):
        """The linked upstream `IProduct` for the package.

        If this `IBugTarget` is a `IDistributionSourcePackage` or an
        `ISourcePackage` and it is linked to an upstream project, return
        the `IProduct`. Otherwise, return None

        :returns: `IProduct` or None
        """
        if self._sourcePackageContext():
            sp = self.context
        elif self._distroSourcePackageContext():
            sp = self.context.development_version
        else:
            sp = None
        if sp is not None:
            packaging = sp.packaging
            if packaging is not None:
                return packaging.productseries.product
        return None

    @cachedproperty
    def upstream_launchpad_project(self):
        """The linked upstream `IProduct` for the package.

        If this `IBugTarget` is a `IDistributionSourcePackage` or an
        `ISourcePackage` and it is linked to an upstream project that uses
        Launchpad to track bugs, return the `IProduct`. Otherwise,
        return None

        :returns: `IProduct` or None
        """
        product = self.upstream_project
        if (product is not None and
            product.bug_tracking_usage == ServiceUsage.LAUNCHPAD):
            return product
        return None

    page_title = 'Bugs'

    @property
    def label(self):
        if not IHeadingContext.providedBy(self.context):
            return "Bugs for %s" % self.context.displayname

    @property
    def schema(self):
        """Return the schema that defines the form."""
        if self._personContext():
            return IPersonBugTaskSearch
        elif self.isUpstreamProduct:
            return IUpstreamProductBugTaskSearch
        else:
            return IBugTaskSearch

    @property
    def feed_links(self):
        """Prevent conflicts between the page and the atom feed.

        The latest-bugs atom feed matches the default output of this
        view, but it does not match this view's bug listing when
        any search parameters are passed in.
        """
        if self.request.get('QUERY_STRING', '') == '':
            # There is no query in this request, so it's okay for this page to
            # have its feed links.
            return super(BugTaskSearchListingView, self).feed_links
        else:
            # The query changes the results so that they would not match the
            # feed.  In this case, suppress the feed links.
            return []

    def initialize(self):
        """Initialize the view with the request.

        Look for old status names and redirect to a new location if found.
        """
        query_string = self.request.get('QUERY_STRING')
        if query_string:
            query_string_rewritten = (
                rewrite_old_bugtask_status_query_string(query_string))
            if query_string_rewritten != query_string:
                redirect_uri = URI(self.request.getURL()).replace(
                    query=query_string_rewritten)
                self.request.response.redirect(str(redirect_uri), status=301)
                return

        self._migrateOldUpstreamStatus()
        LaunchpadFormView.initialize(self)

        # We call self._validate() here because LaunchpadFormView only
        # validates the form if an action is submitted but, because this form
        # can be called through a query string, we don't want to require an
        # action. We pass an empty dict to _validate() because all the data
        # needing validation is already available internally to self.
        self._validate(None, {})

        expose_structural_subscription_data_to_js(
            self.context, self.request, self.user)
        can_view = (IPrivacy(self.context, None) is None
            or check_permission('launchpad.View', self.context))
        if (can_view and
            not FeedsLayer.providedBy(self.request) and
            not self.request.form.get('advanced')):
            cache = IJSONRequestCache(self.request)
            view_names = set(reg.name for reg
                in iter_view_registrations(self.__class__))
            if len(view_names) != 1:
                raise AssertionError("Ambiguous view name.")
            cache.objects['view_name'] = view_names.pop()
            batch_navigator = self.search()
            cache.objects['mustache_model'] = batch_navigator.model
            cache.objects.update(
                get_batch_properties_for_json_cache(self, batch_navigator))
            cache.objects['field_visibility'] = (
                batch_navigator.field_visibility)
            cache.objects['field_visibility_defaults'] = (
                batch_navigator.field_visibility_defaults)
            cache.objects['cbl_cookie_name'] = (
                batch_navigator.getCookieName())

            cache.objects['order_by'] = ','.join(
                get_sortorder_from_request(self.request))
            cache.objects['sort_keys'] = SORT_KEYS

    @property
    def show_config_portlet(self):
        if (IDistribution.providedBy(self.context) or
            IProduct.providedBy(self.context)):
            return True
        else:
            return False

    @property
    def columns_to_show(self):
        """Returns a sequence of column names to be shown in the listing."""
        upstream_context = self._upstreamContext()
        productseries_context = self._productSeriesContext()
        project_context = self._projectContext()
        distribution_context = self._distributionContext()
        distroseries_context = self._distroSeriesContext()
        distrosourcepackage_context = self._distroSourcePackageContext()
        sourcepackage_context = self._sourcePackageContext()

        if (upstream_context or productseries_context or
            distrosourcepackage_context or sourcepackage_context):
            return ["id", "summary", "importance", "status", "heat"]
        elif distribution_context or distroseries_context:
            return [
                "id", "summary", "packagename", "importance", "status",
                "heat"]
        elif project_context:
            return [
                "id", "summary", "productname", "importance", "status",
                "heat"]
        else:
            raise AssertionError(
                "Unrecognized context; don't know which report "
                "columns to show.")

    bugtask_table_template = ViewPageTemplateFile(
        '../templates/bugs-table-include.pt')

    @property
    def template(self):
        query_string = self.request.get('QUERY_STRING') or ''
        query_params = urlparse.parse_qs(query_string)
        if 'batch_request' in query_params:
            return self.bugtask_table_template
        else:
            return super(BugTaskSearchListingView, self).template

    def validate_search_params(self):
        """Validate the params passed for the search.

        An UnexpectedFormData exception is raised if the user submitted a URL
        that could not have been created from the UI itself.
        """
        # The only way the user should get these field values incorrect is
        # through a stale bookmark or a hand-hacked URL.
        for field_name in ("status", "importance", "milestone", "component",
                           "status_upstream"):
            if self.getFieldError(field_name):
                raise UnexpectedFormData(
                    "Unexpected value for field '%s'. Perhaps your bookmarks "
                    "are out of date or you changed the URL by hand?" %
                    field_name)

        orderby = get_sortorder_from_request(self.request)
        for orderby_col in orderby:
            if orderby_col.startswith("-"):
                orderby_col = orderby_col[1:]

            try:
                orderby_expression[orderby_col]
            except KeyError:
                raise UnexpectedFormData(
                    "Unknown sort column '%s'" % orderby_col)

    def setUpWidgets(self):
        """Customize the onKeyPress event of the assignee chooser."""
        LaunchpadFormView.setUpWidgets(self)

        self.widgets["assignee"].onKeyPress = (
            "selectWidget('assignee_option', event)")

    def validate(self, data):
        """Validates the form."""
        self.validateVocabulariesAdvancedForm()
        self.validate_search_params()

    def _migrateOldUpstreamStatus(self):
        """Converts old upstream status value parameters to new ones.

        Before Launchpad version 1.1.6 (build 4412), the upstream parameter
        in the request was a single string value, coming from a set of
        radio buttons. From that version on, the user can select multiple
        values in the web UI. In order to keep old bookmarks working,
        convert the old string parameter into a list.
        """
        old_upstream_status_values_to_new_values = {
            'only_resolved_upstream': 'resolved_upstream'}

        status_upstream = self.request.get('field.status_upstream')
        if status_upstream in old_upstream_status_values_to_new_values.keys():
            self.request.form['field.status_upstream'] = [
                old_upstream_status_values_to_new_values[status_upstream]]
        elif status_upstream == '':
            del self.request.form['field.status_upstream']
        else:
            # The value of status_upstream is either correct, so nothing to
            # do, or it has some other error, which is handled in
            # LaunchpadFormView's own validation.
            pass

    def buildSearchParams(self, searchtext=None, extra_params=None):
        """Build the BugTaskSearchParams object for the given arguments and
        values specified by the user on this form's widgets.
        """
        # Calling _validate populates the data dictionary as a side-effect
        # of validation.
        data = {}
        self._validate(None, data)

        if extra_params:
            data.update(extra_params)

        if data:
            searchtext = data.get("searchtext")
            if searchtext:
                if searchtext.startswith('#'):
                    searchtext = searchtext[1:]
                if searchtext.isdigit():
                    try:
                        bug = getUtility(IBugSet).get(searchtext)
                    except NotFoundError:
                        pass
                    else:
                        self.request.response.redirect(canonical_url(bug))

            assignee_option = self.request.form.get("assignee_option")
            if assignee_option == "none":
                data['assignee'] = NULL

            has_patch = data.pop("has_patch", False)
            if has_patch:
                data["attachmenttype"] = BugAttachmentType.PATCH

            has_branches = data.get('has_branches', True)
            has_no_branches = data.get('has_no_branches', True)
            if has_branches and not has_no_branches:
                data['linked_branches'] = BugBranchSearch.BUGS_WITH_BRANCHES
            elif not has_branches and has_no_branches:
                data['linked_branches'] = (
                    BugBranchSearch.BUGS_WITHOUT_BRANCHES)
            else:
                data['linked_branches'] = BugBranchSearch.ALL

            has_blueprints = data.get('has_blueprints', True)
            has_no_blueprints = data.get('has_no_blueprints', True)
            if has_blueprints and not has_no_blueprints:
                data['linked_blueprints'] = (
                    BugBlueprintSearch.BUGS_WITH_BLUEPRINTS)
            elif not has_blueprints and has_no_blueprints:
                data['linked_blueprints'] = (
                    BugBlueprintSearch.BUGS_WITHOUT_BLUEPRINTS)
            else:
                data['linked_blueprints'] = BugBlueprintSearch.ALL

            # Filter appropriately if the user wants to restrict the
            # search to only bugs with no package information.
            has_no_package = data.pop("has_no_package", False)
            if has_no_package:
                data["sourcepackagename"] = NULL

        self._buildUpstreamStatusParams(data)

        # "Normalize" the form data into search arguments.
        form_values = {}
        for key, value in data.items():
            if key in ('tag'):
                # Skip tag-related parameters, they
                # are handled later on.
                continue
            if zope_isinstance(value, (list, tuple)):
                if len(value) > 0:
                    form_values[key] = any(*value)
            else:
                form_values[key] = value

        if 'tag' in data:
            # Tags require special handling, since they can be used
            # to search either inclusively or exclusively.
            # We take a look at the `tags_combinator` field, and wrap
            # the tag list in the appropriate search directive (either
            # `any` or `all`). If no value is supplied, we assume `any`,
            # in order to remain compatible with old saved search URLs.
            tags = data['tag']
            tags_combinator_all = (
                'tags_combinator' in data and
                data['tags_combinator'] == BugTagsSearchCombinator.ALL)
            if zope_isinstance(tags, (list, tuple)) and len(tags) > 0:
                if tags_combinator_all:
                    form_values['tag'] = all(*tags)
                else:
                    form_values['tag'] = any(*tags)
            else:
                form_values['tag'] = tags

        search_params = get_default_search_params(self.user)
        search_params.orderby = get_sortorder_from_request(self.request)
        for name, value in form_values.items():
            setattr(search_params, name, value)
        return search_params

    def _buildUpstreamStatusParams(self, data):
        """ Convert the status_upstream value to parameters we can
        send to BugTaskSet.search().
        """
        if 'status_upstream' in data:
            status_upstream = data['status_upstream']
            if 'pending_bugwatch' in status_upstream:
                data['pending_bugwatch_elsewhere'] = True
            if 'resolved_upstream' in status_upstream:
                data['resolved_upstream'] = True
            if 'open_upstream' in status_upstream:
                data['open_upstream'] = True
            if 'hide_upstream' in status_upstream:
                data['has_no_upstream_bugtask'] = True
            del data['status_upstream']

    def _getBatchNavigator(self, tasks):
        """Return the batch navigator to be used to batch the bugtasks."""
        return BugListingBatchNavigator(
            tasks, self.request, columns_to_show=self.columns_to_show,
            size=config.malone.buglist_batch_size,
            target_context=self.context)

    def buildBugTaskSearchParams(self, searchtext=None, extra_params=None):
        """Build the parameters to submit to the `searchTasks` method.

        Use the data submitted in the form to populate a dictionary
        which, when expanded (using **params notation) can serve as the
        input for searchTasks().
        """

        # We force the view to populate the data dictionary by calling
        # _validate here.
        data = {}
        self._validate(None, data)

        searchtext = data.get("searchtext")
        if searchtext and searchtext.isdigit():
            try:
                bug = getUtility(IBugSet).get(searchtext)
            except NotFoundError:
                pass
            else:
                self.request.response.redirect(canonical_url(bug))

        if extra_params:
            data.update(extra_params)

        params = {}

        # A mapping of parameters that appear in the destination
        # with a different name, or are being dropped altogether.
        param_names_map = {
            'searchtext': 'search_text',
            'omit_dupes': 'omit_duplicates',
            'subscriber': 'bug_subscriber',
            'tag': 'tags',
            # The correct value is being retrieved
            # using get_sortorder_from_request()
            'orderby': None,
            }

        for key, value in data.items():
            if key in param_names_map:
                param_name = param_names_map[key]
                if param_name is not None:
                    params[param_name] = value
            else:
                params[key] = value

        assignee_option = self.request.form.get("assignee_option")
        if assignee_option == "none":
            params['assignee'] = NULL

        params['order_by'] = get_sortorder_from_request(self.request)

        return params

    def search(self, searchtext=None, context=None, extra_params=None):
        """Return an `ITableBatchNavigator` for the GET search criteria.

        :param searchtext: Text that must occur in the bug report. If
            searchtext is None, the search text will be gotten from the
            request.

        :param extra_params: A dict that provides search params added to
            the search criteria taken from the request. Params in
            `extra_params` take precedence over request params.
        """
        if self._batch_navigator is None:
            unbatchedTasks = self.searchUnbatched(
                searchtext, context, extra_params)
            self._batch_navigator = self._getBatchNavigator(unbatchedTasks)
        return self._batch_navigator

    def searchUnbatched(self, searchtext=None, context=None,
                        extra_params=None):
        """Return a `SelectResults` object for the GET search criteria.

        :param searchtext: Text that must occur in the bug report. If
            searchtext is None, the search text will be gotten from the
            request.

        :param extra_params: A dict that provides search params added to
            the search criteria taken from the request. Params in
            `extra_params` take precedence over request params.
        """
        # Base classes can provide an explicit search context.
        if not context:
            context = self.context

        search_params = self.buildSearchParams(
            searchtext=searchtext, extra_params=extra_params)
        search_params.user = self.user
        try:
            tasks = context.searchTasks(search_params)
        except ValueError as e:
            self.request.response.addErrorNotification(str(e))
            self.request.response.redirect(canonical_url(
                self.context, rootsite='bugs', view_name='+bugs'))
            tasks = None
        return tasks

    def getWidgetValues(
        self, vocabulary_name=None, vocabulary=None, default_values=()):
        """Return data used to render a field's widget.

        Either `vocabulary_name` or `vocabulary` must be supplied."""
        widget_values = []

        if vocabulary is None:
            assert vocabulary_name is not None, 'No vocabulary specified.'
            vocabulary = vocabulary_registry.get(
                self.context, vocabulary_name)
        for term in vocabulary:
            widget_values.append(
                dict(
                    value=term.token, title=term.title or term.token,
                    checked=term.value in default_values))
        return shortlist(widget_values, longest_expected=12)

    def getStatusWidgetValues(self):
        """Return data used to render the status checkboxes."""
        return self.getWidgetValues(
            vocabulary=BugTaskStatusSearchDisplay,
            default_values=DEFAULT_SEARCH_BUGTASK_STATUSES_FOR_DISPLAY)

    def getImportanceWidgetValues(self):
        """Return data used to render the Importance checkboxes."""
        return self.getWidgetValues(vocabulary=BugTaskImportance)

    def getInformationTypeWidgetValues(self):
        """Return data used to render the Information Type checkboxes."""
        if (IProduct.providedBy(self.context)
            or IDistribution.providedBy(self.context)):
            vocab = InformationTypeVocabulary(
                types=self.context.getAllowedBugInformationTypes())
        else:
            vocab = InformationType
        return self.getWidgetValues(vocabulary=vocab)

    def getMilestoneWidgetValues(self):
        """Return data used to render the milestone checkboxes."""
        return self.getWidgetValues("MilestoneWithDateExpected")

    def shouldShowAssigneeWidget(self):
        """Should the assignee widget be shown on the advanced search page?"""
        return True

    def shouldShowCommenterWidget(self):
        """Show the commenter widget on the advanced search page?"""
        return True

    def shouldShowComponentWidget(self):
        """Show the component widget on the advanced search page?"""
        context = self.context
        return (
            (IDistribution.providedBy(context) and
             context.currentseries is not None) or
            IDistroSeries.providedBy(context) or
            ISourcePackage.providedBy(context))

    def shouldShowStructuralSubscriberWidget(self):
        """Should the structural subscriber widget be shown on the page?

        Show the widget when there are subordinate structures.
        """
        return self.structural_subscriber_label is not None

    def shouldShowNoPackageWidget(self):
        """Should the widget to filter on bugs with no package be shown?

        The widget will be shown only on a distribution or
        distroseries's advanced search page.
        """
        return (IDistribution.providedBy(self.context) or
                IDistroSeries.providedBy(self.context))

    def shouldShowReporterWidget(self):
        """Should the reporter widget be shown on the advanced search page?"""
        return True

    def shouldShowReleaseCriticalPortlet(self):
        """Should the page include a portlet showing release-critical bugs
        for different series.
        """
        return (
            IDistribution.providedBy(self.context) and self.context.series
            or IDistroSeries.providedBy(self.context)
            or IProduct.providedBy(self.context) and self.context.series
            or IProductSeries.providedBy(self.context))

    def shouldShowSubscriberWidget(self):
        """Show the subscriber widget on the advanced search page?"""
        return True

    def shouldShowUpstreamStatusBox(self):
        """Should the upstream status filtering widgets be shown?"""
        return self.isUpstreamProduct or not (
            IProduct.providedBy(self.context) or
            IProjectGroup.providedBy(self.context))

    def shouldShowTeamPortlet(self):
        """Should the User's Teams portlet me shown in the results?"""
        return False

    @property
    def structural_subscriber_label(self):
        if IDistribution.providedBy(self.context):
            return 'Package or series subscriber'
        elif IDistroSeries.providedBy(self.context):
            return 'Package subscriber'
        elif IProduct.providedBy(self.context):
            return 'Series subscriber'
        elif IProjectGroup.providedBy(self.context):
            return 'Project or series subscriber'
        elif IPerson.providedBy(self.context):
            return 'Project, distribution, package, or series subscriber'
        else:
            return None

    def shouldShowTargetName(self):
        """Should the bug target name be displayed in the list of results?

        This is mainly useful for the listview.
        """
        # It doesn't make sense to show the target name when viewing product
        # bugs.
        if IProduct.providedBy(self.context):
            return False
        else:
            return True

    def shouldShowAdvancedForm(self):
        """Return True if the advanced form should be shown, or False."""
        if (self.request.form.get('advanced')
            or self.form_has_errors):
            return True
        else:
            return False

    @property
    def should_show_bug_information(self):
        return self.bug_tracking_usage == ServiceUsage.LAUNCHPAD

    @property
    def form_has_errors(self):
        """Return True if the form has errors, otherwise False."""
        return len(self.errors) > 0

    def validateVocabulariesAdvancedForm(self):
        """Provides a meaningful message for vocabulary validation errors."""
        error_message = _(
            "There's no person with the name or email address '%s'.")

        for name in ('assignee', 'bug_reporter', 'structural_subscriber',
                     'bug_commenter', 'subscriber'):
            if self.getFieldError(name):
                self.setFieldError(
                    name, error_message %
                        self.request.get('field.%s' % name))

    @property
    def isUpstreamProduct(self):
        """Is the context a Product that does not use Malone?"""
        return (
            IProduct.providedBy(self.context)
            and self.context.bug_tracking_usage != ServiceUsage.LAUNCHPAD)

    def _upstreamContext(self):
        """Is this page being viewed in an upstream context?

        Return the IProduct if yes, otherwise return None.
        """
        return IProduct(self.context, None)

    def _productSeriesContext(self):
        """Is this page being viewed in a product series context?

        Return the IProductSeries if yes, otherwise return None.
        """
        return IProductSeries(self.context, None)

    def _projectContext(self):
        """Is this page being viewed in a project context?

        Return the IProjectGroup if yes, otherwise return None.
        """
        return IProjectGroup(self.context, None)

    def _personContext(self):
        """Is this page being viewed in a person context?

        Return the IPerson if yes, otherwise return None.
        """
        return IPerson(self.context, None)

    def _distributionContext(self):
        """Is this page being viewed in a distribution context?

        Return the IDistribution if yes, otherwise return None.
        """
        return IDistribution(self.context, None)

    def _distroSeriesContext(self):
        """Is this page being viewed in a distroseries context?

        Return the IDistroSeries if yes, otherwise return None.
        """
        return IDistroSeries(self.context, None)

    def _sourcePackageContext(self):
        """Is this view in a [distroseries] sourcepackage context?

        Return the ISourcePackage if yes, otherwise return None.
        """
        return ISourcePackage(self.context, None)

    def _distroSourcePackageContext(self):
        """Is this page being viewed in a distribution sourcepackage context?

        Return the IDistributionSourcePackage if yes, otherwise return None.
        """
        return IDistributionSourcePackage(self.context, None)

    @property
    def addquestion_url(self):
        """Return the URL for the +addquestion view for the context."""
        if IQuestionTarget.providedBy(self.context):
            answers_usage = IServiceUsage(self.context).answers_usage
            if answers_usage == ServiceUsage.LAUNCHPAD:
                return canonical_url(
                    self.context, rootsite='answers',
                    view_name='+addquestion')
        else:
            return None


class BugTargetView(LaunchpadView):
    """Used to grab bugs for a bug target; used by the latest bugs portlet"""

    def latestBugTasks(self, quantity=5):
        """Return <quantity> latest bugs reported against this target."""
        params = BugTaskSearchParams(orderby="-datecreated",
                                     omit_dupes=True,
                                     user=getUtility(ILaunchBag).user)

        tasklist = self.context.searchTasks(params)
        return tasklist[:quantity]


class TextualBugTaskSearchListingView(BugTaskSearchListingView):
    """View that renders a list of bug IDs for a given set of search criteria.
    """

    def render(self):
        """Render the BugTarget for text display."""
        self.request.response.setHeader(
            'Content-type', 'text/plain')

        # This uses the BugTaskSet internal API instead of using the
        # standard searchTasks() because the latter can retrieve a lot
        # of bugs and we don't want to load all of that data in memory.
        # Retrieving only the bug numbers is much more efficient.
        search_params = self.buildSearchParams()
        search_params.setTarget(self.context)

        return u"".join("%d\n" % bug_id for bug_id in
            getUtility(IBugTaskSet).searchBugIds(search_params))


class BugsBugTaskSearchListingView(BugTaskSearchListingView):
    """Search all bug reports."""

    columns_to_show = ["id", "summary", "bugtargetdisplayname",
                       "importance", "status", "heat"]
    schema = IFrontPageBugTaskSearch
    custom_widget('scope', ProjectScopeWidget)
    label = page_title = 'Search all bug reports'

    def initialize(self):
        """Initialize the view for the request."""
        BugTaskSearchListingView.initialize(self)
        if not self._isRedirected():
            self._redirectToSearchContext()

    def _redirectToSearchContext(self):
        """Check whether a target was given and redirect to it.

        All the URL parameters will be passed on to the target's +bugs
        page.

        If the target widget contains errors, redirect to the front page
        which will handle the error.
        """
        try:
            search_target = self.widgets['scope'].getInputValue()
        except InputErrors:
            query_string = self.request['QUERY_STRING']
            bugs_url = "%s?%s" % (canonical_url(self.context), query_string)
            self.request.response.redirect(bugs_url)
        else:
            if search_target is not None:
                query_string = self.request['QUERY_STRING']
                search_url = "%s/+bugs?%s" % (
                    canonical_url(search_target), query_string)
                self.request.response.redirect(search_url)


class BugTaskExpirableListingView(BugTaskSearchListingView):
    """View for listing Incomplete bugs that can expire."""

    @property
    def can_show_expirable_bugs(self):
        """Return True or False if expirable bug listing can be shown."""
        return target_has_expirable_bugs_listing(self.context)

    @property
    def columns_to_show(self):
        """Show the columns that summarise expirable bugs."""
        if (IDistribution.providedBy(self.context)
            or IDistroSeries.providedBy(self.context)):
            return [
                'id', 'summary', 'packagename', 'date_last_updated', 'heat']
        else:
            return ['id', 'summary', 'date_last_updated', 'heat']

    def search(self):
        """Return an `ITableBatchNavigator` for the expirable bugtasks."""
        bugtaskset = getUtility(IBugTaskSet)
        bugtasks = bugtaskset.findExpirableBugTasks(
            user=self.user, target=self.context, min_days_old=0)
        return BugListingBatchNavigator(
            bugtasks, self.request, columns_to_show=self.columns_to_show,
            size=config.malone.buglist_batch_size)

    page_title = 'Expirable bugs'

    @property
    def label(self):
        if not IHeadingContext.providedBy(self.context):
            return "%s in %s" % (self.page_title, self.context.displayname)
        return self.page_title


class BugNominationsView(BugTaskSearchListingView):
    """View for accepting/declining bug nominations."""

    page_title = 'Nominated bugs'

    @property
    def label(self):
        return "Bugs nominated for %s" % self.context.displayname

    def search(self):
        """Return all the nominated tasks for this series."""
        if IDistroSeries.providedBy(self.context):
            main_context = self.context.distribution
        elif IProductSeries.providedBy(self.context):
            main_context = self.context.product
        else:
            raise AssertionError(
                'Unknown nomination target: %r' % self.context)
        return BugTaskSearchListingView.search(
            self, context=main_context,
            extra_params=dict(nominated_for=self.context))
