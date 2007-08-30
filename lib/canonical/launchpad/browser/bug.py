# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'BugAlsoReportInDistributionView',
    'BugAlsoReportInUpstreamView',
    'BugAlsoReportInDistributionWithBugTrackerCreationView',
    'BugAlsoReportInUpstreamWithBugTrackerCreationView',
    'BugContextMenu',
    'BugEditView',
    'BugFacets',
    'BugMarkAsDuplicateView',
    'BugNavigation',
    'BugRelatedObjectEditView',
    'BugSecrecyEditView',
    'BugSetNavigation',
    'BugTextView',
    'BugURL',
    'BugView',
    'BugWithoutContextView',
    'ChooseAffectedProductView',
    'DeprecatedAssignedBugsView',
    'MaloneView',
    ]

import cgi
import operator
import urllib

from zope.app.form.browser import DropdownWidget, TextWidget
from zope.app.form.interfaces import WidgetsError
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility
from zope.event import notify
from zope.interface import implements
from zope.security.interfaces import Unauthorized

from canonical.launchpad.interfaces import (
    BugTaskSearchParams,
    IAddBugTaskForm,
    IBug,
    IBugSet,
    IBugTaskSet,
    IBugTrackerSet,
    IBugWatchSet,
    ICveSet,
    IDistributionSourcePackage,
    IFrontPageBugTaskSearch,
    ILaunchBag,
    ILaunchpadCelebrities,
    IProductSet,
    NoBugTrackerFound,
    NotFoundError,
    validate_new_distrotask,
    valid_upstreamtask,
    )
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.event import SQLObjectCreatedEvent
from canonical.launchpad.validators import LaunchpadValidationError

from canonical.launchpad.webapp import (
    custom_widget, action, canonical_url, ContextMenu,
    LaunchpadFormView, LaunchpadView,LaunchpadEditFormView, stepthrough,
    Link, Navigation, structured, StandardLaunchpadFacets)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData

from canonical.lp.dbschema import BugTaskImportance, BugTaskStatus
from canonical.widgets.bug import BugTagsWidget
from canonical.widgets.project import ProjectScopeWidget
from canonical.widgets.textwidgets import StrippedTextWidget


class BugNavigation(Navigation):

    # It would be easier, since there is no per-bug sequence for a BugWatch
    # and we have to leak the BugWatch.id anyway, to hang bugwatches off a
    # global /bugwatchs/nnnn

    # However, we want in future to have them at /bugs/nnn/+watch/p where p
    # is not the BugWatch.id but instead a per-bug sequence number (1, 2,
    # 3...) for the 1st, 2nd and 3rd watches added for this bug,
    # respectively. So we are going ahead and hanging this off the bug to
    # which it belongs as a first step towards getting the basic URL schema
    # correct.

    usedfor = IBug

    @stepthrough('+watch')
    def traverse_watches(self, name):
        if name.isdigit():
            # in future this should look up by (bug.id, watch.seqnum)
            return getUtility(IBugWatchSet)[name]


class BugFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for an IBug.

    However, we never show this, but it does apply to things like
    bug nominations, by 'acquisition'.
    """

    usedfor = IBug

    enable_only = []


class BugSetNavigation(Navigation):

    usedfor = IBugSet

    @stepthrough('+text')
    def text(self, name):
        try:
            return getUtility(IBugSet).getByNameOrID(name)
        except (NotFoundError, ValueError):
            return None


class BugContextMenu(ContextMenu):
    usedfor = IBug
    links = ['editdescription', 'markduplicate', 'visibility', 'addupstream',
             'adddistro', 'subscription', 'addsubscriber', 'addcomment',
             'nominate', 'addbranch', 'linktocve', 'unlinkcve',
             'offermentoring', 'retractmentoring', 'activitylog']

    def __init__(self, context):
        # Always force the context to be the current bugtask, so that we don't
        # have to duplicate menu code.
        ContextMenu.__init__(self, getUtility(ILaunchBag).bugtask)

    def editdescription(self):
        text = 'Edit description/tags'
        return Link('+edit', text, icon='edit')

    def visibility(self):
        text = 'Set privacy/security'
        return Link('+secrecy', text, icon='edit')

    def markduplicate(self):
        text = 'Mark as duplicate'
        return Link('+duplicate', text, icon='edit')

    def addupstream(self):
        text = 'Also affects project'
        return Link('+choose-affected-product', text, icon='add')

    def adddistro(self):
        text = 'Also affects distribution'
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
        text = 'Subscribe someone else'
        return Link('+addsubscriber', text, icon='add')

    def nominate(self):
        launchbag = getUtility(ILaunchBag)
        target = launchbag.product or launchbag.distribution
        if check_permission("launchpad.Driver", target):
            text = "Target to release"
        else:
            text = 'Nominate for release'

        return Link('+nominate', text, icon='milestone')

    def addcomment(self):
        text = 'Comment or attach file'
        return Link('+addcomment', text, icon='add')

    def addbranch(self):
        text = 'Add branch'
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
        text = 'Remove CVE link'
        return Link('+unlinkcve', text, icon='remove', enabled=enabled)

    def offermentoring(self):
        text = 'Offer mentorship'
        user = getUtility(ILaunchBag).user
        enabled = self.context.bug.canMentor(user)
        return Link('+mentor', text, icon='add', enabled=enabled)

    def retractmentoring(self):
        text = 'Retract mentorship'
        user = getUtility(ILaunchBag).user
        enabled = (self.context.bug.isMentor(user) and
                   not self.context.bug.is_complete and
                   user)
        return Link('+retractmentoring', text, icon='remove', enabled=enabled)

    def activitylog(self):
        text = 'View activity log'
        return Link('+activity', text, icon='list')



class MaloneView(LaunchpadFormView):
    """The Bugs front page."""

    custom_widget('searchtext', TextWidget, displayWidth=50)
    custom_widget('scope', ProjectScopeWidget)
    schema = IFrontPageBugTaskSearch
    field_names = ['searchtext', 'scope']

    # Test: standalone/xx-slash-malone-slash-bugs.txt
    error_message = None

    @property
    def target_css_class(self):
        """The CSS class for used in the target widget."""
        if self.target_error:
            return 'error'
        else:
            return None

    @property
    def target_error(self):
        """The error message for the target widget."""
        return self.getWidgetError('scope')

    def initialize(self):
        LaunchpadFormView.initialize(self)
        bug_id = self.request.form.get("id")
        if bug_id:
            self._redirectToBug(bug_id)
        elif self.widgets['scope'].hasInput():
            self._validate(action=None, data={})

    def _redirectToBug(self, bug_id):
        """Redirect to the specified bug id."""
        if bug_id.startswith("#"):
            # Be nice to users and chop off leading hashes
            bug_id = bug_id[1:]
        try:
            bug = getUtility(IBugSet).getByNameOrID(bug_id)
        except NotFoundError:
            self.error_message = "Bug %r is not registered." % bug_id
        else:
            return self.request.response.redirect(canonical_url(bug))

    def getMostRecentlyFixedBugs(self, limit=5):
        """Return the ten most recently fixed bugs."""
        fixed_bugs = []
        search_params = BugTaskSearchParams(
            self.user, status=BugTaskStatus.FIXRELEASED,
            orderby='-date_closed')
        fixed_bugtasks = getUtility(IBugTaskSet).search(search_params)
        # XXX: Bjorn Tillenius 2006-12-13:
        #      We might end up returning less than :limit: bugs, but in
        #      most cases we won't, and '4*limit' is here to prevent
        #      this page from timing out in production. Later I'll fix
        #      this properly by selecting bugs instead of bugtasks.
        #      If fixed_bugtasks isn't sliced, it will take a long time
        #      to iterate over it, even over just 10, because
        #      Transaction.iterSelect() listifies the result.
        for bugtask in fixed_bugtasks[:4*limit]:
            if bugtask.bug not in fixed_bugs:
                fixed_bugs.append(bugtask.bug)
                if len(fixed_bugs) >= limit:
                    break
        return fixed_bugs

    def getCveBugLinkCount(self):
        """Return the number of links between bugs and CVEs there are."""
        return getUtility(ICveSet).getBugCveCount()


class BugView(LaunchpadView):
    """View class for presenting information about an IBug.

    Since all bug pages are registered on IBugTask, the context will be
    adapted to IBug in order to make the security declarations work
    properly. This has the effect that the context in the pagetemplate
    changes as well, so the bugtask (which is often used in the pages)
    is available as currentBugTask(). This may not be all that pretty,
    but it was the best solution we came up with when deciding to hang
    all the pages off IBugTask instead of IBug.
    """

    def currentBugTask(self):
        """Return the current IBugTask.

        'current' is determined by simply looking in the ILaunchBag utility.
        """
        return getUtility(ILaunchBag).bugtask

    @property
    def subscription(self):
        """Return whether the current user is subscribed."""
        user = self.user
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


class MultiStepBaseView(LaunchpadFormView):
    """Base view for all steps of the bug-also-affects workflow."""

    next_view = None
    step_name = ""
    main_action_label = u'Continue'

    @action(u'Continue', name='continue')
    def continue_action(self, action, data):
        """Check if the form should be processed or if it's the first time
        we're showing it and call self.main_action() if necessary.
        """
        if not self.shouldProcess(data):
            return

        return self.main_action(action, data)

    def injectStepNameInRequest(self):
        visited_steps = self.request.form.get('field.visited_steps')
        if visited_steps is None:
            self.request.form['field.visited_steps'] = self.step_name
        elif self.step_name not in visited_steps:
            self.request.form['field.visited_steps'] = (
                "%s, %s" % (visited_steps, self.step_name))
        else:
            # Already visited this step, so there's no need to inject our
            # step_name in the request anymore.
            pass

    def shouldProcess(self, data):
        """Should this data be processed by the view's action methods?

        It should be processed only if the user has already visited this page
        and submitted the form.
        
        Since we use identical action names in all views we can't rely on
        that to find out whether or not to process them, so we use an extra
        hidden input to store the views the user has visited already.
        """
        visited_steps = data['visited_steps']
        if visited_steps is not None and self.step_name not in visited_steps:
            # First time we visit this page, so there's no point in validating
            # its data.
            return False
        return True

    def render(self):
        # This is a hack to make it possible to change the label of our main
        # action in subclasses.
        actions = []
        for action in self.actions:
            if action.__name__ == 'field.actions.continue':
                action.label = self.main_action_label
            actions.append(action)
        self.actions = actions
        return super(MultiStepBaseView, self).render()


class ChooseAffectedProductView(MultiStepBaseView):
    """View for choosing a product that is affected by a given bug."""

    # Need to define this here because we will render this view manually.
    template = ViewPageTemplateFile(
        '../templates/bugtask-choose-affected-product.pt')
    __launchpad_facetname__ = 'bugs'

    schema = IAddBugTaskForm
    field_names = ['product', 'visited_steps']
    label = u"Record as affecting another project"
    custom_widget('visited_steps', TextWidget, visible=False)
    step_name = "choose_product"

    def _getUpstream(self, distro_package):
        """Return the upstream if there is a packaging link."""
        for distroseries in distro_package.distribution.serieses:
            source_package = distroseries.getSourcePackage(
                distro_package.sourcepackagename)
            if source_package.direct_packaging is not None:
                return source_package.direct_packaging.productseries.product
        else:
            return None

    def initialize(self):
        super(ChooseAffectedProductView, self).initialize()
        bugtask = self.context
        if (self.widgets['product'].hasInput() or
            not IDistributionSourcePackage.providedBy(bugtask.target)):
            return

        upstream = self._getUpstream(bugtask.target)
        if upstream is None:
            distroseries = bugtask.distribution.currentseries
            if distroseries is not None:
                sourcepackage = distroseries.getSourcePackage(
                    bugtask.sourcepackagename)
                self.request.response.addInfoNotification(
                    'Please select the appropriate upstream project.'
                    ' This step can be avoided by'
                    ' <a href="%(package_url)s/+edit-packaging">updating'
                    ' the packaging information for'
                    ' %(full_package_name)s</a>.',
                    full_package_name=bugtask.bugtargetdisplayname,
                    package_url=canonical_url(sourcepackage))
        else:
            try:
                valid_upstreamtask(bugtask.bug, upstream)
            except WidgetsError:
                # There is already a task for the upstream.
                pass
            else:
                # We can infer the upstream and there's no bugtask for it,
                # so we can go straight to the page asking for the remote
                # bug URL.
                self.request.form['field.product'] = urllib.quote(
                    upstream.name)
                self.next_view = BugAlsoReportInUpstreamView

    def validate(self, data):
        if not self.shouldProcess(data):
            return

        if data.get('product'):
            try:
                valid_upstreamtask(self.context.bug, data.get('product'))
            except WidgetsError, errors:
                for error in errors:
                    self.setFieldError('product', error.snippet())
                return

        entered_product = self.request.form.get(self.widgets['product'].name)
        if not entered_product:
            return

        # The user has entered a product name but we couldn't find it.
        # Show a meaningful error message instead of "Invalid value".
        new_product_url = "%s/+new" % (
            canonical_url(getUtility(IProductSet)))
        search_url = self.widgets['product'].popupHref()
        self.setFieldError(
            'product',
            'There is no project in Launchpad named "%s". You may'
            ' want to <a href="%s">search for it</a>, or'
            ' <a href="%s">register it</a> if you can\'t find it.' % (
                cgi.escape(entered_product),
                cgi.escape(search_url, quote=True),
                cgi.escape(new_product_url, quote=True)))

    def main_action(self, action, data):
        """Inject the selected product into the form and set the next_view to
        be used by our meta view.
        """
        self.request.form['field.product'] = urllib.quote(data['product'].name)
        self.next_view = BugAlsoReportInUpstreamView


class BugAddAffectedProductMetaView(LaunchpadView):
    """Meta view for adding an affected product to an existing bug.

    This view implements a wizard-like workflow in which you specify the first
    step and then each step is responsible for specifying the next one or None
    if, for some reason, we need to stay at the current step.

    Any views used as steps here must inherit from MultiStepBaseView. The
    views are also responsible for injecting into the request anything they
    may want to be available for the next view.
    """

    first_step_view = ChooseAffectedProductView

    def initialize(self):
        view = self.first_step_view(self.context, self.request)
        view.initialize()
        view.injectStepNameInRequest()
        while view.next_view is not None:
            view = view.next_view(self.context, self.request)
            view.initialize()
            view.injectStepNameInRequest()
        self.view = view

    def render(self):
        return self.view.render()


# XXX: FIX docstring and rename.
class BugAlsoReportInView(MultiStepBaseView):
    """View class for reporting a bug in other contexts.

    In this view the user specifies the URL for the remote bug and we create
    the new bugtask/bugwatch.
    
    If the bugtracker in the given URL is not registered in Launchpad, we
    delegate its creation to another view. This other view is then responsible
    for calling back this view's @action method to create the bugtask/bugwatch.
    """

    schema = IAddBugTaskForm
    custom_widget('bug_url', StrippedTextWidget, displayWidth=50)
    custom_widget('visited_steps', TextWidget, visible=False)

    step_name = 'specify_remote_bug_url'
    next_view = None
    task_added = None
    available_action_names = None
    target_field_names = ()
    should_ask_for_confirmation = False
    __launchpad_facetname__ = 'bugs'

    def __init__(self, context, request):
        super(BugAlsoReportInView, self).__init__(context, request)
        self.notifications = []
        self.field_names = ['bug_url', 'visited_steps'] + list(
            self.target_field_names)

    def setUpWidgets(self):
        super(BugAlsoReportInView, self).setUpWidgets()
        self.target_widgets = [
            self.widgets[field_name]
            for field_name in self.field_names
            if field_name in self.target_field_names]
        self.bugwatch_widgets = [self.widgets['bug_url']]
        self.compulsory_widgets = [self.widgets['visited_steps']]

    def getTarget(self, data=None):
        """Return the fix target.

        If data is given extract the target from there. Otherwise extract it
        from this view's widgets.
        """
        raise NotImplementedError()

    def doInitialValidation(self, data):
        """Any initial validation wanted by subclasses."""
        pass

    def validate(self, data):
        """Validate the form.

        Do any initial validation defined in subclasses and check that bug_url
        is None if the target uses Launchpad for bug tracking.
        """
        if not self.shouldProcess(data):
            return

        self.doInitialValidation(data)
        target = self.getTarget(data)
        bug_url = data.get('bug_url')
        if bug_url and target.official_malone:
            self.addError(
                "Bug watches can not be added for %s, as it uses Launchpad"
                " as its official bug tracker. Alternatives are to add a"
                " watch for another project, or a comment containing a"
                " URL to the related bug report." % cgi.escape(
                    target.displayname))

        if target.official_malone:
            # The rest of the validation applies only to targets not
            # using Malone.
            return

        if len(self.errors) > 0:
            # The checks below should be made only if the form doesn't
            # contain any errors.
            return

        if self.request.get('ignore_missing_remote_bug'):
            # The user confirmed that he does want to add the task without a
            # bug watch.
            return
        if not target.official_malone and not bug_url:
            # Add a hidden field to fool LaunchpadFormView into thinking we
            # submitted the action it expected when in fact we're submiting
            # something else to indicate the user has confirmed.
            confirm_button = (
                '<input type="hidden" name="%s" value="1" />'
                '<input style="font-size: smaller" type="submit"'
                ' value="Yes, Add Anyway" name="ignore_missing_remote_bug" />'
                % self.continue_action.__name__)
            #XXX: Bjorn Tillenius 2006-09-13:
            #     This text should be re-written to be more compact. I'm not
            #     doing it now, though, since it might go away completely
            #     soon.
            self.notifications.append(
                "%s doesn't use Launchpad as its bug tracker. If you don't add"
                " a bug watch now you have to keep track of the status"
                " manually. You can however link to an external bug tracker"
                " at a later stage in order to get automatic status updates."
                " Are you sure you want to request a fix anyway?"
                " %s"
                % (cgi.escape(self.getTarget().displayname), confirm_button))
            self.should_ask_for_confirmation = True

    # XXX: Fix docstring
    def main_action(self, action, data):
        """Create new bug task.

        Only one of product and distribution may be not None, and
        if distribution is None, sourcepackagename has to be None.
        """
        bug_url = self.request.form.get('field.bug_url', '')
        if self.should_ask_for_confirmation:
            assert not bug_url, ("We should only ask for confirmation when "
                                 "a bug url is not provided")
            return None

        extracted_bug = None
        extracted_bugtracker = None
        if bug_url:
            bug_url = bug_url.strip()
            try:
                extracted_bugtracker, extracted_bug = getUtility(
                    IBugWatchSet).extractBugTrackerAndBug(bug_url)
            except NoBugTrackerFound:
                # Delegate to another view which will ask the user if (s)he
                # wants to create the bugtracker now.
                if list(self.target_field_names) == ['product']:
                    self.next_view = (
                        BugAlsoReportInUpstreamWithBugTrackerCreationView)
                    return
                else:
                    assert 'distribution' in self.target_field_names
                    self.next_view = (
                        BugAlsoReportInDistributionWithBugTrackerCreationView)
                    return

        product = data.get('product')
        distribution = data.get('distribution')
        sourcepackagename = data.get('sourcepackagename')
        self.task_added = getUtility(IBugTaskSet).createTask(
            self.context.bug, getUtility(ILaunchBag).user, product=product,
            distribution=distribution, sourcepackagename=sourcepackagename)

        target = self.getTarget(data)
        if extracted_bug:
            assert extracted_bugtracker is not None, (
                "validate() should have ensured that bugtracker is not None.")
            # Make sure that we don't add duplicate bug watches.
            bug_watch = self.task_added.bug.getBugWatch(
                extracted_bugtracker, extracted_bug)
            if bug_watch is None:
                bug_watch = self.task_added.bug.addWatch(
                    extracted_bugtracker, extracted_bug, self.user)
                notify(SQLObjectCreatedEvent(bug_watch))
            if not target.official_malone:
                self.task_added.bugwatch = bug_watch

        if not target.official_malone and self.task_added.bugwatch is not None:
            # A remote bug task gets its status from a bug watch, so we want
            # its status/importance to be UNKNOWN when created.
            self.task_added.transitionToStatus(
                BugTaskStatus.UNKNOWN, self.user)
            self.task_added.importance = BugTaskImportance.UNKNOWN

        notify(SQLObjectCreatedEvent(self.task_added))
        self.next_url = canonical_url(self.task_added)


# XXX: FIX docstring and rename.
class BugAlsoReportInDistributionView(BugAlsoReportInView):
    """Specialized BugAlsoReportInView for reporting a bug in a distro."""

    # Need to define this here because we will render this view manually.
    template = ViewPageTemplateFile('../templates/bugtask-requestfix.pt')

    label = "Also affects distribution/package"
    target_field_names = ('distribution', 'sourcepackagename')

    def getTarget(self, data=None):
        if data is not None:
            return data.get('distribution')
        else:
            return self.widgets['distribution'].getInputValue()

    def doInitialValidation(self, data):
        distribution = data.get('distribution')
        sourcepackagename = data.get('sourcepackagename')
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
                validate_new_distrotask(
                    self.context.bug, distribution, sourcepackagename)
            except LaunchpadValidationError, error:
                self.setFieldError('sourcepackagename', error.snippet())

    def render(self):
        for bugtask in IBug(self.context).bugtasks:
            if (IDistributionSourcePackage.providedBy(bugtask.target) and
                (not self.widgets['sourcepackagename'].hasInput())):
                self.widgets['sourcepackagename'].setRenderedValue(
                    bugtask.sourcepackagename)
                break
        return super(BugAlsoReportInDistributionView, self).render()


# XXX: FIX docstring and rename.
class BugAlsoReportInUpstreamView(BugAlsoReportInView):
    """Specialized BugAlsoReportInView for reporting a bug in an upstream."""

    # Need to define this here because we will render this view manually.
    template = ViewPageTemplateFile(
        '../templates/bugtask-requestfix-upstream.pt')

    label = "Confirm project"
    target_field_names = ('product',)
    main_action_label = u'Add to Bug Report'

    def getTarget(self, data=None):
        if data is not None:
            return data.get('product')
        else:
            return self.widgets['product'].getInputValue()


class BugAddAffectedDistroView(BugAddAffectedProductMetaView):

    first_step_view = BugAlsoReportInDistributionView


# XXX: Must rename the 3 views below as they don't actually do anything other
# than creating the bugtracker.
# XXX: Must also fix the docstring.
class BugAlsoReportInWithBugTrackerCreationView(MultiStepBaseView):
    """A view to be used in conjunction with BugAlsoReportInView.

    This view will ask the user if he really wants to register the new bug
    tracker, perform the registration and call BugAlsoReportInView's
    continue_action method to create the new bugtask/bugwatch.

    NOTE: Since we want any subclass which doesn't define an action_url
          property to use this view's one, it must always come first than
          any other view defining that property in the inheritance list.
    """

    schema = IAddBugTaskForm
    custom_widget('bug_url', StrippedTextWidget, displayWidth=50)
    custom_widget('visited_steps', TextWidget, visible=False)

    __launchpad_facetname__ = 'bugs'
    step_name = "bugtracker_creation"
    next_view = None
    main_action_label = u'Register Bug Tracker and Add to Bug Report'

    def create_task_and_bugtracker_action(self, action, data):
        bug_url = data.get('bug_url')
        assert bug_url is not None and len(bug_url) != 0
        bug_url = bug_url.strip()
        try:
            getUtility(IBugWatchSet).extractBugTrackerAndBug(bug_url)
        except NoBugTrackerFound, error:
            getUtility(IBugTrackerSet).ensureBugTracker(
                error.base_url, self.user, error.bugtracker_type)


class BugAlsoReportInDistributionWithBugTrackerCreationView(
        BugAlsoReportInWithBugTrackerCreationView):

    field_names = [
        'distribution', 'sourcepackagename', 'bug_url', 'visited_steps']
    custom_widget('distribution', DropdownWidget, visible=False)
    custom_widget('sourcepackagename', DropdownWidget, visible=False)
    label = "Also affects distribution/package"
    # Need to define this here because we will render this view manually.
    template = ViewPageTemplateFile(
        '../templates/bugtask-confirm-bugtracker-creation.pt')

    def main_action(self, action, data):
        super(BugAlsoReportInDistributionWithBugTrackerCreationView,
              self).create_task_and_bugtracker_action(action, data)
        self.next_view = BugAlsoReportInDistributionView


class BugAlsoReportInUpstreamWithBugTrackerCreationView(
        BugAlsoReportInWithBugTrackerCreationView):

    field_names = ['product', 'bug_url', 'visited_steps']
    custom_widget('product', DropdownWidget, visible=False)
    label = "Confirm project"
    # Need to define this here because we will render this view manually.
    template = ViewPageTemplateFile(
        '../templates/bugtask-confirm-bugtracker-creation.pt')

    def main_action(self, action, data):
        super(BugAlsoReportInUpstreamWithBugTrackerCreationView,
              self).create_task_and_bugtracker_action(action, data)
        self.next_view = BugAlsoReportInUpstreamView


class BugEditViewBase(LaunchpadEditFormView):
    """Base class for all bug edit pages."""

    schema = IBug

    def setUpWidgets(self):
        """Set up the widgets using the bug as the context."""
        LaunchpadEditFormView.setUpWidgets(self, context=self.context.bug)

    def updateBugFromData(self, data):
        """Update the bug using the values in the data dictionary."""
        LaunchpadEditFormView.updateContextFromData(
            self, data, context=self.context.bug)

    @property
    def next_url(self):
        return canonical_url(self.context)


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
        bugtarget = self.context.target
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
                    new_tag, bugtarget.bugtargetdisplayname, confirm_button))
            self._confirm_new_tags = True

    @action('Change', name='change')
    def edit_bug_action(self, action, data):
        if not self._confirm_new_tags:
            self.updateBugFromData(data)
            self.next_url = canonical_url(self.context)

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
        self.updateBugFromData(data)


class BugSecrecyEditView(BugEditViewBase):
    """Page for marking a bug as a private/public."""

    field_names = ['private', 'security_related']
    label = "Bug visibility and security"

    @action('Change', name='change')
    def change_action(self, action, data):
        self.updateBugFromData(data)


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

        if bug.duplicates:
            dupes = ' '.join(str(dupe.id) for dupe in bug.duplicates)
            text.append('duplicates: %s' % dupes)
        else:
            text.append('duplicates: ')

        text.append('subscribers: ')

        for subscription in bug.subscriptions:
            text.append(' %s' % self.person_text(subscription.person))

        return ''.join(line + '\n' for line in text)

    def bugtask_text(self, task):
        text = []
        text.append('task: %s' % task.bugtargetname)
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
    rootsite = 'bugs'

    def __init__(self, context):
        self.context = context

    @property
    def path(self):
        return u"bugs/%d" % self.context.id

