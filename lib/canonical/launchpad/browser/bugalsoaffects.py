# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['BugAlsoAffectsProductMetaView', 'BugAlsoAffectsDistroMetaView']

import cgi
import urllib

from zope.app.form.browser import DropdownWidget, TextWidget
from zope.app.form.interfaces import WidgetsError
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility
from zope.event import notify

from canonical.launchpad.interfaces import (
    IAddBugTaskForm, IBug, IBugTaskSet, IBugTrackerSet, IBugWatchSet,
    IDistributionSourcePackage, ILaunchBag, ILaunchpadCelebrities,
    IProductSet, NoBugTrackerFound, validate_new_distrotask,
    valid_upstreamtask)
from canonical.launchpad.event import SQLObjectCreatedEvent
from canonical.launchpad.validators import LaunchpadValidationError

from canonical.launchpad.webapp import (
    custom_widget, action, canonical_url, LaunchpadFormView, LaunchpadView)

from canonical.lp.dbschema import BugTaskImportance, BugTaskStatus
from canonical.widgets.textwidgets import StrippedTextWidget


class BugAlsoAffectsProductMetaView(LaunchpadView):
    """Meta view for adding an affected product to an existing bug.

    This view implements a wizard-like workflow in which you specify the first
    step and then each step is responsible for specifying the next one or None
    if, for some reason, we need to stay at the current step.

    Any views used as steps here must inherit from AlsoAffectsStep. The
    views are also responsible for injecting into the request anything they
    may want to be available to the next view.
    """

    @property
    def first_step_view(self):
        return ChooseProductStep

    def initialize(self):
        view = self.first_step_view(self.context, self.request)
        # The first time this view is rendered the request won't contain a
        # visited_steps key, but we need it to be in the HTML (in order to be
        # submitted together with the rest of the data), so we inject it
        # in the request before setupWidgets is called (through initialize).
        view.injectStepNameInRequest()
        view.initialize()
        while view.next_view is not None:
            view = view.next_view(self.context, self.request)
            view.initialize()
            view.injectStepNameInRequest()
        self.view = view

    def render(self):
        return self.view.render()


class BugAlsoAffectsDistroMetaView(BugAlsoAffectsProductMetaView):

    @property
    def first_step_view(self):
        return DistroBugTaskCreationStep


class AlsoAffectsStep(LaunchpadFormView):
    """Base view for all steps of the bug-also-affects workflow."""

    next_view = None
    step_name = ""
    main_action_label = u'Continue'

    def validateStep(self, data):
        """To be overriden in subclasses."""
        pass

    @action(u'Continue', name='continue')
    def continue_action(self, action, data):
        """Check if the form should be processed or if it's the first time
        we're showing it and call self.main_action() if necessary.
        """
        if not self.shouldProcess(data):
            return

        return self.main_action(action, data)

    def validate(self, data):
        if not self.shouldProcess(data):
            return

        self.validateStep(data)

    def injectStepNameInRequest(self):
        visited_steps = self.request.form.get('field.visited_steps')
        if not visited_steps:
            self.request.form['field.visited_steps'] = self.step_name
        elif self.step_name not in visited_steps:
            self.request.form['field.visited_steps'] = (
                "%s, %s" % (visited_steps, self.step_name))
        else:
            # Already visited this step, so there's no need to inject our
            # step_name in the request again.
            pass

    def shouldProcess(self, data):
        """Should this data be processed by the view's action methods?

        It should be processed only if the user has already visited this page
        and submitted the form.
        
        Since we use identical action names in all views we can't rely on
        that to find out whether or not to process them, so we use an extra
        hidden input to store the views the user has visited already.
        """
        if self.step_name not in data['visited_steps']:
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
        return super(AlsoAffectsStep, self).render()


class ChooseProductStep(AlsoAffectsStep):
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
        super(ChooseProductStep, self).initialize()
        bugtask = self.context
        if (self.widgets['product'].hasInput() or
            not IDistributionSourcePackage.providedBy(bugtask.target)):
            return

        self.maybeAddNotificationOrTeleport()

    def maybeAddNotificationOrTeleport(self):
        """If we can't infer the upstream and the target distribution has a
        currentseries we add a notification message telling the user the
        package could be linked to an upstream to avoid this extra step.

        On the other hand, if the upstream can be infered and there's no task
        for it yet, we teleport the user straight to the next step.
        """
        bugtask = self.context
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
                self.next_view = ProductBugTaskCreationStep

    def validateStep(self, data):
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
        self.next_view = ProductBugTaskCreationStep


class BugTaskCreationStep(AlsoAffectsStep):
    """The bug task creation step of the AlsoAffects workflow.

    In this view the user specifies the URL for the remote bug and we create
    the new bugtask/bugwatch.
    
    If the bugtracker in the given URL is not registered in Launchpad, we
    delegate its creation to another view. This other view should then
    delegate the bug task creation to this one once the bugtracker is
    registered.
    """

    schema = IAddBugTaskForm
    custom_widget('bug_url', StrippedTextWidget, displayWidth=50)
    custom_widget('visited_steps', TextWidget, visible=False)

    step_name = 'specify_remote_bug_url'
    task_added = None
    available_action_names = None
    target_field_names = ()
    __launchpad_facetname__ = 'bugs'

    def __init__(self, context, request):
        super(BugTaskCreationStep, self).__init__(context, request)
        self.notifications = []
        self.field_names = ['bug_url', 'visited_steps'] + list(
            self.target_field_names)

    def setUpWidgets(self):
        super(BugTaskCreationStep, self).setUpWidgets()
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

    def validateStep(self, data):
        """Check there's no bug_url if the target uses malone."""
        target = self.getTarget(data)
        bug_url = data.get('bug_url')
        if bug_url and target.official_malone:
            self.addError(
                "Bug watches can not be added for %s, as it uses Launchpad"
                " as its official bug tracker. Alternatives are to add a"
                " watch for another project, or a comment containing a"
                " URL to the related bug report." % cgi.escape(
                    target.displayname))

    def main_action(self, action, data):
        """Create the new bug task.

        If a remote bug URL is given and there's no bug watch registered with
        that URL we create a bug watch and link it to the newly created bug
        task.
        """
        bug_url = self.request.form.get('field.bug_url', '')
        target = self.getTarget(data)
        if (not self.request.get('ignore_missing_remote_bug') and 
            not target.official_malone and not bug_url):
            # We have no URL for the remote bug and the target does not use
            # Launchpad for bug tracking, so we warn the user this is not
            # optimal and ask for his confirmation.

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
                    self.next_view = UpstreamBugTrackerCreationStep
                else:
                    assert 'distribution' in self.target_field_names
                    self.next_view = DistroBugTrackerCreationStep
                return

        product = data.get('product')
        distribution = data.get('distribution')
        sourcepackagename = data.get('sourcepackagename')
        self.task_added = getUtility(IBugTaskSet).createTask(
            self.context.bug, getUtility(ILaunchBag).user, product=product,
            distribution=distribution, sourcepackagename=sourcepackagename)

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


class DistroBugTaskCreationStep(BugTaskCreationStep):
    """Specialized BugTaskCreationStep for reporting a bug in a distribution.
    """

    # Need to define this here because we will render this view manually.
    template = ViewPageTemplateFile('../templates/bugtask-requestfix.pt')

    label = "Also affects distribution/package"
    target_field_names = ('distribution', 'sourcepackagename')

    def getTarget(self, data=None):
        if data is not None:
            return data.get('distribution')
        else:
            return self.widgets['distribution'].getInputValue()

    def validateStep(self, data):
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

        super(DistroBugTaskCreationStep, self).validateStep(data)

    def render(self):
        for bugtask in IBug(self.context).bugtasks:
            if (IDistributionSourcePackage.providedBy(bugtask.target) and
                (not self.widgets['sourcepackagename'].hasInput())):
                self.widgets['sourcepackagename'].setRenderedValue(
                    bugtask.sourcepackagename)
                break
        return super(DistroBugTaskCreationStep, self).render()


class ProductBugTaskCreationStep(BugTaskCreationStep):
    """Specialized BugTaskCreationStep for reporting a bug in an upstream."""

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


class BugTrackerCreationStep(AlsoAffectsStep):
    """View for creating a bugtracker from the given URL.

    This view will ask the user if he really wants to register the new bug
    tracker, perform the registration and then delegate to one of
    BugTaskCreationStep's subclasses.
    """

    schema = IAddBugTaskForm
    custom_widget('bug_url', StrippedTextWidget, displayWidth=50)
    custom_widget('visited_steps', TextWidget, visible=False)

    __launchpad_facetname__ = 'bugs'
    step_name = "bugtracker_creation"
    main_action_label = u'Register Bug Tracker and Add to Bug Report'

    def main_action(self, action, data):
        bug_url = data.get('bug_url')
        assert bug_url is not None and len(bug_url) != 0
        bug_url = bug_url.strip()
        try:
            getUtility(IBugWatchSet).extractBugTrackerAndBug(bug_url)
        except NoBugTrackerFound, error:
            getUtility(IBugTrackerSet).ensureBugTracker(
                error.base_url, self.user, error.bugtracker_type)
        self.next_view = self._next_view


class DistroBugTrackerCreationStep(BugTrackerCreationStep):

    _next_view = DistroBugTaskCreationStep
    field_names = [
        'distribution', 'sourcepackagename', 'bug_url', 'visited_steps']
    custom_widget('distribution', DropdownWidget, visible=False)
    custom_widget('sourcepackagename', DropdownWidget, visible=False)
    label = "Also affects distribution/package"
    # Need to define this here because we will render this view manually.
    template = ViewPageTemplateFile(
        '../templates/bugtask-confirm-bugtracker-creation.pt')


class UpstreamBugTrackerCreationStep(BugTrackerCreationStep):

    _next_view = ProductBugTaskCreationStep
    field_names = ['product', 'bug_url', 'visited_steps']
    custom_widget('product', DropdownWidget, visible=False)
    label = "Confirm project"
    # Need to define this here because we will render this view manually.
    template = ViewPageTemplateFile(
        '../templates/bugtask-confirm-bugtracker-creation.pt')

