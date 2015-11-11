# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""IBugTask-related browser views."""

__metaclass__ = type

__all__ = [
    'bugtarget_renderer',
    'BugTargetTraversalMixin',
    'BugTaskBreadcrumb',
    'BugTaskContextMenu',
    'BugTaskCreateQuestionView',
    'BugTaskDeletionView',
    'BugTaskEditView',
    'BugTaskNavigation',
    'BugTaskPrivacyAdapter',
    'BugTaskRemoveQuestionView',
    'BugTasksNominationsView',
    'BugTasksTableView',
    'BugTaskTableRowView',
    'BugTaskTextView',
    'BugTaskView',
    'can_add_package_task_to_bug',
    'can_add_project_task_to_bug',
    'get_comments_for_bugtask',
    'get_visible_comments',
    ]

from collections import defaultdict
from datetime import (
    datetime,
    timedelta,
    )
from itertools import groupby
from operator import attrgetter
import re
import urllib

from lazr.delegates import delegate_to
from lazr.lifecycle.event import ObjectModifiedEvent
from lazr.lifecycle.snapshot import Snapshot
from lazr.restful.interface import copy_field
from lazr.restful.interfaces import (
    IFieldHTMLRenderer,
    IJSONRequestCache,
    IReference,
    IWebServiceClientRequest,
    )
from lazr.restful.utils import smartquote
from pytz import utc
from simplejson import dumps
import transaction
from z3c.pt.pagetemplate import ViewPageTemplateFile
from zope import formlib
from zope.component import (
    adapter,
    ComponentLookupError,
    getAdapter,
    getMultiAdapter,
    getUtility,
    )
from zope.event import notify
from zope.formlib.widget import CustomWidgetFactory
from zope.interface import (
    implementer,
    providedBy,
    )
from zope.schema import Choice
from zope.schema.vocabulary import (
    getVocabularyRegistry,
    SimpleVocabulary,
    )
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy
from zope.traversing.browser import absoluteURL
from zope.traversing.interfaces import IPathAdapter

from lp import _
from lp.app.browser.launchpadform import (
    action,
    custom_widget,
    LaunchpadEditFormView,
    LaunchpadFormView,
    ReturnToReferrerMixin,
    )
from lp.app.browser.lazrjs import (
    TextAreaEditorWidget,
    TextLineEditorWidget,
    vocabulary_to_choice_edit_items,
    )
from lp.app.browser.stringformatter import FormattersAPI
from lp.app.browser.tales import ObjectImageDisplayAPI
from lp.app.browser.vocabulary import vocabulary_filters
from lp.app.enums import PROPRIETARY_INFORMATION_TYPES
from lp.app.errors import NotFoundError
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.bugs.browser.bug import (
    BugContextMenu,
    BugTextView,
    BugViewMixin,
    )
from lp.bugs.browser.bugcomment import (
    build_comments_from_chunks,
    group_comments_with_activity,
    )
from lp.bugs.browser.widgets.bugtask import (
    AssigneeDisplayWidget,
    BugTaskAssigneeWidget,
    BugTaskBugWatchWidget,
    BugTaskSourcePackageNameWidget,
    BugTaskTargetWidget,
    DBItemDisplayWidget,
    )
from lp.bugs.interfaces.bug import (
    IBug,
    IBugSet,
    )
from lp.bugs.interfaces.bugactivity import IBugActivity
from lp.bugs.interfaces.bugattachment import (
    BugAttachmentType,
    IBugAttachmentSet,
    )
from lp.bugs.interfaces.bugnomination import (
    BugNominationStatus,
    IBugNominationSet,
    )
from lp.bugs.interfaces.bugtarget import ISeriesBugTarget
from lp.bugs.interfaces.bugtask import (
    BugTaskImportance,
    BugTaskStatus,
    CannotDeleteBugtask,
    IBugTask,
    IBugTaskSet,
    ICreateQuestionFromBugTaskForm,
    IllegalTarget,
    IRemoveQuestionFromBugTaskForm,
    UserCannotEditBugTaskStatus,
    )
from lp.bugs.interfaces.bugtasksearch import BugTaskSearchParams
from lp.bugs.interfaces.bugtracker import BugTrackerType
from lp.bugs.interfaces.bugwatch import BugWatchActivityStatus
from lp.bugs.interfaces.cve import ICveSet
from lp.bugs.vocabularies import BugTaskMilestoneVocabulary
from lp.code.interfaces.branchcollection import IAllBranches
from lp.registry.interfaces.distribution import (
    IDistribution,
    IDistributionSet,
    )
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )
from lp.registry.interfaces.distroseries import (
    IDistroSeries,
    IDistroSeriesSet,
    )
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.sourcepackage import ISourcePackage
from lp.registry.model.personroles import PersonRoles
from lp.services.config import config
from lp.services.features import getFeatureFlag
from lp.services.feeds.browser import FeedsMixin
from lp.services.fields import PersonChoice
from lp.services.mail.notification import get_unified_diff
from lp.services.privacy.interfaces import IObjectPrivacy
from lp.services.propertycache import (
    cachedproperty,
    get_property_cache,
    )
from lp.services.webapp import (
    canonical_url,
    LaunchpadView,
    Navigation,
    redirection,
    stepthrough,
    )
from lp.services.webapp.authorization import (
    check_permission,
    precache_permission_for_objects,
    )
from lp.services.webapp.breadcrumb import Breadcrumb
from lp.services.webapp.escaping import (
    html_escape,
    structured,
    )
from lp.services.webapp.interfaces import ILaunchBag


vocabulary_registry = getVocabularyRegistry()


@adapter(IBugTask, IReference, IWebServiceClientRequest)
@implementer(IFieldHTMLRenderer)
def bugtarget_renderer(context, field, request):
    """Render a bugtarget as a link."""

    def render(value):
        html = structured(
            """<span>
            <a href="%(href)s" class="%(css_class)s">%(displayname)s</a>
            </span>""",
            href=canonical_url(context.target),
            css_class=ObjectImageDisplayAPI(context.target).sprite_css(),
            displayname=context.bugtargetdisplayname).escapedtext
        return html
    return render


def unique_title(title):
    """Canonicalise a message title to help identify messages with new
    information in their titles.
    """
    if title is None:
        return None
    title = title.lower()
    if title.startswith('re:'):
        title = title[3:]
    return title.strip()


def get_comments_for_bugtask(bugtask, truncate=False, for_display=False,
    slice_info=None, show_spam_controls=False, user=None):
    """Return BugComments related to a bugtask.

    This code builds a sorted list of BugComments in one shot,
    requiring only two database queries. It removes the titles
    for those comments which do not have a "new" subject line

    :param for_display: If true, the zeroth comment is given an empty body so
        that it will be filtered by get_visible_comments.
    :param slice_info: If not None, defines a list of slices of the comments
        to retrieve.
    """
    comments = build_comments_from_chunks(bugtask, truncate=truncate,
        slice_info=slice_info, show_spam_controls=show_spam_controls,
        user=user, hide_first=for_display)
    # TODO: further fat can be shaved off here by limiting the attachments we
    # query to those that slice_info would include.
    for comment in comments.values():
        get_property_cache(comment._message).bugattachments = []

    for attachment in bugtask.bug.attachments_unpopulated:
        message_id = attachment._messageID
        if message_id not in comments:
            # We are not showing this message.
            continue
        if attachment.type == BugAttachmentType.PATCH:
            comments[message_id].patches.append(attachment)
        cache = get_property_cache(attachment.message)
        cache.bugattachments.append(attachment)
    comments = sorted(comments.values(), key=attrgetter("index"))
    current_title = bugtask.bug.title
    for comment in comments:
        if not ((unique_title(comment.title) == \
                 unique_title(current_title)) or \
                (unique_title(comment.title) == \
                 unique_title(bugtask.bug.title))):
            # this comment has a new title, so make that the rolling focus
            current_title = comment.title
            comment.display_title = True
    return comments


def get_visible_comments(comments, user=None):
    """Return comments, filtering out empty or duplicated ones."""
    visible_comments = []
    previous_comment = None
    for comment in comments:
        # Omit comments that are identical to their previous
        # comment, which were probably produced by
        # double-submissions or user errors, and which don't add
        # anything useful to the bug itself.
        # Also omit comments with no body text or attachments to display.
        if (comment.isEmpty() or
            previous_comment and
            previous_comment.isIdenticalTo(comment)):
            continue

        visible_comments.append(comment)
        previous_comment = comment

    # These two lines are here to fill the ValidPersonOrTeamCache cache,
    # so that checking owner.is_valid_person, when rendering the link,
    # won't issue a DB query. Note that this should be obsolete now with
    # getMessagesForView improvements.
    commenters = set(comment.owner for comment in visible_comments)
    getUtility(IPersonSet).getValidPersons(commenters)

    # If a user is supplied, we can also strip out comments that the user
    # cannot see, because they have been marked invisible.
    strip_invisible = True
    if user is not None:
        # XXX cjwatson 2015-09-15: Unify with
        # Bug.userCanSetCommentVisibility, which also allows
        # project-privileged users.
        role = PersonRoles(user)
        strip_invisible = not (role.in_admin or role.in_registry_experts)
    if strip_invisible:
        visible_comments = [c for c in visible_comments
                            if c.visible or c.owner == user]

    return visible_comments


class BugTargetTraversalMixin:
    """Mix-in in class that provides .../+bug/NNN traversal."""

    redirection('+bug', '+bugs')

    @stepthrough('+bug')
    def traverse_bug(self, name):
        """Traverses +bug portions of URLs"""
        return self._get_task_for_context(name)

    def _get_task_for_context(self, name):
        """Return the IBugTask for this name in this context.

        If the bug has been reported, but not in this specific context, a
        redirect to the default context will be returned.

        Returns None if no bug with the given name is found, or the
        bug is not accessible to the current user.
        """
        context = self.context

        # Raises NotFoundError if no bug is found
        bug = getUtility(IBugSet).getByNameOrID(name)

        # Get out now if the user cannot view the bug. Continuing may
        # reveal information about its context
        if not check_permission('launchpad.View', bug):
            return None

        # Loop through this bug's tasks to try and find the appropriate task
        # for this context. We always want to return a task, whether or not
        # the user has the permission to see it so that, for example, an
        # anonymous user is presented with a login screen at the correct URL,
        # rather than making it look as though this task was "not found",
        # because it was filtered out by privacy-aware code.
        for bugtask in bug.bugtasks:
            if bugtask.target == context:
                # Security proxy this object on the way out.
                return getUtility(IBugTaskSet).get(bugtask.id)

        # If we've come this far, there's no task for the requested context.
        # If we are attempting to navigate past the non-existent bugtask,
        # we raise NotFound error. eg +delete or +edit etc.
        # Otherwise we are simply navigating to a non-existent task and so we
        # redirect to one that exists.
        travseral_stack = self.request.getTraversalStack()
        if len(travseral_stack) > 0:
            raise NotFoundError
        return self.redirectSubTree(
            canonical_url(bug.default_bugtask, request=self.request))


class BugTaskNavigation(Navigation):
    """Navigation for the `IBugTask`."""
    usedfor = IBugTask

    @stepthrough('attachments')
    def traverse_attachments(self, name):
        """traverse to an attachment by id."""
        if name.isdigit():
            attachment = getUtility(IBugAttachmentSet)[name]
            if attachment is not None and attachment.bug == self.context.bug:
                return self.redirectSubTree(
                    canonical_url(attachment), status=301)

    @stepthrough('+attachment')
    def traverse_attachment(self, name):
        """traverse to an attachment by id."""
        if name.isdigit():
            attachment = getUtility(IBugAttachmentSet)[name]
            if attachment is not None and attachment.bug == self.context.bug:
                return attachment

    @stepthrough('comments')
    def traverse_comments(self, name):
        """Traverse to a comment by index."""
        if not name.isdigit():
            return None
        index = int(name)
        # Ask the DB to slice out just the comment that we need.
        comments = get_comments_for_bugtask(
            self.context, slice_info=[slice(index, index + 1)])
        # XXX cjwatson 2015-09-15: Unify with
        # Bug.userCanSetCommentVisibility, which also allows
        # project-privileged users.
        user = getUtility(ILaunchBag).user
        roles = PersonRoles(user) if user else None
        if (comments and (
                comments[0].visible
                or user and (
                    comments[0].owner == user
                    or roles.in_admin or roles.in_registry_experts))):
            return comments[0]
        return None

    @stepthrough('nominations')
    def traverse_nominations(self, nomination_id):
        """Traverse to a nomination by id."""
        if not nomination_id.isdigit():
            return None
        return getUtility(IBugNominationSet).get(nomination_id)

    redirection('references', '..')


class BugTaskContextMenu(BugContextMenu):
    """Context menu of actions that can be performed upon an `IBugTask`."""
    usedfor = IBugTask


class BugTaskTextView(LaunchpadView):
    """View for a simple text page displaying information about a bug task."""

    def render(self):
        """Return a text representation of the parent bug."""
        view = BugTextView(self.context.bug, self.request)
        view.initialize()
        return view.render()


class BugTaskView(LaunchpadView, BugViewMixin, FeedsMixin):
    """View class for presenting information about an `IBugTask`."""

    def __init__(self, context, request):
        LaunchpadView.__init__(self, context, request)

        self.notices = []

        # Make sure we always have the current bugtask.
        if not IBugTask.providedBy(context):
            self.context = getUtility(ILaunchBag).bugtask
        else:
            self.context = context
        list(getUtility(IPersonSet).getPrecachedPersonsFromIDs(
            [self.context.bug.ownerID], need_validity=True))

    @property
    def page_title(self):
        return self.context.bug.id

    @property
    def label(self):
        heading = 'Bug #%s in %s' % (
            self.context.bug.id, self.context.bugtargetdisplayname)
        title = FormattersAPI(self.context.bug.title).obfuscate_email()
        return smartquote('%s: "%s"') % (heading, title)

    @cachedproperty
    def page_description(self):
        return IBug(self.context).description

    @property
    def next_url(self):
        """Provided so returning to the page they came from works."""
        referer = self.request.getHeader('referer')

        # XXX bdmurray 2010-09-30 bug=98437: work around zope's test
        # browser setting referer to localhost.
        if referer and referer != 'localhost':
            next_url = referer
        else:
            next_url = canonical_url(self.context)
        return next_url

    @property
    def cancel_url(self):
        """Provided so returning to the page they came from works."""
        referer = self.request.getHeader('referer')

        # XXX bdmurray 2010-09-30 bug=98437: work around zope's test
        # browser setting referer to localhost.
        if referer and referer != 'localhost':
            cancel_url = referer
        else:
            cancel_url = canonical_url(self.context)
        return cancel_url

    @cachedproperty
    def is_duplicate_active(self):
        active = True
        if self.context.bug.duplicateof is not None:
            naked_duplicate = removeSecurityProxy(
                self.context.bug.duplicateof)
            active = getattr(
                naked_duplicate.default_bugtask.target, 'active', True)
        return active

    @cachedproperty
    def api_request(self):
        return IWebServiceClientRequest(self.request)

    @cachedproperty
    def recommended_canonical_url(self):
        return canonical_url(self.context.bug, rootsite='bugs')

    @property
    def information_type(self):
        return self.context.bug.information_type.title

    def initialize(self):
        """Set up the needed widgets."""
        bug = self.context.bug
        cache = IJSONRequestCache(self.request)
        cache.objects['bug'] = bug
        subscribers_url_data = {
            'web_link': canonical_url(bug, rootsite='bugs'),
            'self_link': absoluteURL(bug, self.api_request),
            }
        cache.objects['subscribers_portlet_url_data'] = subscribers_url_data
        cache.objects['total_comments_and_activity'] = (
            self.total_comments + self.total_activity)
        cache.objects['initial_comment_batch_offset'] = (
            self.visible_initial_comments + 1)
        cache.objects['first visible_recent_comment'] = (
            self.total_comments - self.visible_recent_comments)

        # See render() for how this flag is used.
        self._redirecting_to_bug_list = False

        self.bug_title_edit_widget = TextLineEditorWidget(
            bug, IBug['title'], "Edit this summary", 'h1',
            edit_url=canonical_url(self.context, view_name='+edit'),
            max_width='95%', truncate_lines=6)

        # XXX 2010-10-05 gmb bug=655597:
        # This line of code keeps the view's query count down,
        # possibly using witchcraft. It should be rewritten to be
        # useful or removed in favour of making other queries more
        # efficient. The witchcraft is because the subscribers are accessed
        # in the initial page load, so the data is actually used.
        if self.user is not None:
            list(bug.getSubscribersForPerson(self.user))

    def userIsSubscribed(self):
        """Is the user subscribed to this bug?"""
        return (
            self.context.bug.isSubscribed(self.user) or
            self.context.bug.isSubscribedToDupes(self.user))

    def render(self):
        """Render the bug list if the user has permission to see the bug."""
        # Prevent normal rendering when redirecting to the bug list
        # after unsubscribing from a private bug, because rendering the
        # bug page would raise Unauthorized errors!
        if self._redirecting_to_bug_list:
            return u''
        else:
            return LaunchpadView.render(self)

    def _nominateBug(self, series):
        """Nominate the bug for the series and redirect to the bug page."""
        self.context.bug.addNomination(self.user, series)
        self.request.response.addInfoNotification(
            'This bug has been nominated to be fixed in %s.' %
                series.bugtargetdisplayname)
        self.request.response.redirect(canonical_url(self.context))

    @cachedproperty
    def comments(self):
        """Return the bugtask's comments."""
        return self._getComments()

    def _getComments(self, slice_info=None):
        bug = self.context.bug
        show_spam_controls = bug.userCanSetCommentVisibility(self.user)
        return get_comments_for_bugtask(
            self.context, truncate=True, slice_info=slice_info,
            for_display=True, show_spam_controls=show_spam_controls,
            user=self.user)

    @cachedproperty
    def interesting_activity(self):
        return self._getInterestingActivity()

    def _getInterestingActivity(self, earliest_activity_date=None,
                                latest_activity_date=None):
        """A sequence of interesting bug activity."""
        if (earliest_activity_date is not None and
            latest_activity_date is not None):
            # Only get the activity for the date range that we're
            # interested in to save us from processing too much.
            activity = self.context.bug.getActivityForDateRange(
                start_date=earliest_activity_date,
                end_date=latest_activity_date)
        else:
            activity = self.context.bug.activity
        bug_change_re = (
            'affects|description|security vulnerability|information type|'
            'summary|tags|visibility|bug task deleted')
        bugtask_change_re = (
            '[a-z0-9][a-z0-9\+\.\-]+( \([A-Za-z0-9\s]+\))?: '
            '(assignee|importance|milestone|status)')
        interesting_match = re.compile(
            "^(%s|%s)$" % (bug_change_re, bugtask_change_re)).match

        activity_items = [
            activity_item for activity_item in activity
            if interesting_match(activity_item.whatchanged) is not None]
        # Pre-load the doers of the activities in one query.
        person_ids = set(
            activity_item.personID for activity_item in activity_items)
        list(getUtility(IPersonSet).getPrecachedPersonsFromIDs(
            person_ids, need_validity=True))

        interesting_activity = tuple(
            BugActivityItem(activity_item) for activity_item in activity_items)

        # This is a bit kludgy but it means that interesting_activity is
        # populated correctly for all subsequent calls.
        self._interesting_activity_cached_value = interesting_activity
        return interesting_activity

    def _getEventGroups(self, batch_size=None, offset=None):
        # Ensure truncation results in < max_length comments as expected
        assert(config.malone.comments_list_truncate_oldest_to
               + config.malone.comments_list_truncate_newest_to
               < config.malone.comments_list_max_length)

        if (not self.visible_comments_truncated_for_display and
            batch_size is None):
            comments = self.comments
        elif batch_size is not None:
            # If we're limiting to a given set of comments, we work on
            # just that subset of comments from hereon in, which saves
            # on processing time a bit.
            if offset is None:
                offset = self.visible_initial_comments
            comments = self._getComments([
                slice(offset, offset + batch_size)])
        else:
            # the comment function takes 0-offset counts where comment 0 is
            # the initial description, so we need to add one to the limits
            # to adjust.
            oldest_count = 1 + self.visible_initial_comments
            new_count = 1 + self.total_comments - self.visible_recent_comments
            slice_info = [
                slice(None, oldest_count),
                slice(new_count, None),
                ]
            comments = self._getComments(slice_info)

        visible_comments = get_visible_comments(
            comments, user=self.user)
        if len(visible_comments) > 0 and batch_size is not None:
            first_comment = visible_comments[0]
            last_comment = visible_comments[-1]
            interesting_activity = (
                self._getInterestingActivity(
                    earliest_activity_date=first_comment.datecreated,
                    latest_activity_date=last_comment.datecreated))
        else:
            interesting_activity = self.interesting_activity

        event_groups = group_comments_with_activity(
            comments=visible_comments,
            activities=interesting_activity)
        return event_groups

    @cachedproperty
    def _event_groups(self):
        """Return a sorted list of event groups for the current BugTask.

        This is a @cachedproperty wrapper around _getEventGroups(). It's
        here so that we can override it in descendant views, passing
        batch size parameters and suchlike to _getEventGroups() as we
        go.
        """
        return self._getEventGroups()

    @cachedproperty
    def activity_and_comments(self):
        """Build list of comments interleaved with activities

        When activities occur on the same day a comment was posted,
        encapsulate them with that comment.  For the remainder, group
        then as if owned by the person who posted the first action
        that day.

        If the number of comments exceeds the configured maximum limit, the
        list will be truncated to just the first and last sets of comments.

        The division between the most recent and oldest is marked by an entry
        in the list with the key 'num_hidden' defined.
        """
        event_groups = self._event_groups

        def group_activities_by_target(activities):
            activities = sorted(
                activities, key=attrgetter(
                    "datechanged", "target", "attribute"))
            return [
                {"target": target, "activity": list(activity)}
                for target, activity in groupby(
                    activities, attrgetter("target"))]

        def comment_event_dict(comment):
            actors = set(activity.person for activity in comment.activity)
            actors.add(comment.owner)
            assert len(actors) == 1, actors
            dates = set(activity.datechanged for activity in comment.activity)
            dates.add(comment.datecreated)
            comment.activity = group_activities_by_target(comment.activity)
            return {
                "comment": comment,
                "date": min(dates),
                "person": actors.pop(),
                }

        def activity_event_dict(activities):
            actors = set(activity.person for activity in activities)
            assert len(actors) == 1, actors
            dates = set(activity.datechanged for activity in activities)
            return {
                "activity": group_activities_by_target(activities),
                "date": min(dates),
                "person": actors.pop(),
                }

        def event_dict(event_group):
            if isinstance(event_group, list):
                return activity_event_dict(event_group)
            else:
                return comment_event_dict(event_group)

        events = map(event_dict, event_groups)

        # Insert blanks if we're showing only a subset of the comment list.
        if self.visible_comments_truncated_for_display:
            # Find the oldest recent comment in the event list.
            index = 0
            prev_comment = None
            while index < len(events):
                event = events[index]
                comment = event.get("comment")
                if prev_comment is None:
                    prev_comment = comment
                    index += 1
                    continue
                if comment is None:
                    index += 1
                    continue
                if prev_comment.index + 1 != comment.index:
                    # There is a gap here, record it.

                    # The number of items between two items is one less than
                    # their difference. There is one number between 1 and 3,
                    # not 2 (their difference).
                    num_hidden = abs(comment.index - prev_comment.index) - 1
                    separator = {
                        'date': prev_comment.datecreated,
                        'num_hidden': num_hidden,
                        }
                    events.insert(index, separator)
                    index += 1
                prev_comment = comment
                index += 1
        return events

    @property
    def visible_initial_comments(self):
        """How many initial comments are being shown."""
        return config.malone.comments_list_truncate_oldest_to

    @property
    def visible_recent_comments(self):
        """How many recent comments are being shown."""
        return config.malone.comments_list_truncate_newest_to

    @cachedproperty
    def visible_comments_truncated_for_display(self):
        """Whether the visible comment list is truncated for display."""
        show_all = (self.request.form_ng.getOne('comments') == 'all')
        if show_all:
            return False
        max_comments = config.malone.comments_list_max_length
        return self.total_comments > max_comments

    @cachedproperty
    def total_comments(self):
        """We count all comments because the db cannot do visibility yet."""
        return self.context.bug.bug_messages.count() - 1

    @cachedproperty
    def total_activity(self):
        """Return the count of all activity items for the bug."""
        # Ignore the first activity item, since it relates to the bug's
        # creation.
        return self.context.bug.activity.count() - 1

    def wasDescriptionModified(self):
        """Return a boolean indicating whether the description was modified"""
        return (self.context.bug._indexed_messages(
            include_content=True, include_parents=False)[0].text_contents !=
            self.context.bug.description)

    @cachedproperty
    def linked_branches(self):
        """Filter out the bug_branch links to non-visible private branches."""
        linked_branches = list(
            self.context.bug.getVisibleLinkedBranches(
                self.user, eager_load=True))
        # This is an optimization for when we look at the merge proposals.
        if linked_branches:
            list(getUtility(IAllBranches).getMergeProposals(
                for_branches=[link.branch for link in linked_branches],
                eager_load=True))
        return linked_branches

    @property
    def days_to_expiration(self):
        """Return the number of days before the bug is expired, or None."""
        if not self.context.bug.isExpirable(days_old=0):
            return None

        expire_after = timedelta(days=config.malone.days_before_expiration)
        expiration_date = self.context.bug.date_last_updated + expire_after
        remaining_time = expiration_date - datetime.now(utc)
        return remaining_time.days

    @property
    def expiration_message(self):
        """Return a message indicating the time to expiration for the bug.

        If the expiration date of the bug has already passed, the
        message returned will indicate this. This deals with situations
        where a bug is due to be marked invalid but has not yet been
        dealt with by the bug expiration script.

        If the bug is not due to be expired None will be returned.
        """
        if not self.context.bug.isExpirable(days_old=0):
            return None

        days_to_expiration = self.days_to_expiration
        if days_to_expiration <= 0:
            # We should always display a positive number to the user,
            # whether we're talking about the past or the future.
            days_to_expiration = -days_to_expiration
            message = ("This bug report was marked for expiration %i days "
                "ago.")
        else:
            message = ("This bug report will be marked for expiration in %i "
                "days if no further activity occurs.")

        return message % days_to_expiration

    @property
    def official_tags(self):
        """The list of official tags for this bug."""
        target_official_tags = set(self.context.bug.official_tags)
        links = []
        for tag in self.context.bug.tags:
            if tag in target_official_tags:
                links.append((tag, '%s?field.tag=%s' % (
                    canonical_url(self.context.target, view_name='+bugs',
                        force_local_path=True), urllib.quote(tag))))
        return links

    @property
    def unofficial_tags(self):
        """The list of unofficial tags for this bug."""
        target_official_tags = set(self.context.bug.official_tags)
        links = []
        for tag in self.context.bug.tags:
            if tag not in target_official_tags:
                links.append((tag, '%s?field.tag=%s' % (
                    canonical_url(self.context.target, view_name='+bugs',
                        force_local_path=True), urllib.quote(tag))))
        return links

    @property
    def available_official_tags_js(self):
        """Return the list of available official tags for the bug as JSON.

        The list comprises of the official tags for all targets for which the
        bug has a task. It is returned as Javascript snippet, to be embedded
        in the bug page.
        """
        # Unwrap the security proxy. - official_tags is a security proxy
        # wrapped list.
        available_tags = list(self.context.bug.official_tags)
        return 'var available_official_tags = %s;' % dumps(available_tags)

    @property
    def user_is_admin(self):
        """Is the user a Launchpad admin?"""
        return check_permission('launchpad.Admin', self.context)

    @property
    def bug_description_html(self):
        """The bug's description as HTML."""
        bug = self.context.bug
        description = IBug['description']
        title = "Bug Description"
        edit_url = canonical_url(self.context, view_name='+edit')
        return TextAreaEditorWidget(
            bug, description, title, edit_url=edit_url)

    @property
    def bug_heat_html(self):
        """HTML representation of the bug heat."""
        return (
            '<span><a href="/+help-bugs/bug-heat.html" target="help" '
            'class="sprite flame">%d</a></span>' % self.context.bug.heat)


class BugTaskBatchedCommentsAndActivityView(BugTaskView):
    """A view for displaying batches of bug comments and activity."""

    # We never truncate comments in this view; there would be no point.
    visible_comments_truncated_for_display = False

    @property
    def offset(self):
        try:
            return int(self.request.form_ng.getOne('offset'))
        except TypeError:
            # We return visible_initial_comments + 1, since otherwise we'd
            # end up repeating comments that are already visible on the
            # page. The +1 accounts for the fact that bug comments are
            # essentially indexed from 1 due to comment 0 being the
            # initial bug description.
            return self.visible_initial_comments + 1

    @property
    def batch_size(self):
        try:
            return int(self.request.form_ng.getOne('batch_size'))
        except TypeError:
            return config.malone.comments_list_default_batch_size

    @property
    def next_batch_url(self):
        return "%s?offset=%s&batch_size=%s" % (
            canonical_url(self.context, view_name='+batched-comments'),
            self.next_offset, self.batch_size)

    @property
    def next_offset(self):
        return self.offset + self.batch_size

    @property
    def _event_groups(self):
        """See `BugTaskView`."""
        batch_size = self.batch_size
        if (batch_size > (self.total_comments) or
            not self.has_more_comments_and_activity):
            # If the batch size is big enough to encompass all the
            # remaining comments and activity, trim it so that we don't
            # re-show things.
            if self.offset == self.visible_initial_comments + 1:
                offset_to_remove = self.visible_initial_comments
            else:
                offset_to_remove = self.offset
            batch_size = (
                self.total_comments - self.visible_recent_comments -
                # This last bit is to make sure that _getEventGroups()
                # doesn't accidentally inflate the batch size later on.
                offset_to_remove)
        return self._getEventGroups(
            batch_size=batch_size, offset=self.offset)

    @cachedproperty
    def has_more_comments_and_activity(self):
        """Return True if there are more camments and activity to load."""
        return (
            self.next_offset < (self.total_comments + self.total_activity))


def get_prefix(bugtask):
    """Return a prefix that can be used for this form.

    The prefix is constructed using the name of the bugtask's target so as
    to ensure that it's unique within the context of a bug. This is needed
    in order to included multiple edit forms on the bug page, while still
    keeping the field ids unique.
    """
    parts = []
    parts.append(bugtask.pillar.name)

    series = bugtask.productseries or bugtask.distroseries
    if series:
        parts.append(series.name)

    if bugtask.sourcepackagename is not None:
        parts.append(bugtask.sourcepackagename.name)

    return '_'.join(parts)


def get_assignee_vocabulary_info(context):
    """The vocabulary of bug task assignees the current user can set."""
    if context.userCanSetAnyAssignee(getUtility(ILaunchBag).user):
        vocab_name = 'ValidAssignee'
    else:
        vocab_name = 'AllUserTeamsParticipation'
    vocab = vocabulary_registry.get(None, vocab_name)
    return vocab_name, vocab


class BugTaskBugWatchMixin:
    """A mixin to be used where a BugTask view displays BugWatch data."""

    @cachedproperty
    def bug_watch_error_message(self):
        """Return a browser-useable error message for a bug watch."""
        if not self.context.bugwatch:
            return None

        bug_watch = self.context.bugwatch
        if not bug_watch.last_error_type:
            return None

        error_message_mapping = {
            BugWatchActivityStatus.BUG_NOT_FOUND: "%(bugtracker)s bug #"
                "%(bug)s appears not to exist. Check that the bug "
                "number is correct.",
            BugWatchActivityStatus.CONNECTION_ERROR: "Launchpad couldn't "
                "connect to %(bugtracker)s.",
            BugWatchActivityStatus.INVALID_BUG_ID: "Bug ID %(bug)s isn't "
                "valid on %(bugtracker)s. Check that the bug ID is "
                "correct.",
            BugWatchActivityStatus.TIMEOUT: "Launchpad's connection to "
                "%(bugtracker)s timed out.",
            BugWatchActivityStatus.UNKNOWN: "Launchpad couldn't import bug "
                "#%(bug)s from " "%(bugtracker)s.",
            BugWatchActivityStatus.UNPARSABLE_BUG: "Launchpad couldn't "
                "extract a status from %(bug)s on %(bugtracker)s.",
            BugWatchActivityStatus.UNPARSABLE_BUG_TRACKER: "Launchpad "
                "couldn't determine the version of %(bugtrackertype)s "
                "running on %(bugtracker)s.",
            BugWatchActivityStatus.UNSUPPORTED_BUG_TRACKER: "Launchpad "
                "doesn't support importing bugs from %(bugtrackertype)s"
                " bug trackers.",
            BugWatchActivityStatus.PRIVATE_REMOTE_BUG: "The bug is marked as "
                "private on the remote bug tracker. Launchpad cannot import "
                "the status of private remote bugs.",
            }

        if bug_watch.last_error_type in error_message_mapping:
            message = error_message_mapping[bug_watch.last_error_type]
        else:
            message = bug_watch.last_error_type.description

        error_data = {
            'bug': bug_watch.remotebug,
            'bugtracker': bug_watch.bugtracker.title,
            'bugtrackertype': bug_watch.bugtracker.bugtrackertype.title}

        return {
            'message': message % error_data,
            'help_url': '%s#%s' % (
                canonical_url(bug_watch, view_name="+error-help"),
                bug_watch.last_error_type.name),
            }


class BugTaskPrivilegeMixin:

    @cachedproperty
    def user_has_privileges(self):
        """Is the user privileged? That is, an admin, pillar owner, driver
        or bug supervisor.

        If yes, return True, otherwise return False.
        """
        return self.context.userHasBugSupervisorPrivileges(self.user)


class BugTaskEditView(LaunchpadEditFormView, BugTaskBugWatchMixin,
                      BugTaskPrivilegeMixin):
    """The view class used for the task +editstatus page."""

    schema = IBugTask
    milestone_source = None
    user_is_subscribed = None
    edit_form = ViewPageTemplateFile('../templates/bugtask-edit-form.pt')

    _next_url_override = None

    # The field names that we use by default. This list will be mutated
    # depending on the current context and the permissions of the user viewing
    # the form.
    default_field_names = ['assignee', 'bugwatch', 'importance', 'milestone',
                           'status']
    custom_widget('target', BugTaskTargetWidget)
    custom_widget('sourcepackagename', BugTaskSourcePackageNameWidget)
    custom_widget('bugwatch', BugTaskBugWatchWidget)
    custom_widget('assignee', BugTaskAssigneeWidget)

    def initialize(self):
        # Initialize user_is_subscribed, if it hasn't already been set.
        if self.user_is_subscribed is None:
            self.user_is_subscribed = self.context.bug.isSubscribed(self.user)
        super(BugTaskEditView, self).initialize()

    page_title = 'Edit status'

    @property
    def show_target_widget(self):
        # Only non-series tasks can be retargetted.
        return not ISeriesBugTarget.providedBy(self.context.target)

    @property
    def show_sourcepackagename_widget(self):
        # SourcePackage tasks can have only their sourcepackagename changed.
        # Conjoinment means we can't rely on editing the
        # DistributionSourcePackage task for this :(
        return (IDistroSeries.providedBy(self.context.target) or
                ISourcePackage.providedBy(self.context.target))

    @cachedproperty
    def field_names(self):
        """Return the field names that can be edited by the user."""
        field_names = set(self.default_field_names)

        # The fields that we present to the users change based upon the
        # current context and the user's permissions, so we update field_names
        # with any fields that may need to be added.
        field_names.update(self.editable_field_names)

        # To help with caching, return an immutable object.
        return frozenset(field_names)

    @cachedproperty
    def editable_field_names(self):
        """Return the names of fields the user has permission to edit."""
        if self.context.pillar.official_malone:
            # Don't edit self.field_names directly, because it's shared by all
            # BugTaskEditView instances.
            editable_field_names = set(self.default_field_names)
            editable_field_names.discard('bugwatch')

            # XXX: Brad Bollenbach 2006-09-29 bug=63000: Permission checking
            # doesn't belong here!
            if not self.user_has_privileges:
                if 'milestone' in editable_field_names:
                    editable_field_names.remove("milestone")
                if 'importance' in editable_field_names:
                    editable_field_names.remove("importance")
        else:
            editable_field_names = set(('bugwatch', ))
            if self.context.bugwatch is None:
                editable_field_names.update(('status', 'assignee'))
                if ('importance' in self.default_field_names
                    and self.user_has_privileges):
                    editable_field_names.add('importance')
            else:
                bugtracker = self.context.bugwatch.bugtracker
                if bugtracker.bugtrackertype == BugTrackerType.EMAILADDRESS:
                    editable_field_names.add('status')
                    if ('importance' in self.default_field_names
                        and self.user_has_privileges):
                        editable_field_names.add('importance')

        if self.show_target_widget:
            editable_field_names.add('target')
        elif self.show_sourcepackagename_widget:
            editable_field_names.add('sourcepackagename')

        # To help with caching, return an immutable object.
        return frozenset(editable_field_names)

    @property
    def is_question(self):
        """Return True or False if this bug was converted into a question.

        Bugtasks cannot be edited if the bug was converted into a question.
        """
        return self.context.bug.getQuestionCreatedFromBug() is not None

    @property
    def next_url(self):
        """See `LaunchpadFormView`."""
        if self._next_url_override is None:
            return canonical_url(self.context)
        else:
            return self._next_url_override

    @property
    def initial_values(self):
        """See `LaunchpadFormView.`"""
        field_values = {}
        for name in self.field_names:
            field_values[name] = getattr(self.context, name)

        return field_values

    @property
    def prefix(self):
        """Return a prefix that can be used for this form.

        The prefix is constructed using the name of the bugtask's target so as
        to ensure that it's unique within the context of a bug. This is needed
        in order to included multiple edit forms on the bug page, while still
        keeping the field ids unique.
        """
        return get_prefix(self.context)

    def setUpFields(self):
        """Sets up the fields for the bug task edit form.

        See `LaunchpadFormView`.
        """
        super(BugTaskEditView, self).setUpFields()
        read_only_field_names = self._getReadOnlyFieldNames()

        if 'target' in self.editable_field_names:
            self.form_fields = self.form_fields.omit('target')
            target_field = copy_field(IBugTask['target'], readonly=False)
            self.form_fields += formlib.form.Fields(target_field)

        # The status field is a special case because we alter the vocabulary
        # it uses based on the permissions of the user viewing form.
        if 'status' in self.editable_field_names:
            if self.user is None:
                status_noshow = set(BugTaskStatus.items)
            else:
                status_noshow = set((
                    BugTaskStatus.UNKNOWN, BugTaskStatus.EXPIRED))
                status_noshow.update(
                    status for status in BugTaskStatus.items
                    if not self.context.canTransitionToStatus(
                        status, self.user))

            if self.context.status in status_noshow:
                # The user has to be able to see the current value.
                status_noshow.remove(self.context.status)

            # We shouldn't have to build our vocabulary out of (item.title,
            # item) tuples -- iterating over an EnumeratedType gives us
            # ITokenizedTerms that we could use. However, the terms generated
            # by EnumeratedType have their name as the token and here we need
            # the title as the token for backwards compatibility.
            status_items = [
                (item.title, item) for item in BugTaskStatus.items
                if item not in status_noshow]
            status_field = Choice(
                __name__='status', title=self.schema['status'].title,
                vocabulary=SimpleVocabulary.fromItems(status_items))

            self.form_fields = self.form_fields.omit('status')
            self.form_fields += formlib.form.Fields(status_field)

        # If we have a milestone vocabulary already, create a new field
        # to use it, instead of creating a new one.
        if self.milestone_source is not None:
            milestone_source = self.milestone_source
            milestone_field = Choice(
                __name__='milestone',
                title=self.schema['milestone'].title,
                source=milestone_source, required=False)
        else:
            milestone_field = copy_field(
                IBugTask['milestone'], readonly=False)

        self.form_fields = self.form_fields.omit('milestone')
        self.form_fields += formlib.form.Fields(milestone_field)

        for field in read_only_field_names:
            self.form_fields[field].for_display = True

        # In cases where the status or importance fields are read only we give
        # them a custom widget so that they are rendered correctly.
        for field in ['status', 'importance']:
            if field in read_only_field_names:
                self.form_fields[field].custom_widget = CustomWidgetFactory(
                    DBItemDisplayWidget)

        if 'importance' not in read_only_field_names:
            # Users shouldn't be able to set a bugtask's importance to
            # `UNKNOWN`, only bug watches do that.
            importance_vocab_items = [
                item for item in BugTaskImportance.items.items
                if item != BugTaskImportance.UNKNOWN]
            self.form_fields = self.form_fields.omit('importance')
            self.form_fields += formlib.form.Fields(
                Choice(__name__='importance',
                       title=_('Importance'),
                       values=importance_vocab_items,
                       default=BugTaskImportance.UNDECIDED))

        if self.context.pillar.official_malone:
            self.form_fields = self.form_fields.omit('bugwatch')

        elif (self.context.bugwatch is not None and
            self.form_fields.get('assignee', False)):
            self.form_fields['assignee'].custom_widget = CustomWidgetFactory(
                AssigneeDisplayWidget)

        if (self.context.bugwatch is None and
            self.form_fields.get('assignee', False)):
            # Make the assignee field editable
            self.form_fields = self.form_fields.omit('assignee')
            vocabulary, ignored = get_assignee_vocabulary_info(self.context)
            self.form_fields += formlib.form.Fields(PersonChoice(
                __name__='assignee', title=_('Assigned to'), required=False,
                vocabulary=vocabulary, readonly=False))
            self.form_fields['assignee'].custom_widget = CustomWidgetFactory(
                BugTaskAssigneeWidget)

    def _getReadOnlyFieldNames(self):
        """Return the names of fields that will be rendered read only."""
        if self.context.pillar.official_malone:
            read_only_field_names = []

            if not self.user_has_privileges:
                read_only_field_names.append("milestone")
                read_only_field_names.append("importance")
        else:
            editable_field_names = self.editable_field_names
            read_only_field_names = [
                field_name for field_name in self.field_names
                if field_name not in editable_field_names]

        return read_only_field_names

    def validate(self, data):
        if self.show_sourcepackagename_widget and 'sourcepackagename' in data:
            data['target'] = self.context.distroseries
            spn = data.get('sourcepackagename')
            if spn:
                data['target'] = data['target'].getSourcePackage(spn)
            del data['sourcepackagename']
            error_field = 'sourcepackagename'
        else:
            error_field = 'target'

        new_target = data.get('target')
        if new_target and new_target != self.context.target:
            try:
                # The validity of the source package has already been checked
                # by the bug target widget.
                self.context.validateTransitionToTarget(
                    new_target, check_source_package=False)
            except IllegalTarget as e:
                self.setFieldError(error_field, e[0])

    def updateContextFromData(self, data, context=None):
        """Updates the context object using the submitted form data.

        This method overrides that of LaunchpadEditFormView because of the
        fairly involved thread of logic behind updating some BugTask
        attributes, in particular the status, assignee and bugwatch fields.
        """
        if context is None:
            context = self.context
        bugtask = context

        if self.request.form.get('subscribe', False):
            bugtask.bug.subscribe(self.user, self.user)
            self.request.response.addNotification(
                "You have subscribed to this bug report.")

        # Save the field names we extract from the form in a separate
        # list, because we modify this list of names later if the
        # bugtask is reassigned to a different product.
        field_names = data.keys()
        new_values = data.copy()
        data_to_apply = data.copy()

        bugtask_before_modification = Snapshot(
            bugtask, providing=providedBy(bugtask))

        # If the user is reassigning an upstream task to a different
        # product, we'll clear out the milestone value, to avoid
        # violating DB constraints that ensure an upstream task can't
        # be assigned to a milestone on a different product.
        # This is also done by transitionToTarget, but do it here so we
        # can display notifications and remove the milestone from the
        # submitted data.
        milestone_cleared = None
        milestone_ignored = False
        missing = object()
        new_target = new_values.pop("target", missing)
        if (new_target is not missing and
            bugtask.target.pillar != new_target.pillar):
            # We clear the milestone value if one was already set. We ignore
            # the milestone value if it was currently None, and the user tried
            # to set a milestone value while also changing the product. This
            # allows us to provide slightly clearer feedback messages.
            if bugtask.milestone:
                milestone_cleared = bugtask.milestone
            elif new_values.get('milestone') is not None:
                milestone_ignored = True

            # Regardless of the user's permission, the milestone
            # must be cleared because the milestone is unique to a product.
            removeSecurityProxy(bugtask).milestone = None
            # Remove the "milestone" field from the list of fields
            # whose changes we want to apply, because we don't want
            # the form machinery to try and set this value back to
            # what it was!
            data_to_apply.pop('milestone', None)

        # We special case setting target, status and assignee, because
        # there's a workflow associated with changes to these fields.
        for manual_field in ('target', 'status', 'assignee'):
            data_to_apply.pop(manual_field, None)

        # We grab the comment_on_change field before we update bugtask so as
        # to avoid problems accessing the field if the user has changed the
        # product of the BugTask.
        comment_on_change = self.request.form.get(
            "%s.comment_on_change" % self.prefix)

        changed = formlib.form.applyChanges(
            bugtask, self.form_fields, data_to_apply, self.adapters)

        # Set the "changed" flag properly, just in case status and/or assignee
        # happen to be the only values that changed. We explicitly verify that
        # we got a new status and/or assignee, because the form is not always
        # guaranteed to pass all the values. For example: bugtasks linked to a
        # bug watch don't allow editing the form, and the value is missing
        # from the form.
        # The new target has already been validated so don't do it again.
        if new_target is not missing and bugtask.target != new_target:
            changed = True
            bugtask.transitionToTarget(new_target, self.user, validate=False)

        # Now that we've updated the bugtask we can add messages about
        # milestone changes, if there were any.
        if milestone_cleared:
            self.request.response.addWarningNotification(
                "The %s milestone setting has been removed because "
                "you reassigned the bug to %s." % (
                    milestone_cleared.displayname,
                    bugtask.bugtargetdisplayname))
        elif milestone_ignored:
            self.request.response.addWarningNotification(
                "The milestone setting was ignored because "
                "you reassigned the bug to %s." %
                bugtask.bugtargetdisplayname)

        if comment_on_change:
            bugtask.bug.newMessage(
                owner=getUtility(ILaunchBag).user,
                subject=bugtask.bug.followup_subject(),
                content=comment_on_change)

        new_status = new_values.pop("status", missing)
        new_assignee = new_values.pop("assignee", missing)
        if new_status is not missing and bugtask.status != new_status:
            changed = True
            try:
                bugtask.transitionToStatus(new_status, self.user)
            except UserCannotEditBugTaskStatus:
                # We need to roll back the transaction at this point,
                # since other changes may have been made.
                transaction.abort()
                self.setFieldError(
                    'status',
                    "Only the Bug Supervisor for %s can set the bug's "
                    "status to %s" %
                    (bugtask.target.displayname, new_status.title))
                return

        if new_assignee is not missing and bugtask.assignee != new_assignee:
            if new_assignee is not None and new_assignee != self.user:
                is_contributor = new_assignee.isBugContributorInTarget(
                    user=self.user, target=bugtask.pillar)
                if not is_contributor:
                    # If we have a new assignee who isn't a bug
                    # contributor in this pillar, we display a warning
                    # to the user, in case they made a mistake.
                    self.request.response.addWarningNotification(
                        structured(
                        """<a href="%s">%s</a>
                        did not previously have any assigned bugs in
                        <a href="%s">%s</a>.
                        <br /><br />
                        If this bug was assigned by mistake,
                        you may <a href="%s/+editstatus"
                        >change the assignment</a>.""",
                        canonical_url(new_assignee),
                        new_assignee.displayname,
                        canonical_url(bugtask.pillar),
                        bugtask.pillar.title,
                        canonical_url(bugtask)))
            changed = True
            bugtask.transitionToAssignee(new_assignee)

        if bugtask_before_modification.bugwatch != bugtask.bugwatch:
            bug_importer = getUtility(ILaunchpadCelebrities).bug_importer
            if bugtask.bugwatch is None:
                # Reset the status and importance to the default values,
                # since Unknown isn't selectable in the UI.
                bugtask.transitionToStatus(
                    IBugTask['status'].default, bug_importer)
                bugtask.transitionToImportance(
                    IBugTask['importance'].default, bug_importer)
            else:
                #XXX: Bjorn Tillenius 2006-03-01:
                #     Reset the bug task's status information. The right
                #     thing would be to convert the bug watch's status to a
                #     Launchpad status, but it's not trivial to do at the
                #     moment. I will fix this later.
                bugtask.transitionToStatus(
                    BugTaskStatus.UNKNOWN,
                    bug_importer)
                bugtask.transitionToImportance(
                    BugTaskImportance.UNKNOWN,
                    bug_importer)
                bugtask.transitionToAssignee(None)

        if changed:
            notify(
                ObjectModifiedEvent(
                    object=bugtask,
                    object_before_modification=bugtask_before_modification,
                    edited_fields=field_names))

            # We clear the known views cache because the bug may not be
            # viewable anymore by the current user. If the bug is not
            # viewable, then we redirect to the current bugtask's pillar's
            # bug index page with a message.
            get_property_cache(bugtask.bug)._known_viewers = set()
            if not bugtask.bug.userCanView(self.user):
                self.request.response.addWarningNotification(
                    "The bug you have just updated is now a private bug for "
                    "%s. You do not have permission to view such bugs."
                    % bugtask.pillar.displayname)
                self._next_url_override = canonical_url(
                    new_target.pillar, rootsite='bugs')

        if (bugtask.sourcepackagename and (
            self.widgets.get('target') or
            self.widgets.get('sourcepackagename'))):
            real_package_name = bugtask.sourcepackagename.name

            # We get entered_package_name directly from the form here, since
            # validating the sourcepackagename field mutates its value in to
            # the one already in real_package_name, which makes our comparison
            # of the two below useless.
            if self.widgets.get('sourcepackagename'):
                field_name = self.widgets['sourcepackagename'].name
            else:
                field_name = self.widgets['target'].package_widget.name
            entered_package_name = self.request.form.get(field_name)

            if real_package_name != entered_package_name:
                # The user entered a binary package name which got
                # mapped to a source package.
                self.request.response.addNotification(
                    "'%(entered_package)s' is a binary package. This bug has"
                    " been assigned to its source package '%(real_package)s'"
                    " instead." %
                    {'entered_package': entered_package_name,
                     'real_package': real_package_name})

    @action('Save Changes', name='save')
    def save_action(self, action, data):
        """Update the bugtask with the form data."""
        self.updateContextFromData(data)


class BugTaskDeletionView(ReturnToReferrerMixin, LaunchpadFormView):
    """Used to delete a bugtask."""

    schema = IBugTask
    field_names = []

    label = 'Remove bug task'
    page_title = label

    @property
    def next_url(self):
        """Return the next URL to call when this call completes."""
        if not self.request.is_ajax:
            return self._next_url or self._return_url
        return None

    @action('Delete', name='delete_bugtask')
    def delete_bugtask_action(self, action, data):
        bugtask = self.context
        bug = bugtask.bug
        deleted_bugtask_url = canonical_url(self.context, rootsite='bugs')
        success_message = ("This bug no longer affects %s."
                    % bugtask.bugtargetdisplayname)
        error_message = None
        # We set the next_url here before the bugtask is deleted since later
        # the bugtask will not be available if required to construct the url.
        self._next_url = self._return_url

        try:
            bugtask.delete()
            self.request.response.addNotification(success_message)
        except CannotDeleteBugtask as e:
            error_message = str(e)
            self.request.response.addErrorNotification(error_message)
        if self.request.is_ajax:
            if error_message:
                self.request.response.setHeader('Content-type',
                    'application/json')
                return dumps(None)
            launchbag = getUtility(ILaunchBag)
            launchbag.add(bug.default_bugtask)
            # If we are deleting the current highlighted bugtask via ajax,
            # we must force a redirect to the new default bugtask to ensure
            # all URLs and other client cache content is correctly refreshed.
            # We can't do the redirect here since the XHR caller won't see it
            # so we return the URL to go to and let the caller do it.
            if self._return_url == deleted_bugtask_url:
                next_url = canonical_url(
                    bug.default_bugtask, rootsite='bugs')
                self.request.response.setHeader('Content-type',
                    'application/json')
                return dumps(dict(bugtask_url=next_url))
            # No redirect required so return the new bugtask table HTML.
            view = getMultiAdapter(
                (bug, self.request),
                name='+bugtasks-and-nominations-table')
            view.initialize()
            return view.render()


def bugtask_sort_key(bugtask):
    """Return a sort key for displaying a set of tasks for a single bug.

    Designed to make sense when bugtargetdisplayname is shown.
    """
    if IDistribution.providedBy(bugtask.target):
        return (
            None, bugtask.target.displayname, None, None, None)
    elif IDistroSeries.providedBy(bugtask.target):
        return (
            None, bugtask.target.distribution.displayname,
            bugtask.target.name, None, None)
    elif IDistributionSourcePackage.providedBy(bugtask.target):
        return (
            bugtask.target.sourcepackagename.name,
            bugtask.target.distribution.displayname, None, None, None)
    elif ISourcePackage.providedBy(bugtask.target):
        return (
            bugtask.target.sourcepackagename.name,
            bugtask.target.distribution.displayname,
            bugtask.target.distroseries.name, None, None)
    elif IProduct.providedBy(bugtask.target):
        return (None, None, None, bugtask.target.displayname, None)
    elif IProductSeries.providedBy(bugtask.target):
        return (
            None, None, None, bugtask.target.product.displayname,
            bugtask.target.name)
    raise AssertionError("No sort key for %r" % bugtask.target)


class BugTasksNominationsView(LaunchpadView):
    """Browser class for rendering the bug nominations portlet."""

    def __init__(self, context, request):
        """Ensure we always have a bug context."""
        LaunchpadView.__init__(self, IBug(context), request)

    def displayAlsoAffectsLinks(self):
        """Return True if the Also Affects links should be displayed."""
        # Hide the links when the bug is viewed in a CVE context
        return self.request.getNearest(ICveSet) == (None, None)

    @cachedproperty
    def current_user_affected_status(self):
        """Is the current user marked as affected by this bug?"""
        return self.context.isUserAffected(self.user)

    @property
    def current_user_affected_js_status(self):
        """A javascript literal indicating if the user is affected."""
        affected = self.current_user_affected_status
        if affected is None:
            return 'null'
        elif affected:
            return 'true'
        else:
            return 'false'

    @cachedproperty
    def other_users_affected_count(self):
        """The number of other users affected by this bug.
        """
        if getFeatureFlag('bugs.affected_count_includes_dupes.disabled'):
            if self.current_user_affected_status:
                return self.context.users_affected_count - 1
            else:
                return self.context.users_affected_count
        else:
            return self.context.other_users_affected_count_with_dupes

    @cachedproperty
    def total_users_affected_count(self):
        """The number of affected users, typically across all users.

        Counting across duplicates may be disabled at run time.
        """
        if getFeatureFlag('bugs.affected_count_includes_dupes.disabled'):
            return self.context.users_affected_count
        else:
            return self.context.users_affected_count_with_dupes

    @cachedproperty
    def affected_statement(self):
        """The default "this bug affects" statement to show.

        The outputs of this method should be mirrored in
        MeTooChoiceSource._getSourceNames() (Javascript).
        """
        me_affected = self.current_user_affected_status
        other_affected = self.other_users_affected_count
        if me_affected is None:
            if other_affected == 1:
                return "This bug affects 1 person. Does this bug affect you?"
            elif other_affected > 1:
                return (
                    "This bug affects %d people. Does this bug "
                    "affect you?" % other_affected)
            else:
                return "Does this bug affect you?"
        elif me_affected is True:
            if other_affected == 0:
                return "This bug affects you"
            elif other_affected == 1:
                return "This bug affects you and 1 other person"
            else:
                return "This bug affects you and %d other people" % (
                    other_affected)
        else:
            if other_affected == 0:
                return "This bug doesn't affect you"
            elif other_affected == 1:
                return "This bug affects 1 person, but not you"
            elif other_affected > 1:
                return "This bug affects %d people, but not you" % (
                    other_affected)

    @cachedproperty
    def anon_affected_statement(self):
        """The "this bug affects" statement to show to anonymous users.

        The outputs of this method should be mirrored in
        MeTooChoiceSource._getSourceNames() (Javascript).
        """
        affected = self.total_users_affected_count
        if affected == 1:
            return "This bug affects 1 person"
        elif affected > 1:
            return "This bug affects %d people" % affected
        else:
            return None

    def canAddProjectTask(self):
        return can_add_project_task_to_bug(self.context)

    def canAddPackageTask(self):
        return can_add_package_task_to_bug(self.context)

    @property
    def current_bugtask(self):
        """Return the current `IBugTask`.

        'current' is determined by simply looking in the ILaunchBag utility.
        """
        return getUtility(ILaunchBag).bugtask


def can_add_project_task_to_bug(bug):
    """Can a new bug task on a project be added to this bug?

    If a bug has any bug tasks already, were it to be Proprietary or
    Embargoed, it cannot be marked as also affecting any other
    project, so return False.
    """
    if bug.information_type not in PROPRIETARY_INFORMATION_TYPES:
        return True
    return len(bug.bugtasks) == 0


def can_add_package_task_to_bug(bug):
    """Can a new bug task on a src pkg be added to this bug?

    If a bug has any existing bug tasks on a project, were it to
    be Proprietary or Embargoed, then it cannot be marked as
    affecting a package, so return False.

    A task on a given package may still be illegal to add, but
    this will be caught when bug.addTask() is attempted.
    """
    if bug.information_type not in PROPRIETARY_INFORMATION_TYPES:
        return True
    for pillar in bug.affected_pillars:
        if IProduct.providedBy(pillar):
            return False
    return True


class BugTasksTableView(LaunchpadView):
    """Browser class for rendering the bugtasks table."""

    target_releases = None

    def __init__(self, context, request):
        """Ensure we always have a bug context."""
        LaunchpadView.__init__(self, IBug(context), request)

    def initialize(self):
        """Cache the list of bugtasks and set up the release mapping."""
        # Cache some values, so that we don't have to recalculate them
        # for each bug task.
        # Note: even though the publisher queries all the bugtasks and we in
        # theory could just reuse that already loaded list here, it's better
        # to do another query to only load the bug tasks for active projects
        # so we don't incur the cost of setting up data structures for tasks
        # we will not be showing in the listing.
        bugtask_set = getUtility(IBugTaskSet)
        search_params = BugTaskSearchParams(user=self.user, bug=self.context)
        self.bugtasks = list(bugtask_set.search(search_params))
        self.many_bugtasks = len(self.bugtasks) >= 10
        self.user_is_subscribed = self.context.isSubscribed(self.user)

        # If we have made it to here then the logged in user can see the
        # bug, hence they can see any assignees.
        # The security adaptor will do the job also but we don't want or need
        # the expense of running several complex SQL queries.
        authorised_people = [task.assignee for task in self.bugtasks
                             if task.assignee is not None]
        precache_permission_for_objects(
            self.request, 'launchpad.LimitedView', authorised_people)

        distro_packages = defaultdict(list)
        distro_series_packages = defaultdict(list)
        for bugtask in self.bugtasks:
            target = bugtask.target
            if IDistributionSourcePackage.providedBy(target):
                distro_packages[target.distribution].append(
                    target.sourcepackagename)
            if ISourcePackage.providedBy(target):
                distro_series_packages[target.distroseries].append(
                    target.sourcepackagename)
        distro_set = getUtility(IDistributionSet)
        self.target_releases = dict(distro_set.getCurrentSourceReleases(
            distro_packages))
        distro_series_set = getUtility(IDistroSeriesSet)
        self.target_releases.update(
            distro_series_set.getCurrentSourceReleases(
                distro_series_packages))
        ids = set()
        for release_person_ids in map(attrgetter('creatorID', 'maintainerID'),
            self.target_releases.values()):
            ids.update(release_person_ids)
        ids.discard(None)
        if ids:
            list(getUtility(IPersonSet).getPrecachedPersonsFromIDs(ids))

    @cachedproperty
    def caching_milestone_vocabulary(self):
        return BugTaskMilestoneVocabulary(milestones=self.milestones)

    @cachedproperty
    def milestones(self):
        if self.bugtasks:
            bugtask_set = getUtility(IBugTaskSet)
            return list(
                bugtask_set.getBugTaskTargetMilestones(self.bugtasks))
        else:
            return []

    def getTargetLinkTitle(self, target):
        """Return text to put as the title for the link to the target."""
        if not (IDistributionSourcePackage.providedBy(target) or
                ISourcePackage.providedBy(target)):
            return None
        current_release = self.target_releases.get(target)
        if current_release is None:
            return "No current release for this source package in %s" % (
                target.distribution.displayname)
        uploader = current_release.creator
        maintainer = current_release.maintainer
        return (
            "Latest release: %(version)s, uploaded to %(component)s"
            " on %(date_uploaded)s by %(uploader)s,"
            " maintained by %(maintainer)s" % dict(
                version=current_release.version,
                component=current_release.component.name,
                date_uploaded=current_release.dateuploaded,
                uploader=uploader.unique_displayname,
                maintainer=maintainer.unique_displayname,
                ))

    def _getTableRowView(self, context, is_converted_to_question,
                         is_conjoined_slave):
        """Get the view for the context, and initialize it.

        The view's is_conjoined_slave and is_converted_to_question
        attributes are set, as well as the edit view.
        """
        view = getMultiAdapter(
            (context, self.request),
            name='+bugtasks-and-nominations-table-row')
        view.is_converted_to_question = is_converted_to_question
        view.is_conjoined_slave = is_conjoined_slave

        view.edit_view = getMultiAdapter(
            (context, self.request), name='+edit-form')
        view.milestone_source = self.caching_milestone_vocabulary
        if IBugTask.providedBy(context):
            view.target_link_title = self.getTargetLinkTitle(context.target)
            view.edit_view.milestone_source = (
                BugTaskMilestoneVocabulary(context, self.milestones))
        view.edit_view.user_is_subscribed = self.user_is_subscribed
        # Hint to optimize when there are many bugtasks.
        view.many_bugtasks = self.many_bugtasks
        return view

    def getBugTaskAndNominationViews(self):
        """Return the IBugTasks and IBugNominations views for this bug.

        Returns a list of views, sorted by the context's targetname,
        with upstream tasks sorted before distribution tasks, and
        nominations sorted after tasks. Approved nominations are not
        included in the returned results.
        """
        bug = self.context
        all_bugtasks = list(sorted(self.bugtasks, key=bugtask_sort_key))

        # Cache whether the bug was converted to a question, since
        # bug.getQuestionCreatedFromBug issues a db query each time it
        # is called.
        is_converted_to_question = bug.getQuestionCreatedFromBug() is not None
        # Insert bug nominations in between the appropriate tasks.
        bugtask_and_nomination_views = []
        # Having getNominations() get the list of bug nominations each
        # time it gets called in the for loop is expensive. Get the
        # nominations here, so we can pass it to getNominations() later
        # on.
        nominations = list(bug.getNominations())
        # Eager load validity for all the persons we know of that will be
        # displayed.
        ids = set(map(attrgetter('ownerID'), nominations))
        ids.discard(None)
        if ids:
            list(getUtility(IPersonSet).getPrecachedPersonsFromIDs(
                ids, need_validity=True))

        # Build a cache we can pass on to getConjoinedMaster(), so that
        # it doesn't have to iterate over all the bug tasks in each loop
        # iteration.
        bugtasks_by_package = bug.getBugTasksByPackageName(all_bugtasks)

        latest_parent = None

        for bugtask in all_bugtasks:
            # Series bug targets only display the series name, so they
            # must always be preceded by their parent context. Normally
            # the parent will have a task, but if not we need to show a
            # fake one.
            if ISeriesBugTarget.providedBy(bugtask.target):
                parent = bugtask.target.bugtarget_parent
            else:
                latest_parent = parent = bugtask.target

            if parent != latest_parent:
                latest_parent = parent
                bugtask_and_nomination_views.append(
                    getMultiAdapter(
                        (parent, self.request),
                        name='+bugtasks-and-nominations-table-row'))

            conjoined_master = bugtask.getConjoinedMaster(
                all_bugtasks, bugtasks_by_package)
            view = self._getTableRowView(
                bugtask, is_converted_to_question,
                conjoined_master is not None)
            bugtask_and_nomination_views.append(view)
            target = bugtask.product or bugtask.distribution
            if not target:
                continue

            target_nominations = bug.getNominations(
                target, nominations=nominations)
            bugtask_and_nomination_views.extend(
                self._getTableRowView(
                    nomination, is_converted_to_question, False)
                for nomination in target_nominations
                if nomination.status != BugNominationStatus.APPROVED)

        return bugtask_and_nomination_views


class BugTaskTableRowView(LaunchpadView, BugTaskBugWatchMixin,
                          BugTaskPrivilegeMixin):
    """Browser class for rendering a bugtask row on the bug page."""

    is_conjoined_slave = None
    is_converted_to_question = None
    target_link_title = None
    many_bugtasks = False

    template = ViewPageTemplateFile(
        '../templates/bugtask-tasks-and-nominations-table-row.pt')

    def __init__(self, context, request):
        super(BugTaskTableRowView, self).__init__(context, request)
        self.milestone_source = BugTaskMilestoneVocabulary

    @cachedproperty
    def api_request(self):
        return IWebServiceClientRequest(self.request)

    def initialize(self):
        super(BugTaskTableRowView, self).initialize()
        link = canonical_url(self.context)
        task_link = edit_link = canonical_url(
                                    self.context, view_name='+editstatus')
        delete_link = canonical_url(self.context, view_name='+delete')
        can_edit = check_permission('launchpad.Edit', self.context)
        bugtask_id = self.context.id
        launchbag = getUtility(ILaunchBag)
        is_primary = self.context.id == launchbag.bugtask.id
        self.data = dict(
            # Looking at many_bugtasks is an important optimization.  With
            # 150+ bugtasks, it can save three or four seconds of rendering
            # time.
            expandable=(not self.many_bugtasks and self.canSeeTaskDetails()),
            indent_task=ISeriesBugTarget.providedBy(self.context.target),
            is_conjoined_slave=self.is_conjoined_slave,
            task_link=task_link,
            edit_link=edit_link,
            can_edit=can_edit,
            link=link,
            id=bugtask_id,
            row_id='tasksummary%d' % bugtask_id,
            form_row_id='task%d' % bugtask_id,
            row_css_class='highlight' if is_primary else None,
            target_link=canonical_url(self.context.target),
            target_link_title=self.target_link_title,
            user_can_delete=self.user_can_delete_bugtask,
            delete_link=delete_link,
            user_can_edit_importance=self.user_has_privileges,
            importance_css_class='importance' + self.context.importance.name,
            importance_title=self.context.importance.title,
            # We always look up all milestones, so there's no harm
            # using len on the list here and avoid the COUNT query.
            target_has_milestones=len(self._visible_milestones) > 0,
            user_can_edit_status=self.user_can_edit_status,
            )

        if not self.many_bugtasks:
            cache = IJSONRequestCache(self.request)
            bugtask_data = cache.objects.get('bugtask_data', None)
            if bugtask_data is None:
                bugtask_data = dict()
                cache.objects['bugtask_data'] = bugtask_data
            bugtask_data[bugtask_id] = self.bugtask_config()

    def canSeeTaskDetails(self):
        """Whether someone can see a task's status details.

        Return True if this is not a conjoined task, and the bug is
        not a duplicate, and a question was not made from this report.
        It is independent of whether they can *change* the status; you
        need to expand the details to see any milestone set.
        """
        assert self.is_conjoined_slave is not None, (
            'is_conjoined_slave should be set before rendering the page.')
        assert self.is_converted_to_question is not None, (
            'is_converted_to_question should be set before rendering the'
            ' page.')
        return (self.displayEditForm() and
                not self.is_conjoined_slave and
                self.context.bug.duplicateof is None and
                not self.is_converted_to_question)

    def _getSeriesTargetNameHelper(self, bugtask):
        """Return the short name of bugtask's targeted series."""
        series = bugtask.distroseries or bugtask.productseries
        if not series:
            return None
        return series.name.capitalize()

    def getSeriesTargetName(self):
        """Get the series to which this task is targeted."""
        return self._getSeriesTargetNameHelper(self.context)

    def getConjoinedMasterName(self):
        """Get the conjoined master's name for displaying."""
        return self._getSeriesTargetNameHelper(self.context.conjoined_master)

    @property
    def bugtask_icon(self):
        """Which icon should be shown for the task, if any?"""
        return getAdapter(self.context, IPathAdapter, 'image').sprite_css()

    def displayEditForm(self):
        """Return true if the BugTask edit form should be shown."""
        # Hide the edit form when the bug is viewed in a CVE context
        return self.request.getNearest(ICveSet) == (None, None)

    @property
    def status_widget_items(self):
        """The available status items as JSON."""
        if self.user is not None:
            # We shouldn't have to build our vocabulary out of (item.title,
            # item) tuples -- iterating over an EnumeratedType gives us
            # ITokenizedTerms that we could use. However, the terms generated
            # by EnumeratedType have their name as the token and here we need
            # the title as the token for backwards compatibility.
            status_items = [
                (item.title, item) for item in BugTaskStatus.items
                if item not in (BugTaskStatus.UNKNOWN,
                                BugTaskStatus.EXPIRED)]

            disabled_items = [status for status in BugTaskStatus.items
                if not self.context.canTransitionToStatus(status, self.user)]

            items = vocabulary_to_choice_edit_items(
                SimpleVocabulary.fromItems(status_items),
                include_description=True,
                css_class_prefix='status',
                disabled_items=disabled_items)
        else:
            items = '[]'

        return items

    @property
    def importance_widget_items(self):
        """The available status items as JSON."""
        if self.user is not None:
            # We shouldn't have to build our vocabulary out of (item.title,
            # item) tuples -- iterating over an EnumeratedType gives us
            # ITokenizedTerms that we could use. However, the terms generated
            # by EnumeratedType have their name as the token and here we need
            # the title as the token for backwards compatibility.
            importance_items = [
                (item.title, item) for item in BugTaskImportance.items
                if item != BugTaskImportance.UNKNOWN]

            items = vocabulary_to_choice_edit_items(
                SimpleVocabulary.fromItems(importance_items),
                include_description=True,
                css_class_prefix='importance')
        else:
            items = '[]'

        return items

    @cachedproperty
    def _visible_milestones(self):
        """The visible milestones for this context."""
        return self.milestone_source.visible_milestones(self.context)

    @property
    def milestone_widget_items(self):
        """The available milestone items as JSON."""
        if self.user is not None:
            items = vocabulary_to_choice_edit_items(
                self._visible_milestones,
                value_fn=lambda item: canonical_url(
                    item, request=self.api_request))
            items.append({
                "name": "Remove milestone",
                "disabled": False,
                "value": None})
        else:
            items = '[]'

        return items

    def bugtask_canonical_url(self):
        """Return the canonical url for the bugtask."""
        return canonical_url(self.context)

    @cachedproperty
    def user_can_edit_importance(self):
        """Can the user edit the Importance field?

        If yes, return True, otherwise return False.
        """
        return self.user_can_edit_status and self.user_has_privileges

    @cachedproperty
    def user_can_edit_status(self):
        """Can the user edit the Status field?

        If yes, return True, otherwise return False.
        """
        bugtask = self.context
        edit_allowed = bugtask.pillar.official_malone or bugtask.bugwatch
        if bugtask.bugwatch:
            bugtracker = bugtask.bugwatch.bugtracker
            edit_allowed = (
                bugtracker.bugtrackertype == BugTrackerType.EMAILADDRESS)
        return edit_allowed

    @property
    def user_can_edit_assignee(self):
        """Can the user edit the Assignee field?

        If yes, return True, otherwise return False.
        """
        return self.user is not None

    @cachedproperty
    def user_can_delete_bugtask(self):
        """Can the user delete the bug task?

        If yes, return True, otherwise return False.
        """
        bugtask = self.context
        return (check_permission('launchpad.Delete', bugtask)
                and bugtask.canBeDeleted())

    @property
    def style_for_add_milestone(self):
        if self.context.milestone is None:
            return ''
        else:
            return 'hidden'

    @property
    def style_for_edit_milestone(self):
        if self.context.milestone is None:
            return 'hidden'
        else:
            return ''

    def bugtask_config(self):
        """Configuration for the bugtask JS widgets on the row."""
        assignee_vocabulary_name, assignee_vocabulary = (
            get_assignee_vocabulary_info(self.context))
        filter_details = vocabulary_filters(assignee_vocabulary)
        # Display the search field only if the user can set any person
        # or team
        user = self.user
        hide_assignee_team_selection = (
            not self.context.userCanSetAnyAssignee(user) and
            (user is None or user.teams_participated_in.count() == 0))
        cx = self.context
        return dict(
            id=cx.id,
            row_id=self.data['row_id'],
            form_row_id=self.data['form_row_id'],
            bugtask_path='/'.join([''] + self.data['link'].split('/')[3:]),
            prefix=get_prefix(cx),
            targetname=cx.bugtargetdisplayname,
            bug_title=cx.bug.title,
            assignee_value=cx.assignee and cx.assignee.name,
            assignee_is_team=cx.assignee and cx.assignee.is_team,
            assignee_vocabulary=assignee_vocabulary_name,
            assignee_vocabulary_filters=filter_details,
            hide_assignee_team_selection=hide_assignee_team_selection,
            user_can_unassign=cx.userCanUnassign(user),
            user_can_delete=self.user_can_delete_bugtask,
            delete_link=self.data['delete_link'],
            target_is_product=IProduct.providedBy(cx.target),
            status_widget_items=self.status_widget_items,
            status_value=cx.status.title,
            importance_widget_items=self.importance_widget_items,
            importance_value=cx.importance.title,
            milestone_widget_items=self.milestone_widget_items,
            milestone_value=(
                canonical_url(
                    cx.milestone,
                    request=self.api_request)
                if cx.milestone else None),
            user_can_edit_assignee=self.user_can_edit_assignee,
            user_can_edit_milestone=self.user_has_privileges,
            user_can_edit_status=self.user_can_edit_status,
            user_can_edit_importance=self.user_has_privileges,
            )


@implementer(IObjectPrivacy)
class BugTaskPrivacyAdapter:
    """Provides `IObjectPrivacy` for `IBugTask`."""

    def __init__(self, context):
        self.context = context

    @property
    def is_private(self):
        """Return True if the bug is private, otherwise False."""
        return self.context.bug.private


class BugTaskCreateQuestionView(LaunchpadFormView):
    """View for creating a question from a bug."""
    schema = ICreateQuestionFromBugTaskForm

    def setUpFields(self):
        """See `LaunchpadFormView`."""
        LaunchpadFormView.setUpFields(self)
        if not self.can_be_a_question:
            self.form_fields = self.form_fields.omit('comment')

    @property
    def next_url(self):
        """See `LaunchpadFormView`."""
        return canonical_url(self.context)

    @property
    def can_be_a_question(self):
        """Return True if this bug can become a question, otherwise False."""
        return self.context.bug.canBeAQuestion()

    @action('Convert this Bug into a Question', name='create')
    def create_action(self, action, data):
        """Create a question from this bug and set this bug to Invalid.

        The bugtask's status will be set to Invalid. The question
        will be linked to this bug.

        A question will not be created if a question was previously created,
        the pillar does not use Launchpad to track bugs, or there is more
        than one valid bugtask.
        """
        if not self.context.bug.canBeAQuestion():
            self.request.response.addNotification(
                'This bug could not be converted into a question.')
            return

        comment = data.get('comment', None)
        self.context.bug.convertToQuestion(self.user, comment=comment)

    label = 'Convert this bug to a question'

    page_title = label


class BugTaskRemoveQuestionView(LaunchpadFormView):
    """View for creating a question from a bug."""
    schema = IRemoveQuestionFromBugTaskForm

    def setUpFields(self):
        """See `LaunchpadFormView`."""
        LaunchpadFormView.setUpFields(self)
        if not self.has_question:
            self.form_fields = self.form_fields.omit('comment')

    @property
    def next_url(self):
        """See `LaunchpadFormView`."""
        return canonical_url(self.context)

    @property
    def has_question(self):
        """Return True if a question was created from this bug, or False."""
        return self.context.bug.getQuestionCreatedFromBug() is not None

    @action('Convert Back to Bug', name='remove')
    def remove_action(self, action, data):
        """Remove a question from this bug.

        The question will be unlinked from the bug. The question is not
        altered in any other way; it belongs to the question workflow.
        The bug's bugtasks are editable, though none are changed. Bug
        supervisors are responsible for updating the bugtasks.
        """
        question = self.context.bug.getQuestionCreatedFromBug()
        if question is None:
            self.request.response.addNotification(
                'This bug does not have a question to remove')
            return

        owner_is_subscribed = question.isSubscribed(self.context.bug.owner)
        question.unlinkBug(self.context.bug, user=self.user)
        # The question.owner was implicitly unsubscribed when the bug
        # was unlinked. We resubscribe the owner if he was subscribed.
        if owner_is_subscribed is True:
            self.context.bug.subscribe(question.owner, self.user)
        self.request.response.addNotification(
            structured(
                'Removed Question #%s: <a href="%s">%s<a>.',
                str(question.id),
                canonical_url(question),
                question.title))

        comment = data.get('comment', None)
        if comment is not None:
            self.context.bug.newMessage(
                owner=getUtility(ILaunchBag).user,
                subject=self.context.bug.followup_subject(),
                content=comment)

    @property
    def label(self):
        return ('Bug #%i - Convert this question back to a bug'
                % self.context.bug.id)

    page_title = label


@delegate_to(IBugActivity, context='activity')
class BugActivityItem:
    """A decorated BugActivity."""

    def __init__(self, activity):
        self.activity = activity

    @property
    def change_summary(self):
        """Return a formatted summary of the change."""
        if self.target is not None:
            # This is a bug task.  We want the attribute, as filtered out.
            summary = self.attribute
        else:
            # Otherwise, the attribute is more normalized than what we want.
            # Use "whatchanged," which sometimes is more descriptive.
            summary = self.whatchanged
        return self.get_better_summary(summary)

    def get_better_summary(self, summary):
        """For some activities, we want a different summary for the UI.

        Some event names are more descriptive as data, but less relevant to
        users, who are unfamiliar with the lp code."""
        better_summaries = {
            'bug task deleted': 'no longer affects',
            }
        return better_summaries.get(summary, summary)

    @property
    def _formatted_tags_change(self):
        """Return a tags change as lists of added and removed tags."""
        assert self.whatchanged == 'tags', (
            "Can't return a formatted tags change for a change in %s."
            % self.whatchanged)

        # Turn the strings of newvalue and oldvalue into sets so we
        # can work out the differences.
        if self.newvalue != '':
            new_tags = set(re.split('\s+', self.newvalue))
        else:
            new_tags = set()

        if self.oldvalue != '':
            old_tags = set(re.split('\s+', self.oldvalue))
        else:
            old_tags = set()

        added_tags = sorted(new_tags.difference(old_tags))
        removed_tags = sorted(old_tags.difference(new_tags))

        return_string = ''
        if len(added_tags) > 0:
            return_string = "added: %s\n" % ' '.join(added_tags)
        if len(removed_tags) > 0:
            return_string = (
                return_string + "removed: %s" % ' '.join(removed_tags))

        # Trim any leading or trailing \ns and then convert the to
        # <br />s so they're displayed correctly.
        return return_string.strip('\n')

    @property
    def change_details(self):
        """Return a detailed description of the change."""
        # Our default return dict. We may mutate this depending on
        # what's changed.
        return_dict = {
            'old_value': self.oldvalue,
            'new_value': self.newvalue,
            }
        attribute = self.attribute
        if attribute == 'title':
            # We display summary changes as a unified diff, replacing
            # \ns with <br />s so that the lines are separated properly.
            diff = html_escape(
                get_unified_diff(self.oldvalue, self.newvalue, 72))
            return diff.replace("\n", "<br />")

        elif attribute == 'description':
            # Description changes can be quite long, so we just return
            # 'updated' rather than returning the whole new description
            # or a diff.
            return 'updated'

        elif attribute == 'tags':
            # We special-case tags because we can work out what's been
            # added and what's been removed.
            return html_escape(self._formatted_tags_change).replace(
                '\n', '<br />')

        elif attribute == 'assignee':
            for key in return_dict:
                if return_dict[key] is None:
                    return_dict[key] = 'nobody'
                else:
                    return_dict[key] = html_escape(return_dict[key])

        elif attribute == 'milestone':
            for key in return_dict:
                if return_dict[key] is None:
                    return_dict[key] = 'none'
                else:
                    return_dict[key] = html_escape(return_dict[key])

        elif attribute == 'bug task deleted':
            return self.oldvalue

        else:
            # Our default state is to just return oldvalue and newvalue.
            # Since we don't necessarily know what they are, we escape
            # them.
            for key in return_dict:
                return_dict[key] = html_escape(return_dict[key])

        return "%(old_value)s &#8594; %(new_value)s" % return_dict


class BugTaskBreadcrumb(Breadcrumb):
    """Breadcrumb for an `IBugTask`."""

    def __init__(self, context):
        super(BugTaskBreadcrumb, self).__init__(context)
        # If the user does not have permission to view the bug for
        # whatever reason, raise ComponentLookupError.
        try:
            context.bug.displayname
        except Unauthorized:
            raise ComponentLookupError()

    @property
    def text(self):
        return self.context.bug.displayname

    @property
    def detail(self):
        bug = self.context.bug
        title = smartquote('"%s"' % bug.title)
        return '%s %s' % (bug.displayname, title)
