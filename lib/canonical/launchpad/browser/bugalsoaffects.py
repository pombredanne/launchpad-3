# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['BugAlsoAffectsProductMetaView', 'BugAlsoAffectsDistroMetaView',
           'BugAlsoAffectsProductWithProductCreationView']

import cgi
from textwrap import dedent

from zope.app.form.browser import DropdownWidget, TextWidget
from zope.app.form.interfaces import WidgetsError
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility
from zope.event import notify
from zope.formlib import form
from zope.schema import Choice
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    BugTaskImportance, BugTaskStatus, IAddBugTaskForm,
    IAddBugTaskWithProductCreationForm, IBug, IBugTaskSet, IBugTrackerSet,
    IBugWatchSet, IDistributionSourcePackage, ILaunchBag,
    ILaunchpadCelebrities, IProductSet, NoBugTrackerFound,
    validate_new_distrotask, valid_upstreamtask)
from canonical.launchpad.event import SQLObjectCreatedEvent
from canonical.launchpad.validators import LaunchpadValidationError

from canonical.launchpad.webapp import (
    custom_widget, action, canonical_url, LaunchpadFormView, LaunchpadView)

from canonical.widgets.itemswidgets import LaunchpadRadioWidget
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
        # In fact we should be calling injectStepNameInRequest after
        # initialize() in both cases, otherwise the form will be processed
        # when it's first rendered, thus showing warning/error messages before
        # the user submits it. For the first step, though, this won't happen
        # because the request won't contain the action name, but it also won't
        # contain the visited_steps key and thus the HTML won't contain the
        # hidden widget unless I inject before calling initialize().
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
    """Base view for all steps of the bug-also-affects workflow.
    
    Subclasses must override step_name, _field_names and define a
    main_action() method which processes the form data.
    """

    __launchpad_facetname__ = 'bugs'
    schema = IAddBugTaskForm
    custom_widget('visited_steps', TextWidget, visible=False)

    _field_names = []
    next_view = None
    step_name = ""
    main_action_label = u'Continue'

    @property
    def field_names(self):
        return self._field_names + ['visited_steps']

    def validateStep(self, data):
        """Validation specific to a given step.

        To be overridden in subclasses, if necessary.
        """
        pass

    @action(u'Continue', name='continue')
    def continue_action(self, action, data):
        """Check if the form should be processed or if it's the first time
        we're showing it and call self.main_action() if necessary.
        """
        if not self.shouldProcess(data):
            return

        return self.main_action(data)

    def validate(self, data):
        """Call self.validateStep() if the form should be processed.

        Subclasses /must not/ override this method. They should override
        validateStep() if they have any custom validation they need to
        perform.
        """
        if not self.shouldProcess(data):
            return

        self.validateStep(data)

    def injectStepNameInRequest(self):
        """Inject this step's name into the request if necessary."""
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
        return self.step_name in data['visited_steps']

    def render(self):
        # This is a hack to make it possible to change the label of our main
        # action in subclasses.
        actions = []
        for action in self.actions:
            # Only change the label of our 'continue' action.
            if action.__name__ == 'field.actions.continue':
                action.label = self.main_action_label
            actions.append(action)
        self.actions = actions
        return super(AlsoAffectsStep, self).render()


class ChooseProductStep(AlsoAffectsStep):
    """View for choosing a product that is affected by a given bug."""

    template = ViewPageTemplateFile(
        '../templates/bugtask-choose-affected-product.pt')

    _field_names = ['product']
    label = u"Record as affecting another project"
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
        if (self.widgets['product'].hasInput() or
            not IDistributionSourcePackage.providedBy(self.context.target)):
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
        if upstream is not None:
            if not upstream.active:
                # XXX: This is only possible because of bug 140526, which
                # allows packages to be linked to inactive products.
                # -- Guilherme Salgado, 2007-09-18
                series = bugtask.distribution.currentseries
                assert series is not None, (
                    "This package is linked to a product series so this "
                    "package's distribution must have at least one distro "
                    "series.")
                sourcepackage = series.getSourcePackage(
                    bugtask.sourcepackagename)
                self.request.response.addWarningNotification(_(dedent("""
                    This package is linked to an inactive upstream.  You
                    can <a href="%(package_url)s/+edit-packaging">fix it</a>
                    to avoid this step in the future.""")),
                    package_url=canonical_url(sourcepackage))
                return

            try:
                valid_upstreamtask(bugtask.bug, upstream)
            except WidgetsError:
                # There is already a task for the upstream.
                pass
            else:
                # We can infer the upstream and there's no bugtask for it,
                # so we can go straight to the page asking for the remote
                # bug URL.
                self.request.form['field.product'] = upstream.name
                self.next_view = ProductBugTaskCreationStep
            return

        distroseries = bugtask.distribution.currentseries
        if distroseries is not None:
            sourcepackage = distroseries.getSourcePackage(
                bugtask.sourcepackagename)
            self.request.response.addInfoNotification(_(dedent("""
                Please select the appropriate upstream project. This step can
                be avoided by <a href="%(package_url)s/+edit-packaging"
                >updating the packaging information for
                %(full_package_name)s</a>.""")),
                full_package_name=bugtask.bugtargetdisplayname,
                package_url=canonical_url(sourcepackage))

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
        # Tell the user to search for it using the popup widget as it'll allow
        # the user to register a new product if the one he is looking for is
        # not yet registered.
        search_url = self.widgets['product'].popupHref()
        self.setFieldError(
            'product',
            'There is no project in Launchpad named "%s". Please '
            '<a href="%s">search for it</a> as it may be registered with '
            'a different name.' % (
                cgi.escape(entered_product),
                cgi.escape(search_url, quote=True)))

    def main_action(self, data):
        """Inject the selected product into the form and set the next_view to
        be used by our meta view.
        """
        self.request.form['field.product'] = data['product'].name
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

    custom_widget('bug_url', StrippedTextWidget, displayWidth=62)

    step_name = 'specify_remote_bug_url'
    target_field_names = ()

    # This is necessary so that other views which dispatch work to this one
    # have access to the newly created task.
    task_added = None

    def __init__(self, context, request):
        super(BugTaskCreationStep, self).__init__(context, request)
        self.notifications = []
        self._field_names = ['bug_url'] + list(self.target_field_names)

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

    def main_action(self, data):
        """Create the new bug task.

        If a remote bug URL is given and there's no bug watch registered with
        that URL we create a bug watch and link it to the newly created bug
        task.
        """
        bug_url = data.get('bug_url', '')
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
            self.notifications.append(_(dedent("""
                %s doesn't use Launchpad as its bug tracker. Without a bug
                URL to watch, status will need to be tracked manually.
                Request a fix anyway?  %s""" %
                (cgi.escape(self.getTarget().displayname), confirm_button))))
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
        task_added = self.task_added

        if extracted_bug:
            assert extracted_bugtracker is not None, (
                "validate() should have ensured that bugtracker is not None.")
            # Display a notification, if another bug is already linked
            # to the same external bug.
            other_bugs_already_watching = [
                bug for bug in extracted_bugtracker.getBugsWatching(
                    extracted_bug)
                if bug != self.context.bug]
            # Simply add one notification per bug to simplify the
            # implementation; most of the time it will be only one bug.
            for other_bug in other_bugs_already_watching:
                self.request.response.addInfoNotification(
                    '<a href="%(bug_url)s">Bug #%(bug_id)s</a> also links'
                    ' to the added bug watch'
                    ' (%(bugtracker_name)s #%(remote_bug)s).',
                    bug_url=canonical_url(other_bug), bug_id=other_bug.id,
                    bugtracker_name=extracted_bugtracker.name,
                    remote_bug=extracted_bug)

            # Make sure that we don't add duplicate bug watches.
            bug_watch = task_added.bug.getBugWatch(
                extracted_bugtracker, extracted_bug)
            if bug_watch is None:
                bug_watch = task_added.bug.addWatch(
                    extracted_bugtracker, extracted_bug, self.user)
                notify(SQLObjectCreatedEvent(bug_watch))
            if not target.official_malone:
                task_added.bugwatch = bug_watch

        if not target.official_malone and task_added.bugwatch is not None:
            # A remote bug task gets its status from a bug watch, so we want
            # its status/importance to be UNKNOWN when created.
            task_added.transitionToStatus(BugTaskStatus.UNKNOWN, self.user)
            task_added.importance = BugTaskImportance.UNKNOWN

        notify(SQLObjectCreatedEvent(task_added))
        self.next_url = canonical_url(task_added)


class DistroBugTaskCreationStep(BugTaskCreationStep):
    """Specialized BugTaskCreationStep for reporting a bug in a distribution.
    """

    template = ViewPageTemplateFile('../templates/bugtask-requestfix.pt')

    label = "Also affects distribution/package"
    target_field_names = ('distribution', 'sourcepackagename')

    def getTarget(self, data=None):
        if data is not None:
            return data.get('distribution')
        else:
            return self.widgets['distribution'].getInputValue()

    def validateStep(self, data):
        """Check that

        1. there's no bug_url if the target uses malone;
        2. there is a package with the given name;
        3. it's possible to create a new task for the given package/distro.
        """
        target = self.getTarget(data)
        bug_url = data.get('bug_url')
        if bug_url and target.official_malone:
            self.addError(
                "Bug watches can not be added for %s, as it uses Launchpad"
                " as its official bug tracker. Alternatives are to add a"
                " watch for another project, or a comment containing a"
                " URL to the related bug report." % cgi.escape(
                    target.displayname))

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

    custom_widget('bug_url', StrippedTextWidget, displayWidth=62)
    step_name = "bugtracker_creation"
    main_action_label = u'Register Bug Tracker and Add to Bug Report'
    _next_view = None

    def main_action(self, data):
        assert self._next_view is not None, (
            "_next_view must be specified in subclasses.")
        bug_url = data.get('bug_url').strip()
        try:
            getUtility(IBugWatchSet).extractBugTrackerAndBug(bug_url)
        except NoBugTrackerFound, error:
            getUtility(IBugTrackerSet).ensureBugTracker(
                error.base_url, self.user, error.bugtracker_type)
        self.next_view = self._next_view


class DistroBugTrackerCreationStep(BugTrackerCreationStep):

    _next_view = DistroBugTaskCreationStep
    _field_names = ['distribution', 'sourcepackagename', 'bug_url']
    custom_widget('distribution', DropdownWidget, visible=False)
    custom_widget('sourcepackagename', DropdownWidget, visible=False)
    label = "Also affects distribution/package"
    template = ViewPageTemplateFile(
        '../templates/bugtask-confirm-bugtracker-creation.pt')


class UpstreamBugTrackerCreationStep(BugTrackerCreationStep):

    _next_view = ProductBugTaskCreationStep
    _field_names = ['product', 'bug_url']
    custom_widget('product', DropdownWidget, visible=False)
    label = "Confirm project"
    template = ViewPageTemplateFile(
        '../templates/bugtask-confirm-bugtracker-creation.pt')


class BugAlsoAffectsProductWithProductCreationView(LaunchpadFormView):
    """Register a product and indicate this bug affects it.

    If there's no bugtracker with the given URL registered in Launchpad, then
    a new bugtracker is created as well.
    """

    label = "Register project affected by this bug"
    schema = IAddBugTaskWithProductCreationForm
    custom_widget('bug_url', StrippedTextWidget, displayWidth=62)
    custom_widget('existing_product', LaunchpadRadioWidget)
    field_names = ['bug_url', 'displayname', 'name', 'summary']
    existing_products = None
    MAX_PRODUCTS_TO_DISPLAY = 10

    def _findProductsUsingGivenBugTrackerAndStoreThem(self):
        """Find products using the bugtracker wich runs on the given URL.

        These products are stored in self.existing_products.

        If there are too many products using that bugtracker then we'll store
        only the first ones that somehow match the name given.
        """
        bug_url = self.request.form.get('field.bug_url')
        if not bug_url:
            return

        bugwatch_set = getUtility(IBugWatchSet)
        try:
            bugtracker, bug = bugwatch_set.extractBugTrackerAndBug(bug_url)
        except NoBugTrackerFound:
            # There's no bugtracker registered with the given URL, so we
            # don't need to worry about finding products using it.
            bugtracker = None

        if bugtracker is None:
            return
        count = bugtracker.products.count()
        if count > 0 and count <= self.MAX_PRODUCTS_TO_DISPLAY:
            self.existing_products = bugtracker.products
        elif count > self.MAX_PRODUCTS_TO_DISPLAY:
            name_matches = getUtility(IProductSet).search(
                self.request.form.get('field.name'))
            self.existing_products = bugtracker.products.intersect(
                name_matches).limit(self.MAX_PRODUCTS_TO_DISPLAY)
        else:
            # The bugtracker is registered in Launchpad but there are no
            # products using it at the moment.
            pass

    def setUpFields(self):
        """Setup an extra field with all products using the given bugtracker.

        This extra field is setup only if there is one or more products using
        that bugtracker.
        """
        super(BugAlsoAffectsProductWithProductCreationView, self).setUpFields()
        self._findProductsUsingGivenBugTrackerAndStoreThem()
        if self.existing_products is None or self.existing_products.count() < 1:
            # No need to setup any extra fields.
            return

        terms = []
        for product in self.existing_products:
            terms.append(SimpleTerm(product, product.name, product.title))
        existing_product = form.FormField(
            Choice(__name__='existing_product',
                   title=_("Existing project"), required=True,
                   vocabulary=SimpleVocabulary(terms)),
            custom_widget=self.custom_widgets['existing_product'])
        self.form_fields += form.Fields(existing_product)
        if 'field.existing_product' not in self.request.form:
            # This is the first time the form is being submitted, so the
            # request doesn't contain a value for the existing_product
            # widget and thus we'll end up rendering an error message around
            # said widget unless we sneak a value for it in our request.
            self.request.form['field.existing_product'] = terms[0].token

    def validate_existing_product(self, action, data):
        """Check if the chosen project is not already affected by this bug."""
        self._validate(action, data)
        project = data.get('existing_product')
        try:
            valid_upstreamtask(self.context.bug, project)
        except WidgetsError, errors:
            for error in errors:
                self.setFieldError('existing_product', error.snippet())

    @action('Use Existing Project', name='use_existing_product',
            validator=validate_existing_product)
    def use_existing_product_action(self, action, data):
        """Record the chosen project as being affected by this bug.

        Also creates a bugwatch for the given remote bug.
        """
        data['product'] = data['existing_product']
        self._createBugTaskAndWatch(data)

    @action('Continue', name='continue')
    def continue_action(self, action, data):
        """Create a new product and a bugtask for this bug on that product.

        If the URL of the remote bug given is of a bugtracker used by any
        other products registered in Launchpad, then we show these products to
        the user and ask if he doesn't want to create the task in one of them.
        """
        if self.existing_products and not self.request.form.get('create_new'):
            # Present the projects using that bugtracker to the user as
            # possible options to report the bug on. If there are too many
            # projects using that bugtracker then show only the ones that
            # match the text entered as the project's name
            return

        product = getUtility(IProductSet).createProduct(
            self.user, data['name'], data['displayname'], data['displayname'],
            data['summary'])
        data['product'] = product
        self._createBugTaskAndWatch(data)

    def _createBugTaskAndWatch(self, data):
        """Create a bugtask and bugwatch on the chosen product.

        This is done by manually calling the main_action() method of
        UpstreamBugTrackerCreationStep and ProductBugTaskCreationStep.

        This method also sets self.next_url to the URL of the newly added
        bugtask.
        """
        view = UpstreamBugTrackerCreationStep(self.context, self.request)
        view.main_action(data)

        view = ProductBugTaskCreationStep(self.context, self.request)
        view.main_action(data)

        data['product'].bugtracker = view.task_added.bugwatch.bugtracker
        self.next_url = canonical_url(view.task_added)

