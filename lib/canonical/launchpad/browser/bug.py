# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'BugSetNavigation',
    'BugView',
    'MaloneView',
    'BugEditView',
    'BugRelatedObjectEditView',
    'BugAlsoReportInView',
    'BugContextMenu',
    'BugWithoutContextView',
    'DeprecatedAssignedBugsView',
    'BugTextView',
    'BugURL',
    'BugMarkAsDuplicateView',
    'BugSecrecyEditView',
    'ChooseAffectedProductView',
    ]

import cgi
import operator
import urllib

from zope.app.form.browser import TextWidget
from zope.app.form.interfaces import InputErrors, WidgetsError
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility
from zope.event import notify
from zope.interface import implements
from zope.security.interfaces import Unauthorized

from canonical.launchpad.interfaces import (
    BugTaskSearchParams, IAddBugTaskForm, IBug, IBugSet, IBugTaskSet,
    IBugWatchSet, ICveSet, IDistributionSourcePackage, IFrontPageBugTaskSearch,
    ILaunchBag, ILaunchpadCelebrities, IProductSet, IUpstreamBugTask,
    NoBugTrackerFound, NotFoundError, UnrecognizedBugTrackerURL,
    valid_distrotask, valid_upstreamtask)
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.event import SQLObjectCreatedEvent

from canonical.launchpad.webapp import (
    custom_widget, action, canonical_url, ContextMenu,
    LaunchpadFormView, LaunchpadView,LaunchpadEditFormView, stepthrough,
    Link, Navigation, structured)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData

from canonical.lp.dbschema import BugTaskImportance, BugTaskStatus
from canonical.widgets.bug import BugTagsWidget
from canonical.widgets.textwidgets import StrippedTextWidget


class BugSetNavigation(Navigation):

    usedfor = IBugSet

    # XXX
    # The browser:page declaration should be sufficient, but the traversal
    # takes priority. This is a workaround.
    # https://launchpad.net/products/launchpad/+bug/30238
    # -- Daf 2006/02/01

    @stepthrough('+text')
    def text(self, name):
        try:
            return getUtility(IBugSet).getByNameOrID(name)
        except (NotFoundError, ValueError):
            return None

    def traverse(self, name):
        try:
            return getUtility(IBugSet).getByNameOrID(name)
        except (NotFoundError, ValueError):
            # If the bug is not found, we expect a NotFoundError. If the
            # value of name is not a value that can be used to retrieve
            # a specific bug, we expect a ValueError.
            return None


class BugContextMenu(ContextMenu):
    usedfor = IBug
    links = ['editdescription', 'markduplicate', 'visibility', 'addupstream',
             'adddistro', 'subscription', 'addsubscriber', 'addcomment',
             'nominate', 'addbranch', 'linktocve', 'unlinkcve', 'filebug',
             'activitylog']

    def __init__(self, context):
        # Always force the context to be the current bugtask, so that we don't
        # have to duplicate menu code.
        ContextMenu.__init__(self, getUtility(ILaunchBag).bugtask)

    def editdescription(self):
        text = 'Edit Description/Tags'
        return Link('+edit', text, icon='edit')

    def visibility(self):
        text = 'Visibility/Security'
        return Link('+secrecy', text, icon='edit')

    def markduplicate(self):
        text = 'Mark as Duplicate'
        return Link('+duplicate', text, icon='edit')

    def addupstream(self):
        text = 'Also Affects Upstream'
        return Link('+choose-affected-product', text, icon='add')

    def adddistro(self):
        text = 'Also Affects Distribution'
        return Link('+distrotask', text, icon='add')

    def subscription(self):
        user = getUtility(ILaunchBag).user
        if user is None:
            text = 'Subscribe/Unsubscribe'
            icon = 'edit'
        elif user is not None and (
            self.context.bug.isSubscribed(user) or
            self.context.bug.isSubscribedToDupes(user)):
            text = 'Unsubscribe'
            icon = 'remove'
        else:
            for team in user.teams_participated_in:
                if (self.context.bug.isSubscribed(team) or
                    self.context.bug.isSubscribedToDupes(team)):
                    text = 'Subscribe/Unsubscribe'
                    icon = 'edit'
                    break
            else:
                text = 'Subscribe'
                icon = 'add'
        return Link('+subscribe', text, icon=icon)

    def addsubscriber(self):
        text = 'Subscribe Someone Else'
        return Link('+addsubscriber', text, icon='add')

    def nominate(self):
        launchbag = getUtility(ILaunchBag)
        target = launchbag.product or launchbag.distribution
        if check_permission("launchpad.Driver", target):
            text = "Target to Release"
        else:
            text = 'Nominate for Release'

        return Link('+nominate', text, icon='milestone')

    def addcomment(self):
        text = 'Comment/Attach File'
        return Link('+addcomment', text, icon='add')

    def addbranch(self):
        text = 'Add Branch'
        return Link('+addbranch', text, icon='add')

    def linktocve(self):
        text = structured(
            'Link to '
            '<abbr title="Common Vulnerabilities and Exposures Index">'
            'CVE'
            '</abbr>')
        return Link('+linkcve', text, icon='add')

    def unlinkcve(self):
        enabled = bool(self.context.bug.cves)
        text = 'Remove CVE Link'
        return Link('+unlinkcve', text, icon='remove', enabled=enabled)

    def filebug(self):
        bugtarget = self.context.target
        linktarget = '%s/%s' % (canonical_url(bugtarget), '+filebug')
        text = 'Report a Bug in %s' % bugtarget.displayname
        return Link(linktarget, text, icon='add')

    def activitylog(self):
        text = 'Activity Log'
        return Link('+activity', text, icon='list')



class MaloneView(LaunchpadFormView):
    """The Bugs front page."""

    schema = IFrontPageBugTaskSearch
    field_names = ['searchtext', 'target']

    # Test: standalone/xx-slash-malone-slash-bugs.txt
    error_message = None
    def initialize(self):
        LaunchpadFormView.initialize(self)
        bug_id = self.request.form.get("id")
        if not bug_id:
            return
        if bug_id.startswith("#"):
            # Be nice to users and chop off leading hashes
            bug_id = bug_id[1:]
        try:
            bug = getUtility(IBugSet).getByNameOrID(bug_id)
        except NotFoundError:
            self.error_message = "Bug %r is not registered." % bug_id
        else:
            return self.request.response.redirect(canonical_url(bug))

    def getMostRecentlyFixedBugs(self, limit=10):
        """Return the ten most recently fixed bugs."""
        fixed_bugs = []
        search_params = BugTaskSearchParams(
            self.user, status=BugTaskStatus.FIXRELEASED,
            orderby='-date_closed')
        fixed_bugtasks = getUtility(IBugTaskSet).search(search_params) 
        # XXX: We might end up returning less than :limit: bugs, but in
        #      most cases we won't, and '4*limit' is here to prevent
        #      this page from timing out in production. Later I'll fix
        #      this properly by selecting bugs instead of bugtasks.
        #      If fixed_bugtasks isn't sliced, it will take a long time
        #      to iterate over it, even over just 10, because
        #      Transaction.iterSelect() listifies the result.
        #      -- Bjorn Tillenius, 2006-12-13
        for bugtask in fixed_bugtasks[:4*limit]:
            if bugtask.bug not in fixed_bugs:
                fixed_bugs.append(bugtask.bug)
                if len(fixed_bugs) >= limit:
                    break
        return fixed_bugs

    def getCveBugLinkCount(self):
        """Return the number of links between bugs and CVEs there are."""
        return getUtility(ICveSet).getBugCveCount()


class BugView:
    """View class for presenting information about an IBug.

    Since all bug pages are registered on IBugTask, the context will be
    adapted to IBug in order to make the security declarations work
    properly. This has the effect that the context in the pagetemplate
    changes as well, so the bugtask (which is often used in the pages)
    is available as currentBugTask(). This may not be all that pretty,
    but it was the best solution we came up with when deciding to hang
    all the pages off IBugTask instead of IBug.
    """

    def __init__(self, context, request):
        self.current_bugtask = context
        self.context = IBug(context)
        self.request = request
        self.user = getUtility(ILaunchBag).user

    def currentBugTask(self):
        """Return the current IBugTask.

        'current' is determined by simply looking in the ILaunchBag utility.
        """
        return getUtility(ILaunchBag).bugtask

    @property
    def subscription(self):
        """Return whether the current user is subscribed."""
        user = getUtility(ILaunchBag).user
        if user is None:
            return False
        return self.context.isSubscribed(user)

    def duplicates(self):
        """Return a list of dicts of duplicates.

        Each dict contains the title that should be shown and the bug
        object itself. This allows us to protect private bugs using a
        title like 'Private Bug'.
        """
        dupes = []
        for bug in self.context.duplicates:
            dupe = {}
            try:
                dupe['title'] = bug.title
            except Unauthorized:
                dupe['title'] = 'Private Bug'
            dupe['id'] = bug.id
            dupe['url'] = self.getDupeBugLink(bug)
            dupes.append(dupe)

        return dupes

    def getDupeBugLink(self, dupe):
        """Return a URL for a duplicate of this bug.

        The link will be in the current context if the dupe is also
        reported in this context, otherwise a default /bugs/$bug.id
        style URL will be returned.
        """
        current_task = self.currentBugTask()

        for task in dupe.bugtasks:
            if task.target == current_task.target:
                return canonical_url(task)

        return canonical_url(dupe)


class BugWithoutContextView:
    """View that redirects to the new bug page.

    The user is redirected, to the oldest IBugTask ('oldest' being
    defined as the IBugTask with the smallest ID.)
    """
    def redirectToNewBugPage(self):
        """Redirect the user to the 'first' report of this bug."""
        # An example of practicality beating purity.
        bugtasks = sorted(self.context.bugtasks, key=operator.attrgetter('id'))
        self.request.response.redirect(canonical_url(bugtasks[0]))


class BugAlsoReportInBaseView:
    """Base view for both classes dealing with adding new bugtasks."""

    def validateProduct(self, product):
        try:
            valid_upstreamtask(self.context.bug, product)
        except WidgetsError, errors:
            for error in errors:
                self.setFieldError('product', error.snippet())
            return False
        else:
            return True


class ChooseAffectedProductView(LaunchpadFormView, BugAlsoReportInBaseView):
    """View for choosing a product and redirect to +add-affected-product."""

    schema = IUpstreamBugTask
    field_names = ['product']
    label = u"Add affected product to bug"

    def _getUpstream(self, distro_package):
        """Return the upstream if there is a packaging link."""
        for distrorelease in distro_package.distribution.releases:
            source_package = distrorelease.getSourcePackage(
                distro_package.sourcepackagename)
            if source_package.direct_packaging is not None:
                return source_package.direct_packaging.productseries.product
        else:
            return None

    def initialize(self):
        LaunchpadFormView.initialize(self)
        bugtask = self.context
        if self.widgets['product'].hasInput():
            self._validate(action=None, data={})
        elif IDistributionSourcePackage.providedBy(bugtask.target):
            upstream = self._getUpstream(bugtask.target)
            if upstream is None:
                distrorelease = bugtask.distribution.currentrelease
                if distrorelease is not None:
                    sourcepackage = distrorelease.getSourcePackage(
                        bugtask.sourcepackagename)
                    self.request.response.addInfoNotification(
                        'Please select the appropriate upstream product.'
                        ' This step can be avoided by'
                        ' <a href="%(package_url)s/+packaging">updating'
                        ' the packaging information for'
                        ' %(full_package_name)s</a>.',
                        full_package_name=bugtask.targetname,
                        package_url=canonical_url(sourcepackage))
            else:
                try:
                    valid_upstreamtask(bugtask.bug, upstream)
                except WidgetsError:
                    # There is already a task for the upstream.
                    pass
                else:
                    self.request.response.redirect(
                        "%s/+add-affected-product?field.product=%s" % (
                            canonical_url(self.context),
                            urllib.quote(upstream.name)))

    def validate(self, data):
        if data.get('product'):
            self.validateProduct(data['product'])
        else:
            # If the user entered a product, provide a more useful error
            # message than "Invalid value".
            entered_product = self.request.form.get(
                self.widgets['product'].name)
            if entered_product:
                new_product_url = "%s/+new" % (
                    canonical_url(getUtility(IProductSet)))
                search_url = self.widgets['product'].popupHref()
                self.setFieldError(
                    'product',
                    'There is no product in Launchpad named "%s". You may'
                    ' want to <a href="%s">search for it</a>, or'
                    ' <a href="%s">register it</a> if you can\'t find it.' % (
                        cgi.escape(entered_product),
                        cgi.escape(search_url, quote=True),
                        cgi.escape(new_product_url, quote=True)))

    @action(u'Continue', name='continue')
    def continue_action(self, action, data):
        self.next_url = '%s/+add-affected-product?field.product=%s' % (
            canonical_url(self.context), urllib.quote(data['product'].name))


class BugAlsoReportInView(LaunchpadFormView, BugAlsoReportInBaseView):
    """View class for reporting a bug in other contexts."""

    schema = IAddBugTaskForm
    custom_widget('bug_url', StrippedTextWidget, displayWidth=50)

    index = ViewPageTemplateFile('../templates/bugtask-requestfix.pt')
    upstream_page = ViewPageTemplateFile(
        '../templates/bugtask-requestfix-upstream.pt')
    _confirm_new_task = False
    extracted_bug = None
    extracted_bugtracker = None

    def __init__(self, context, request):
        LaunchpadFormView.__init__(self, context, request)
        self.notifications = []
        self.field_names = ['bug_url']

    def setUpLabelAndWidgets(self, label, target_field_names):
        """Initialize the form and render it."""
        self.label = label
        self.field_names.extend(target_field_names)
        self.initialize()
        self.target_widgets = [
            self.widgets[field_name]
            for field_name in self.field_names
            if field_name in target_field_names]
        self.bugwatch_widgets = [
            self.widgets[field_name]
            for field_name in self.field_names
            if field_name not in target_field_names]

    def render_upstreamtask(self):
        self.setUpLabelAndWidgets("Add affected product to bug", ['product'])
        self.index = self.upstream_page

        # It's not possible to enter the product on this page, so
        # validate the given product and redirect if there are any
        # errors.
        try:
            product = self.widgets['product'].getInputValue()
        except InputErrors:
            product_error = True
        else:
            if (self.continue_action.submitted() or
                self.confirm_action.submitted()):
                # If the user submitted the form, we've already
                # validated the widget. Get the error directly instead
                # of trying to validate again.
                product_error = self.getWidgetError('product')
            else:
                product_error = not self.validateProduct(product)

        if product_error:
            product_name = self.request.form.get('field.product', '')
            self.request.response.redirect(
                "%s/+choose-affected-product?field.product=%s" % (
                    canonical_url(self.context),
                    urllib.quote(product_name)))
            return u''
        # self.continue_action is a descriptor that returns a "bound
        # action", so we need to assign it to itself in order for the
        # label change to stick around.
        self.continue_action = self.continue_action
        self.continue_action.label = (
            u'Indicate bug in %s' % cgi.escape(product.displayname))
        return self.render()

    def render_distrotask(self):
        self.setUpLabelAndWidgets(
            "Add affected source package to bug",
            ['distribution', 'sourcepackagename'])
        for bugtask in IBug(self.context).bugtasks:
            if (IDistributionSourcePackage.providedBy(bugtask.target) and
                (not self.widgets['sourcepackagename'].hasInput())):
                self.widgets['sourcepackagename'].setRenderedValue(
                    bugtask.sourcepackagename)
                break
        return self.render()

    def getBugTargetName(self):
        """Return the name of the fix target.

        This is either the chosen product or distribution.
        """
        if 'distribution' in self.field_names:
            target = self.widgets['distribution'].getInputValue()
        elif 'product' in self.field_names:
            target = self.widgets['product'].getInputValue()
        else:
            raise AssertionError(
                'Either a product or distribution widget should be present'
                ' in the form.')
        return target.displayname

    def validate(self, data):
        """Validate the form.

        Check that:
            * We have a unique upstream task
            * We have a unique distribution task
            * If the target uses Malone, a bug_url has to be None.
        """
        product = data.get('product')
        distribution = data.get('distribution')
        sourcepackagename = data.get('sourcepackagename')
        if product:
            target = product
            if not self.validateProduct(product):
                return
        elif distribution:
            target = distribution
            entered_package = self.request.form.get(
                self.widgets['sourcepackagename'].name)
            if sourcepackagename is None and entered_package:
                # The entered package doesn't exist.
                filebug_url = "%s/+filebug" % canonical_url(
                    getUtility(ILaunchpadCelebrities).launchpad)
                self.setFieldError(
                    'sourcepackagename',
                    'There is no package in %s named "%s". If it should'
                    ' be here, <a href="%s">report this as a bug</a>.' % (
                        cgi.escape(distribution.displayname),
                        cgi.escape(entered_package),
                        cgi.escape(filebug_url, quote=True)))
            else:
                try:
                    valid_distrotask(
                        self.context.bug, distribution, sourcepackagename,
                        on_create=True)
                except WidgetsError, errors:
                    for error in errors:
                        self.setFieldError(
                            'sourcepackagename', error.snippet())
        else:
            # Validation failed for either the product or distribution,
            # no point in trying to validate further.
            return

        bug_url = data.get('bug_url')
        if bug_url and target.official_malone:
            self.addError(
                "Bug watches can not be added for %s, as it uses Malone"
                " as its official bug tracker. Alternatives are to add a"
                " watch for another product, or a comment containing a"
                " URL to the related bug report." % cgi.escape(
                    target.displayname))

        if target.official_malone:
            # The rest of the validation applies only to targets not
            # using Malone.
            return

        if bug_url is not None:
            # Try to find out which bug and bug tracker the URL is
            # referring to.
            bugwatch_set = getUtility(IBugWatchSet)
            try:
                # Assign attributes, so that the action handler can
                # access the extracted bugtracker and bug.
                self.extracted_bugtracker, self.extracted_bug = (
                    bugwatch_set.extractBugTrackerAndBug(bug_url))
            except NoBugTrackerFound, error:
                # XXX: The user should be able to press a button here in
                #      order to register the tracker.
                #      -- Bjorn Tillenius, 2006-09-26
                self.setFieldError(
                    'bug_url',
                    "The bug tracker at %s isn't registered in Launchpad."
                    ' You need to'
                    ' <a href="/bugs/bugtrackers/+newbugtracker">register'
                    ' it</a> before you can link any bugs to it.' % (
                        cgi.escape(error.base_url)))
            except UnrecognizedBugTrackerURL:
                self.setFieldError(
                    'bug_url',
                    "Launchpad doesn't know what kind of bug tracker"
                    ' this URL is pointing at.')

        if len(self.errors) > 0:
            # The checks below should be made only if the form doesn't
            # contain any errors.
            return

        confirm_action = self.confirm_action
        if confirm_action.submitted():
            # The user confirmed that he does want to add the task.
            return
        if not target.official_malone and not bug_url:
            confirm_button = (
                '<input style="font-size: smaller" type="submit"'
                ' value="%s" name="%s" />' % (
                    confirm_action.label, confirm_action.__name__))
            #XXX: This text should be re-written to be more compact. I'm not
            #     doing it now, though, since it might go away completely
            #     soon. -- Bjorn Tillenius, 2006-09-13
            self.notifications.append(
                "%s doesn't use Malone as its bug tracker. If you don't add"
                " a bug watch now you have to keep track of the status"
                " manually. You can however link to an external bug tracker"
                " at a later stage in order to get automatic status updates."
                " Are you sure you want to request a fix anyway?"
                " %s" % (cgi.escape(self.getBugTargetName()), confirm_button))
            self._confirm_new_task = True

    @action(u'Continue', name='request_fix')
    def continue_action(self, action, data):
        """Create new bug task.

        Only one of product and distribution may be not None, and
        if distribution is None, sourcepackagename has to be None.
        """
        if self._confirm_new_task:
            return
        product = data.get('product')
        distribution = data.get('distribution')
        sourcepackagename = data.get('sourcepackagename')
        bugtracker = self.extracted_bugtracker
        remotebug = self.extracted_bug

        if product is not None:
            target = product
        elif distribution is not None:
            target = distribution
        else:
            raise AssertionError(
                'validate() should ensure that a product or distribution'
                ' is present')

        taskadded = getUtility(IBugTaskSet).createTask(
            self.context.bug,
            getUtility(ILaunchBag).user,
            product=product,
            distribution=distribution, sourcepackagename=sourcepackagename)

        if remotebug:
            assert bugtracker is not None, (
                "validate() should have ensured that bugtracker is not None.")
            # Make sure that we don't add duplicate bug watches.
            bug_watch = taskadded.bug.getBugWatch(bugtracker, remotebug)
            if bug_watch is None:
                bug_watch = taskadded.bug.addWatch(
                    bugtracker, remotebug, self.user)
                notify(SQLObjectCreatedEvent(bug_watch))
            if not target.official_malone:
                taskadded.bugwatch = bug_watch

        if not target.official_malone and taskadded.bugwatch is not None:
            # A remote bug task gets its from a bug watch, so we want
            # its status to be None when created.
            taskadded.transitionToStatus(BugTaskStatus.UNKNOWN)
            taskadded.importance = BugTaskImportance.UNKNOWN

        notify(SQLObjectCreatedEvent(taskadded))
        self.next_url = canonical_url(taskadded)

    @action('Yes, request fix anyway', name='confirm')
    def confirm_action(self, action, data):
        self.continue_action.success(data)

    def render(self):
        """Render the page with only one submit button."""
        # The confirmation button shouldn't be rendered automatically.
        self.actions = [self.continue_action]
        return LaunchpadFormView.render(self)


class BugEditViewBase(LaunchpadEditFormView):
    """Base class for all bug edit pages."""

    schema = IBug

    def __init__(self, context, request):
        self.current_bugtask = context
        context = IBug(context)
        LaunchpadEditFormView.__init__(self, context, request)

    @property
    def next_url(self):
        return canonical_url(self.current_bugtask)


class BugEditView(BugEditViewBase):
    """The view for the edit bug page."""

    field_names = ['title', 'description', 'tags', 'name']
    custom_widget('title', TextWidget, displayWidth=30)
    custom_widget('tags', BugTagsWidget)
    next_url = None

    _confirm_new_tags = False

    def __init__(self, context, request):
        BugEditViewBase.__init__(self, context, request)
        self.notifications = []

    def validate(self, data):
        """Make sure new tags are confirmed."""
        if 'tags' not in data:
            return
        confirm_action = self.confirm_tag_action
        if confirm_action.submitted():
            # Validation is needed only for the change action.
            return
        bugtarget = self.current_bugtask.target
        newly_defined_tags = set(data['tags']).difference(
            bugtarget.getUsedBugTags())
        # Display the confirm button in a notification message. We want
        # it to be slightly smaller than usual, so we can't simply let
        # it render itself.
        confirm_button = (
            '<input style="font-size: smaller" type="submit"'
            ' value="%s" name="%s" />' % (
                confirm_action.label, confirm_action.__name__))
        for new_tag in newly_defined_tags:
            self.notifications.append(
                'The tag "%s" hasn\'t yet been used by %s before.'
                ' Is this a new tag? %s' % (
                    new_tag, bugtarget.bugtargetname, confirm_button))
            self._confirm_new_tags = True

    @action('Change', name='change')
    def edit_bug_action(self, action, data):
        if not self._confirm_new_tags:
            self.updateContextFromData(data)
            self.next_url = canonical_url(self.current_bugtask)

    @action('Yes, define new tag', name='confirm_tag')
    def confirm_tag_action(self, action, data):
        self.actions['field.actions.change'].success(data)

    def render(self):
        """Render the page with only one submit button."""
        # The confirmation button shouldn't be rendered automatically.
        self.actions = [self.edit_bug_action]
        return BugEditViewBase.render(self)


class BugMarkAsDuplicateView(BugEditViewBase):
    """Page for marking a bug as a duplicate."""

    field_names = ['duplicateof']
    label = "Mark bug report as a duplicate"

    @action('Change', name='change')
    def change_action(self, action, data):
        self.updateContextFromData(data)


class BugSecrecyEditView(BugEditViewBase):
    """Page for marking a bug as a private/public."""

    field_names = ['private', 'security_related']
    label = "Bug visibility and security"

    @action('Change', name='change')
    def change_action(self, action, data):
        self.updateContextFromData(data)


class BugRelatedObjectEditView(SQLObjectEditView):
    """View class for edit views of bug-related object.

    Examples would include the edit cve page, edit subscription page,
    etc.
    """
    def __init__(self, context, request):
        SQLObjectEditView.__init__(self, context, request)
        # Store the current bug in an attribute of the view, so that
        # ZPT rendering code can access it.
        self.bug = getUtility(ILaunchBag).bug
        self.current_bugtask = getUtility(ILaunchBag).bugtask

    def changed(self):
        """Redirect to the bug page."""
        self.request.response.redirect(canonical_url(self.current_bugtask))


class DeprecatedAssignedBugsView:
    """Deprecate the /malone/assigned namespace.

    It's important to ensure that this namespace continues to work, to
    prevent linkrot, but since FOAF seems to be a more natural place
    to put the assigned bugs report, we'll redirect to the appropriate
    FOAF URL.
    """
    def __init__(self, context, request):
        """Redirect the user to their assigned bugs report."""
        self.context = context
        self.request = request

    def redirect_to_assignedbugs(self):
        self.request.response.redirect(
            canonical_url(getUtility(ILaunchBag).user) +
            "/+assignedbugs")


class BugTextView(LaunchpadView):
    """View for simple text page displaying information for a bug."""

    def person_text(self, person):
        return '%s (%s)' % (person.displayname, person.name)

    def bug_text(self, bug):
        text = []
        text.append('bug: %d' % bug.id)
        text.append('title: %s' % bug.title)
        text.append('reporter: %s' % self.person_text(bug.owner))

        if bug.duplicateof:
            text.append('duplicate-of: %d' % bug.duplicateof.id)
        else:
            text.append('duplicate-of: ')

        text.append('subscribers: ')

        for subscription in bug.subscriptions:
            text.append(' %s' % self.person_text(subscription.person))

        return ''.join(line + '\n' for line in text)

    def bugtask_text(self, task):
        text = []
        text.append('task: %s' % task.targetname)
        text.append('status: %s' % task.status.title)
        text.append('reporter: %s' % self.person_text(task.owner))

        text.append('importance: %s' % task.importance.title)

        if task.assignee:
            text.append('assignee: %s' % self.person_text(task.assignee))
        else:
            text.append('assignee: ')

        if task.milestone:
            text.append('milestone: %s' % task.milestone.name)
        else:
            text.append('milestone: ')

        return ''.join(line + '\n' for line in text)

    def render(self):
        self.request.response.setHeader('Content-type', 'text/plain')
        texts = (
            [self.bug_text(self.context)] +
            [self.bugtask_text(task) for task in self.context.bugtasks])
        return u'\n'.join(texts)


class BugURL:
    implements(ICanonicalUrlData)

    inside = None
    rootsite = 'mainsite'

    def __init__(self, context):
        self.context = context

    @property
    def path(self):
        return u"bugs/%d" % self.context.id
