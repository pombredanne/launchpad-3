# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Specification views."""

__metaclass__ = type

__all__ = [
    'NewSpecificationFromDistributionView',
    'NewSpecificationFromDistroSeriesView',
    'NewSpecificationFromProductView',
    'NewSpecificationFromProductSeriesView',
    'NewSpecificationFromProjectView',
    'NewSpecificationFromRootView',
    'NewSpecificationFromSprintView',
    'SpecificationActionMenu',
    'SpecificationContextMenu',
    'SpecificationEditMilestoneView',
    'SpecificationEditPeopleView',
    'SpecificationEditPriorityView',
    'SpecificationEditStatusView',
    'SpecificationEditView',
    'SpecificationEditWhiteboardView',
    'SpecificationGoalDecideView',
    'SpecificationGoalProposeView',
    'SpecificationLinkBranchView',
    'SpecificationNavigation',
    'SpecificationProductSeriesGoalProposeView',
    'SpecificationRetargetingView',
    'SpecificationSetView',
    'SpecificationSimpleView',
    'SpecificationSprintAddView',
    'SpecificationSupersedingView',
    'SpecificationTreePNGView',
    'SpecificationTreeImageTag',
    'SpecificationTreeDotOutput',
    'SpecificationView',
    ]

from operator import attrgetter
import os
from subprocess import (
    PIPE,
    Popen,
    )

from lazr.restful.interface import use_template
from lazr.restful.interfaces import (
    IFieldHTMLRenderer,
    IWebServiceClientRequest,
    )
from zope import component
from zope.app.form.browser import (
    TextAreaWidget,
    TextWidget,
    )
from zope.app.form.browser.itemswidgets import DropdownWidget
from zope.component import getUtility
from zope.error.interfaces import IErrorReportingUtility
from zope.formlib import form
from zope.formlib.form import Fields
from zope.interface import (
    implementer,
    Interface,
    )
from zope.schema import (
    Bool,
    Choice,
    )
from zope.schema.vocabulary import (
    SimpleTerm,
    SimpleVocabulary,
    )

from canonical.config import config
from canonical.launchpad import _
from canonical.launchpad.webapp import (
    canonical_url,
    LaunchpadView,
    Navigation,
    stepthrough,
    stepto,
    )
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.menu import (
    ContextMenu,
    enabled_with_permission,
    Link,
    NavigationMenu,
    )
from lp.app.browser.launchpad import AppFrontPageSearchView
from lp.app.browser.launchpadform import (
    action,
    custom_widget,
    LaunchpadEditFormView,
    LaunchpadFormView,
    safe_action,
    )
from lp.app.browser.lazrjs import (
    BooleanChoiceWidget,
    EnumChoiceWidget,
    InlinePersonEditPickerWidget,
    TextAreaEditorWidget,
    TextLineEditorWidget,
    )
from lp.app.browser.tales import (
    DateTimeFormatterAPI,
    format_link,
    )
from lp.blueprints.browser.specificationtarget import HasSpecificationsView
from lp.blueprints.enums import (
    NewSpecificationDefinitionStatus,
    SpecificationDefinitionStatus,
    SpecificationImplementationStatus,
    )
from lp.blueprints.errors import TargetAlreadyHasSpecification
from lp.blueprints.interfaces.specification import (
    ISpecification,
    ISpecificationSet,
    )
from lp.blueprints.interfaces.specificationbranch import ISpecificationBranch
from lp.blueprints.interfaces.sprintspecification import ISprintSpecification
from lp.code.interfaces.branchnamespace import IBranchNamespaceSet
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.product import IProduct
from lp.services.propertycache import cachedproperty


class INewSpecification(Interface):
    """A schema for a new specification."""

    use_template(ISpecification, include=[
        'name',
        'title',
        'specurl',
        'summary',
        'assignee',
        'drafter',
        'approver',
        ])

    definition_status = Choice(
        title=_('Definition Status'),
        vocabulary=NewSpecificationDefinitionStatus,
        default=NewSpecificationDefinitionStatus.NEW,
        description=_(
            "The current status of the process to define the "
            "feature and get approval for the implementation plan."))


class INewSpecificationProjectTarget(Interface):
    """A mixin schema for a new specification.

    Requires the user to specify a product from a given project.
    """
    target = Choice(
        title=_("For"),
        description=_("The project for which this proposal is being made."),
        required=True, vocabulary='ProjectProducts')


class INewSpecificationSeriesGoal(Interface):
    """A mixin schema for a new specification.

    Allows the user to propose the specification as a series goal.
    """
    goal = Bool(title=_('Propose for series goal'),
                description=_("Check this to indicate that you wish to "
                              "propose this blueprint as a series goal."),
                required=True, default=False)


class INewSpecificationSprint(Interface):
    """A mixin schema for a new specification.

    Allows the user to propose the specification for discussion at a sprint.
    """
    sprint = Choice(title=_("Propose for sprint"),
                    description=_("The sprint to which agenda this "
                                  "blueprint is being suggested."),
                    required=False, vocabulary='FutureSprint')


class INewSpecificationTarget(Interface):
    """A mixin schema for a new specification.

    Requires the user to specify a distribution or a product as a target.
    """
    use_template(ISpecification, include=['target'])


class NewSpecificationView(LaunchpadFormView):
    """An abstract view for creating a new specification."""

    page_title = 'Register a blueprint in Launchpad'
    label = "Register a new blueprint"

    @action(_('Register Blueprint'), name='register')
    def register(self, action, data):
        """Registers a new specification."""
        self.transform(data)
        spec = getUtility(ISpecificationSet).new(
            owner = self.user,
            name = data.get('name'),
            title = data.get('title'),
            specurl = data.get('specurl'),
            summary = data.get('summary'),
            product = data.get('product'),
            drafter = data.get('drafter'),
            assignee = data.get('assignee'),
            approver = data.get('approver'),
            distribution = data.get('distribution'),
            definition_status = data.get('definition_status'))
        # Propose the specification as a series goal, if specified.
        series = data.get('series')
        if series is not None:
            spec.proposeGoal(series, self.user)
        # Propose the specification as a sprint topic, if specified.
        sprint = data.get('sprint')
        if sprint is not None:
            spec.linkSprint(sprint, self.user)
        # Set the default value for the next URL.
        self._next_url = canonical_url(spec)

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    def transform(self, data):
        """Transforms the given form data.

        Called after the new specification form is submitted, but before the
        new specification is created.

        Ensures that the given data dictionary contains valid entries for each
        of the arguments in ISpecificationSet.new(), to be used when creating
        the new specification.

        Optionally provides values for the following additional keys:

        series: causes the new specification to be proposed as a series goal.
        sprint: causes the new specification to be proposed as a sprint topic.
        """
        raise NotImplementedError

    @property
    def next_url(self):
        """The next URL to redirect to after creating a new specification.

        The default implementation returns a URL for the new specification
        itself. Subclasses can override this behaviour by returning an
        alternative URL.
        """
        return self._next_url


class NewSpecificationFromTargetView(NewSpecificationView):
    """An abstract view for creating a specification from a target context.

    The context must correspond to a unique specification target.
    """

    schema = Fields(INewSpecification,
                    INewSpecificationSprint)


class NewSpecificationFromDistributionView(NewSpecificationFromTargetView):
    """A view for creating a specification from a distribution."""

    def transform(self, data):
        data['distribution'] = self.context


class NewSpecificationFromProductView(NewSpecificationFromTargetView):
    """A view for creating a specification from a product."""

    def transform(self, data):
        data['product'] = self.context


class NewSpecificationFromSeriesView(NewSpecificationFromTargetView):
    """An abstract view for creating a specification from a series."""

    schema = Fields(INewSpecification,
                    INewSpecificationSprint,
                    INewSpecificationSeriesGoal)

    def transform(self, data):
        if data['goal']:
            data['series'] = self.context


class NewSpecificationFromDistroSeriesView(NewSpecificationFromSeriesView):
    """A view for creating a specification from a distro series."""

    def transform(self, data):
        super(NewSpecificationFromDistroSeriesView, self).transform(data)
        data['distribution'] = self.context.distribution


class NewSpecificationFromProductSeriesView(NewSpecificationFromSeriesView):
    """A view for creating a specification from a product series."""

    def transform(self, data):
        super(NewSpecificationFromProductSeriesView, self).transform(data)
        data['product'] = self.context.product


class NewSpecificationFromNonTargetView(NewSpecificationView):
    """An abstract view for creating a specification outside a target context.

    The context may not correspond to a unique specification target. Hence
    sub-classes must define a schema requiring the user to specify a target.
    """

    def transform(self, data):
        data['distribution'] = IDistribution(data['target'], None)
        data['product'] = IProduct(data['target'], None)

    def validate(self, data):
        """Ensures that the name for the new specification is unique.

        The name must be unique within the context of the chosen target.
        """
        name = data.get('name')
        target = data.get('target')
        if name is not None and target is not None:
            if target.getSpecification(name):
                errormessage = INewSpecification['name'].errormessage
                self.setFieldError('name', errormessage % name)


class NewSpecificationFromProjectView(NewSpecificationFromNonTargetView):
    """A view for creating a specification from a project."""

    schema = Fields(INewSpecificationProjectTarget,
                    INewSpecification,
                    INewSpecificationSprint)


class NewSpecificationFromRootView(NewSpecificationFromNonTargetView):
    """A view for creating a specification from the root of Launchpad."""

    schema = Fields(INewSpecificationTarget,
                    INewSpecification,
                    INewSpecificationSprint)


class NewSpecificationFromSprintView(NewSpecificationFromNonTargetView):
    """A view for creating a specification from a sprint."""

    schema = Fields(INewSpecificationTarget,
                    INewSpecification)

    def transform(self, data):
        super(NewSpecificationFromSprintView, self).transform(data)
        data['sprint'] = self.context

    @property
    def next_url(self):
        return canonical_url(self.context)


class SpecificationNavigation(Navigation):

    usedfor = ISpecification

    @stepthrough('+subscription')
    def traverse_subscriptions(self, name):
        return self.context.getSubscriptionByName(name)

    @stepto('+branch')
    def traverse_branch(self):
        branch = getUtility(IBranchNamespaceSet).traverse(
            iter(self.request.stepstogo))
        return self.context.getBranchLink(branch)

    def traverse(self, name):
        # fallback to looking for a sprint with this name, with this feature
        # on the agenda
        return self.context.getSprintSpecification(name)


class SpecificationEditLinksMixin:

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        text = 'Change details'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def supersede(self):
        text = 'Mark superseded'
        return Link('+supersede', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def retarget(self):
        text = 'Re-target blueprint'
        return Link('+retarget', text, icon='edit')


class SpecificationActionMenu(NavigationMenu, SpecificationEditLinksMixin):

    usedfor = ISpecification
    facet = 'specifications'
    links = ('edit', 'supersede', 'retarget')


class SpecificationContextMenu(ContextMenu, SpecificationEditLinksMixin):

    usedfor = ISpecification
    links = ['edit', 'people', 'status', 'priority',
             'whiteboard', 'proposegoal',
             'milestone', 'requestfeedback', 'givefeedback', 'subscription',
             'addsubscriber',
             'linkbug', 'unlinkbug', 'linkbranch',
             'adddependency', 'removedependency',
             'dependencytree', 'linksprint', 'supersede',
             'retarget']

    def givefeedback(self):
        text = 'Give feedback'
        enabled = (self.user is not None and
                   bool(self.context.getFeedbackRequests(self.user)))
        return Link('+givefeedback', text, icon='edit', enabled=enabled)

    @enabled_with_permission('launchpad.Edit')
    def milestone(self):
        text = 'Target milestone'
        return Link('+milestone', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def people(self):
        text = 'Change people'
        return Link('+people', text, icon='edit')

    @enabled_with_permission('launchpad.Admin')
    def priority(self):
        text = 'Change priority'
        return Link('+priority', text, icon='edit')

    @enabled_with_permission('launchpad.AnyPerson')
    def requestfeedback(self):
        text = 'Request feedback'
        return Link('+requestfeedback', text, icon='add')

    @enabled_with_permission('launchpad.AnyPerson')
    def proposegoal(self):
        text = 'Propose as goal'
        if self.context.goal is not None:
            text = 'Modify goal'
        if self.context.distribution is not None:
            link = '+setdistroseries'
        elif self.context.product is not None:
            link = '+setproductseries'
        else:
            raise AssertionError(
                'Unknown target on specification "%s".' % self.context.name)
        return Link(link, text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def status(self):
        text = 'Change status'
        return Link('+status', text, icon='edit')

    def addsubscriber(self):
        """Return the 'Subscribe someone else' Link."""
        text = 'Subscribe someone else'
        return Link('+addsubscriber', text, icon='add')

    def subscription(self):
        """Return the 'Edit Subscription' Link."""
        user = self.user
        if user is None:
            return Link('+subscribe', 'Edit subscription', icon='edit')

        if self.context.isSubscribed(user):
            return Link(
                '+subscription/%s' % user.name,
                'Update subscription', icon='edit')
        else:
            return Link('+subscribe', 'Subscribe', icon='add')

    @enabled_with_permission('launchpad.AnyPerson')
    def linkbug(self):
        text = 'Link a bug report'
        return Link('+linkbug', text, icon='add')

    @enabled_with_permission('launchpad.AnyPerson')
    def unlinkbug(self):
        text = 'Unlink a bug'
        enabled = bool(self.context.bugs)
        return Link('+unlinkbug', text, icon='remove', enabled=enabled)

    @enabled_with_permission('launchpad.Edit')
    def adddependency(self):
        text = 'Add dependency'
        return Link('+linkdependency', text, icon='add')

    @enabled_with_permission('launchpad.Edit')
    def removedependency(self):
        text = 'Remove dependency'
        enabled = bool(self.context.dependencies)
        return Link('+removedependency', text, icon='remove', enabled=enabled)

    def dependencytree(self):
        text = 'Show dependencies'
        enabled = (bool(self.context.dependencies) or
                   bool(self.context.blocked_specs))
        return Link('+deptree', text, icon='info', enabled=enabled)

    @enabled_with_permission('launchpad.AnyPerson')
    def linksprint(self):
        text = 'Propose for sprint'
        return Link('+linksprint', text, icon='add')

    @enabled_with_permission('launchpad.AnyPerson')
    def whiteboard(self):
        text = 'Edit whiteboard'
        return Link('+whiteboard', text, icon='edit')

    @enabled_with_permission('launchpad.AnyPerson')
    def linkbranch(self):
        if self.context.linked_branches.count() > 0:
            text = 'Link to another branch'
        else:
            text = 'Link a related branch'
        return Link('+linkbranch', text, icon='add')


class SpecificationSimpleView(LaunchpadView):
    """Used to render portlets and listing items that need browser code."""

    @cachedproperty
    def feedbackrequests(self):
        if self.user is None:
            return []
        return list(self.context.getFeedbackRequests(self.user))

    @cachedproperty
    def has_dep_tree(self):
        return self.context.dependencies or self.context.blocked_specs

    @cachedproperty
    def linked_branches(self):
        return [branch_link for branch_link in self.context.linked_branches
                if check_permission('launchpad.View', branch_link.branch)]

    @cachedproperty
    def bug_links(self):
        return self.context.getLinkedBugTasks(self.user)


class SpecificationView(SpecificationSimpleView):
    """Used to render the main view of a specification."""

    @property
    def label(self):
        return self.context.title

    @property
    def page_title(self):
        return self.label

    def initialize(self):
        # The review that the user requested on this spec, if any.
        self.notices = []

        if not self.user:
            return

        if self.feedbackrequests:
            msg = "You have %d feedback request(s) on this blueprint."
            msg %= len(self.feedbackrequests)
            self.notices.append(msg)

    @property
    def approver_widget(self):
        return InlinePersonEditPickerWidget(
            self.context, ISpecification['approver'],
            format_link(self.context.approver),
            header='Change approver', edit_view='+people',
            step_title='Select a new approver')

    @property
    def drafter_widget(self):
        return InlinePersonEditPickerWidget(
            self.context, ISpecification['drafter'],
            format_link(self.context.drafter),
            header='Change drafter', edit_view='+people',
            step_title='Select a new drafter')

    @property
    def assignee_widget(self):
        return InlinePersonEditPickerWidget(
            self.context, ISpecification['assignee'],
            format_link(self.context.assignee),
            header='Change assignee', edit_view='+people',
            step_title='Select a new assignee')

    @property
    def definition_status_widget(self):
        return EnumChoiceWidget(
            self.context, ISpecification['definition_status'],
            header='Change definition status to', edit_view='+status',
            edit_title='Change definition status',
            css_class_prefix='specstatus')

    @property
    def implementation_status_widget(self):
        return EnumChoiceWidget(
            self.context, ISpecification['implementation_status'],
            header='Change implementation status to', edit_view='+status',
            edit_title='Change implementation status',
            css_class_prefix='specdelivery')

    @property
    def priority_widget(self):
        return EnumChoiceWidget(
            self.context, ISpecification['priority'],
            header='Change priority to', edit_view='+priority',
            edit_title='Change priority',
            css_class_prefix='specpriority')

    @property
    def title_widget(self):
        field = ISpecification['title']
        title = "Edit the blueprint title"
        return TextLineEditorWidget(self.context, field, title, 'h1')

    @property
    def summary_widget(self):
        """The summary as a widget."""
        return TextAreaEditorWidget(
            self.context, ISpecification['summary'], title="")

    @property
    def whiteboard_widget(self):
        """The description as a widget."""
        return TextAreaEditorWidget(
            self.context, ISpecification['whiteboard'], title="Whiteboard",
            edit_view='+whiteboard', edit_title='Edit whiteboard',
            hide_empty=False)

    @property
    def direction_widget(self):
        return BooleanChoiceWidget(
            self.context, ISpecification['direction_approved'],
            tag='span',
            false_text='Needs approval',
            true_text='Approved',
            header='Change approval of basic direction')


class SpecificationEditSchema(ISpecification):
    """Provide overrides for the implementaion and definition status."""

    definition_status = Choice(
        title=_('Definition Status'), required=True,
        vocabulary=SpecificationDefinitionStatus,
        default=SpecificationDefinitionStatus.NEW,
        description=_(
            "The current status of the process to define the "
            "feature and get approval for the implementation plan."))

    implementation_status = Choice(
        title=_("Implementation Status"), required=True,
        default=SpecificationImplementationStatus.UNKNOWN,
        vocabulary=SpecificationImplementationStatus,
        description=_(
            "The state of progress being made on the actual "
            "implementation or delivery of this feature."))


class SpecificationEditView(LaunchpadEditFormView):

    schema = SpecificationEditSchema
    field_names = ['name', 'title', 'specurl', 'summary', 'whiteboard']
    label = 'Edit specification'
    custom_widget('summary', TextAreaWidget, height=5)
    custom_widget('whiteboard', TextAreaWidget, height=10)
    custom_widget('specurl', TextWidget, width=60)

    @property
    def adapters(self):
        """See `LaunchpadFormView`"""
        return {SpecificationEditSchema: self.context}

    @action(_('Change'), name='change')
    def change_action(self, action, data):
        old_status = self.context.lifecycle_status
        self.updateContextFromData(data)
        # We need to ensure that resolution is recorded if the spec is now
        # resolved.
        new_status = self.context.lifecycle_status
        if new_status != old_status:
            self.request.response.addNotification(
                'Blueprint is now considered "%s".' % new_status.title)
        self.next_url = canonical_url(self.context)


class SpecificationEditWhiteboardView(SpecificationEditView):
    label = 'Edit specification status whiteboard'
    field_names = ['whiteboard']
    custom_widget('whiteboard', TextAreaWidget, height=15)


class SpecificationEditPeopleView(SpecificationEditView):
    label = 'Change the people involved'
    field_names = ['assignee', 'drafter', 'approver', 'whiteboard']


class SpecificationEditPriorityView(SpecificationEditView):
    label = 'Change priority'
    field_names = ['priority', 'direction_approved', 'whiteboard']

    @property
    def extra_info(self):
        return ('The priority should reflect the views of the coordinating '
                'team of %s.' % self.context.target.displayname)


class SpecificationEditStatusView(SpecificationEditView):
    label = 'Change status'
    field_names = ['definition_status', 'implementation_status', 'whiteboard']


class SpecificationEditMilestoneView(SpecificationEditView):
    label = 'Target to a milestone'
    field_names = ['milestone', 'whiteboard']

    @property
    def extra_info(self):
        return ("Select the milestone of %s in which you would like this "
                "feature to be implemented."
                % self.context.target.displayname)


class SpecificationGoalProposeView(LaunchpadEditFormView):
    schema = ISpecification
    label = 'Target to a distribution series'
    field_names = ['distroseries', 'whiteboard']
    custom_widget('whiteboard', TextAreaWidget, height=5)

    @property
    def initial_values(self):
        return {
            'productseries': self.context.productseries,
            'distroseries': self.context.distroseries,
            'whiteboard': self.context.whiteboard,
            }

    @action('Continue', name='continue')
    def continue_action(self, action, data):
        self.context.whiteboard = data['whiteboard']
        self.context.proposeGoal(data['distroseries'], self.user)
        self.next_url = canonical_url(self.context)

    @property
    def cancel_url(self):
        return canonical_url(self.context)


class SpecificationProductSeriesGoalProposeView(SpecificationGoalProposeView):
    label = 'Target to a product series'
    field_names = ['productseries', 'whiteboard']

    @action('Continue', name='continue')
    def continue_action(self, action, data):
        self.context.whiteboard = data['whiteboard']
        self.context.proposeGoal(data['productseries'], self.user)
        self.next_url = canonical_url(self.context)

    @property
    def cancel_url(self):
        return canonical_url(self.context)


class SpecificationGoalDecideView(LaunchpadFormView):
    """View used to allow the drivers of a series to accept
    or decline the spec as a goal for that series. Typically they would use
    the multi-select goalset view on their series, but it's also
    useful for them to have this one-at-a-time view on the spec itself.
    """

    schema = Interface
    field_names = []

    @property
    def label(self):
        return _("Accept as %s series goal?") % self.context.goal.name

    @action(_('Accept'), name='accept')
    def accept_action(self, action, data):
        self.context.acceptBy(self.user)

    @action(_('Decline'), name='decline')
    def decline_action(self, action, data):
        self.context.declineBy(self.user)

    @property
    def next_url(self):
        return canonical_url(self.context)

    cancel_url = next_url


class SpecificationRetargetingView(LaunchpadFormView):

    schema = ISpecification
    field_names = ['target']
    label = _('Move this blueprint to a different project')

    def validate(self, data):
        """Ensure that the target is valid and that there is not
        already a blueprint with the same name as this one for the
        given target.
        """

        target = data.get('target')

        if target is None:
            self.setFieldError('target',
                "There is no project with the name '%s'. "
                "Please check that name and try again." %
                self.request.form.get("field.target"))
            return

        try:
            self.context.validateMove(target)
        except TargetAlreadyHasSpecification:
            self.setFieldError('target',
                'There is already a blueprint with this name for %s. '
                'Please change the name of this blueprint and try again.' %
                target.displayname)

    @action(_('Retarget Blueprint'), name='retarget')
    def retarget_action(self, action, data):
        self.context.retarget(data['target'])
        self._nextURL = canonical_url(self.context)

    @property
    def next_url(self):
        return self._nextURL

    @property
    def cancel_url(self):
        return canonical_url(self.context)


class SupersededByWidget(DropdownWidget):
    """Custom select widget for specification superseding.

    This is just a standard DropdownWidget with the (no value) text
    rendered as something meaningful to the user, as per Bug #4116.

    TODO: This should be replaced with something more scalable as there
    is no upper limit to the number of specifications.
    -- StuartBishop 20060704
    """
    _messageNoValue = _("(Not Superseded)")


class SpecificationSupersedingView(LaunchpadFormView):
    schema = ISpecification
    field_names = ['superseded_by']
    label = _('Mark blueprint superseded')
    custom_widget('superseded_by', SupersededByWidget)

    @property
    def initial_values(self):
        return {
            'superseded_by': self.context.superseded_by,
            }

    def setUpFields(self):
        """Override the setup to define own fields."""
        if self.context.target is None:
            raise AssertionError("No target found for this spec.")
        specs = sorted(self.context.target.specifications(),
                       key=attrgetter('name'))
        terms = [SimpleTerm(spec, spec.name, spec.title)
                 for spec in specs if spec != self.context]

        self.form_fields = form.Fields(
            Choice(
                __name__='superseded_by',
                title=_("Superseded by"),
                vocabulary=SimpleVocabulary(terms),
                required=False,
                description=_(
                    "The blueprint which supersedes this one. Note "
                    "that selecting a blueprint here and pressing "
                    "Continue will change the blueprint status "
                    "to Superseded.")),
            render_context=self.render_context)

    @action(_('Continue'), name='supersede')
    def supersede_action(self, action, data):
        # Store some shorter names to avoid line-wrapping.
        SUPERSEDED = SpecificationDefinitionStatus.SUPERSEDED
        NEW = SpecificationDefinitionStatus.NEW
        self.context.superseded_by = data['superseded_by']
        # XXX: salgado, 2010-11-24, bug=680880: This logic should be in model
        # code.
        if data['superseded_by'] is not None:
            # set the state to superseded
            self.context.definition_status = SUPERSEDED
        else:
            # if the current state is SUPERSEDED and we are now removing the
            # superseded-by then we should move this spec back into the
            # drafting pipeline by resetting its status to NEW
            if self.context.definition_status == SUPERSEDED:
                self.context.definition_status = NEW
        newstate = self.context.updateLifecycleStatus(self.user)
        if newstate is not None:
            self.request.response.addNotification(
                'Blueprint is now considered "%s".' % newstate.title)
        self.next_url = canonical_url(self.context)

    @property
    def cancel_url(self):
        return canonical_url(self.context)


class SpecGraph:
    """A directed linked graph of nodes representing spec dependencies."""

    # We want to be able to test SpecGraph and SpecGraphNode without setting
    # up canonical_urls.  This attribute is used by tests to generate URLs for
    # nodes without calling canonical_url.
    # The pattern is either None (meaning use canonical_url) or a string
    # containing one '%s' replacement marker.
    url_pattern_for_testing = None

    def __init__(self):
        self.nodes = set()
        self.edges = set()
        self.root_node = None

    def newNode(self, spec, root=False):
        """Return a new node based on the given spec.

        If root=True, make this the root node.

        There can be at most one root node set.
        """
        assert self.getNode(spec.name) is None, (
            "A spec called %s is already in the graph" % spec.name)
        node = SpecGraphNode(spec, root=root,
                url_pattern_for_testing=self.url_pattern_for_testing)
        self.nodes.add(node)
        if root:
            assert not self.root_node
            self.root_node = node
        return node

    def getNode(self, name):
        """Return the node with the given name.

        Return None if there is no such node.
        """
        # Efficiency: O(n)
        for node in self.nodes:
            if node.name == name:
                return node
        return None

    def newOrExistingNode(self, spec):
        """Return the node for the spec.

        If there is already a node for spec.name, return that node.
        Otherwise, create a new node for the spec, and return that.
        """
        node = self.getNode(spec.name)
        if node is None:
            node = self.newNode(spec)
        return node

    def link(self, from_node, to_node):
        """Form a direction link from from_node to to_node."""
        assert from_node in self.nodes
        assert to_node in self.nodes
        assert (from_node, to_node) not in self.edges
        self.edges.add((from_node, to_node))

    def addDependencyNodes(self, spec):
        """Add nodes for the specs that the given spec depends on,
        transitively.
        """
        get_related_specs_fn = attrgetter('dependencies')

        def link_nodes_fn(node, dependency):
            self.link(dependency, node)
        self.walkSpecsMakingNodes(spec, get_related_specs_fn, link_nodes_fn)

    def addBlockedNodes(self, spec):
        """Add nodes for specs that the given spec blocks, transitively."""
        get_related_specs_fn = attrgetter('blocked_specs')

        def link_nodes_fn(node, blocked_spec):
            self.link(node, blocked_spec)
        self.walkSpecsMakingNodes(spec, get_related_specs_fn, link_nodes_fn)

    def walkSpecsMakingNodes(self, spec, get_related_specs_fn, link_nodes_fn):
        """Walk the specs, making and linking nodes.

        Examples of functions to use:

        get_related_specs_fn = lambda spec: spec.blocked_specs

        def link_nodes_fn(node, related):
            graph.link(node, related)
        """
        # This is a standard pattern for "flattening" a recursive algorithm.
        to_search = set([spec])
        visited = set()
        while to_search:
            current_spec = to_search.pop()
            visited.add(current_spec)
            node = self.newOrExistingNode(current_spec)
            related_specs = set(get_related_specs_fn(current_spec))
            for related_spec in related_specs:
                link_nodes_fn(node, self.newOrExistingNode(related_spec))
            to_search.update(related_specs.difference(visited))

    def getNodesSorted(self):
        """Return a list of all nodes, sorted by name."""
        return sorted(self.nodes, key=attrgetter('name'))

    def getEdgesSorted(self):
        """Return a list of all edges, sorted by name.

        An edge is a tuple (from_node, to_node).
        """
        return sorted(self.edges,
            key=lambda (from_node, to_node): (from_node.name, to_node.name))

    def listNodes(self):
        """Return a string of diagnostic output of nodes and edges.

        Used for debugging and in unit tests.
        """
        L = []
        edges = self.getEdgesSorted()
        if self.root_node:
            L.append('Root is %s' % self.root_node)
        else:
            L.append('Root is undefined')
        for node in self.getNodesSorted():
            L.append('%s:' % node)
            to_nodes = [to_node for from_node, to_node in edges
                        if from_node == node]
            L += ['    %s' % to_node.name for to_node in to_nodes]
        return '\n'.join(L)

    def getDOTGraphStatement(self):
        """Return a unicode string that is the DOT representation of this
        graph.

        graph : [ strict ] (graph | digraph) [ ID ] '{' stmt_list '}'
        stmt_list : [ stmt [ ';' ] [ stmt_list ] ]
        stmt : node_stmt | edge_stmt | attr_stmt | ID '=' ID | subgraph

        """
        graphname = 'deptree'
        graph_attrs = dict(
            mode='hier',
            # bgcolor='transparent',  # Fails with graphviz-cairo.
            bgcolor='#ffffff',  # Same as Launchpad page background.
            size='9.2,9',  # Width fits of 2 col layout, 1024x768.
            ratio='compress',
            ranksep=0.25,
            nodesep=0.01  # Separation between nodes
            )

        # Global node and edge attributes.
        node_attrs = dict(
            fillcolor='white',
            style='filled',
            fontname='Sans',
            fontsize=11
            )
        edge_attrs = dict(arrowhead='normal')

        L = []
        L.append('digraph %s {' % to_DOT_ID(graphname))
        L.append('graph')
        L.append(dict_to_DOT_attrs(graph_attrs))
        L.append('node')
        L.append(dict_to_DOT_attrs(node_attrs))
        L.append('edge')
        L.append(dict_to_DOT_attrs(edge_attrs))
        for node in self.getNodesSorted():
            L.append(node.getDOTNodeStatement())
        for from_node, to_node in self.getEdgesSorted():
            L.append('%s -> %s' % (
                to_DOT_ID(from_node.name), to_DOT_ID(to_node.name)))
        L.append('}')
        return u'\n'.join(L)


class SpecificationSprintAddView(LaunchpadFormView):

    schema = ISprintSpecification
    label = _("Propose specification for meeting agenda")
    field_names = ["sprint"]
    # ISprintSpecification.sprint is a read-only field, so we need to set
    # for_input to True here to ensure it's rendered as an input widget.
    for_input = True

    @action(_('Continue'), name='continue')
    def continue_action(self, action, data):
        self.context.linkSprint(data["sprint"], self.user)
        self.next_url = canonical_url(self.context)

    @property
    def cancel_url(self):
        return canonical_url(self.context)


class SpecGraphNode:
    """Node in the spec dependency graph.

    A SpecGraphNode object has various display-related properties.
    """

    def __init__(self, spec, root=False, url_pattern_for_testing=None):
        self.name = spec.name
        if url_pattern_for_testing:
            self.URL = url_pattern_for_testing % self.name
        else:
            self.URL = canonical_url(spec)
        self.isRoot = root
        if self.isRoot:
            self.color = 'red'
        elif spec.is_complete:
            self.color = 'grey'
        else:
            self.color = 'black'
        self.comment = spec.title
        self.label = self.makeLabel(spec)
        self.tooltip = spec.title

    def makeLabel(self, spec):
        """Return a label for the spec."""
        if spec.assignee:
            label = '%s\n(%s)' % (spec.name, spec.assignee.name)
        else:
            label = spec.name
        return label

    def __str__(self):
        return '<%s>' % self.name

    def getDOTNodeStatement(self):
        """Return this node's data as a DOT unicode.

        This fills in the node_stmt in the DOT BNF:
        http://www.graphviz.org/doc/info/lang.html

        node_stmt : node_id [ attr_list ]
        node_id : ID [ port ]
        attr_list : '[' [ a_list ] ']' [ attr_list ]
        a_list  : ID [ '=' ID ] [ ',' ] [ a_list ]
        port : ':' ID [ ':' compass_pt ] | ':' compass_pt
        compass_pt : (n | ne | e | se | s | sw | w | nw)

        We don't care about the [ port ] part.

        """
        attrnames = ['color', 'comment', 'label', 'tooltip']
        if not self.isRoot:
            # We want to have links in the image map for all nodes
            # except the one that were currently on the page of.
            attrnames.append('URL')
        attrdict = dict((name, getattr(self, name)) for name in attrnames)
        return u'%s\n%s' % (to_DOT_ID(self.name), dict_to_DOT_attrs(attrdict))


def dict_to_DOT_attrs(some_dict, indent='    '):
    r"""Convert some_dict to unicode DOT attrs output.

    attr_list : '[' [ a_list ] ']' [ attr_list ]
    a_list  : ID [ '=' ID ] [ ',' ] [ a_list ]

    The attributes are sorted by dict key.
    """
    if not some_dict:
        return u''
    L = []
    L.append('[')
    for key, value in sorted(some_dict.items()):
        L.append('%s=%s,' % (to_DOT_ID(key), to_DOT_ID(value)))
    # Remove the trailing comma from the last attr.
    lastitem = L.pop()
    L.append(lastitem[:-1])
    L.append(']')
    return u'\n'.join('%s%s' % (indent, line) for line in L)


def to_DOT_ID(value):
    r"""Accept a value and return the DOT escaped version.

    The returned value is always a unicode string.

    >>> to_DOT_ID(u'foo " bar \n')
    u'"foo \\" bar \\n"'

    """
    if isinstance(value, str):
        unitext = unicode(value, encoding='ascii')
    else:
        unitext = unicode(value)
    output = unitext.replace(u'"', u'\\"')
    output = output.replace(u'\n', u'\\n')
    return u'"%s"' % output


class ProblemRenderingGraph(Exception):
    """There was a problem rendering the graph."""


class SpecificationTreeGraphView(LaunchpadView):
    """View for displaying the dependency tree as a PNG with image map."""

    def makeSpecGraph(self):
        """Return a SpecGraph object rooted on the spec that is self.context.
        """
        graph = SpecGraph()
        graph.newNode(self.context, root=True)
        graph.addDependencyNodes(self.context)
        graph.addBlockedNodes(self.context)
        return graph

    def getDotFileText(self):
        """Return a unicode string of the dot file text."""
        specgraph = self.makeSpecGraph()
        return specgraph.getDOTGraphStatement()

    def renderGraphvizGraph(self, format):
        """Return graph data in the appropriate format.

        Shell out to `dot` to do the work.
        Raise ProblemRenderingGraph exception if `dot` gives any error output.
        """
        assert format in ('png', 'cmapx')
        input = self.getDotFileText().encode('UTF-8')
        # XXX sinzui 2008-04-03 bug=211568:
        # This use of subprocess.Popen is far from ideal. There is extra
        # risk of getting an OSError, or an command line issue that we
        # represent as a ProblemRenderingGraph. We need python bindings
        # to make the PNG/cmapx.
        cmd = 'unflatten -l 2 | dot -T%s' % format
        process = Popen(
            cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE,
            close_fds=True)
        process.stdin.write(input)
        process.stdin.close()
        output = process.stdout.read()
        err = process.stderr.read()
        if err:
            raise ProblemRenderingGraph(err, output)
        return output


def log_oops(error, request):
    """Log an oops report without raising an error."""
    info = (error.__class__, error, None)
    globalErrorUtility = getUtility(IErrorReportingUtility)
    globalErrorUtility.raising(info, request)


here = os.path.dirname(__file__)


class SpecificationTreePNGView(SpecificationTreeGraphView):

    fail_over_image_path = os.path.join(
        config.root, 'lib', 'canonical', 'launchpad', 'icing',
        'blueprints-deptree-error.png')

    def render(self):
        """Render a PNG displaying the specification dependency graph."""
        try:
            image = self.renderGraphvizGraph('png')
            self.request.response.setHeader('Content-type', 'image/png')
        except (ProblemRenderingGraph, OSError), error:
            # The subprocess or command can raise errors that might not
            # occur if we used a Python bindings for GraphViz. Instead of
            # sending the generated image, return the fail-over image
            # that explains there was a problem.
            log_oops(error, self.request)
            try:
                fail_over_image = open(self.fail_over_image_path, 'rb')
                image = fail_over_image.read()
            finally:
                fail_over_image.close()
        return image


class SpecificationTreeImageTag(SpecificationTreeGraphView):

    def render(self):
        """Render the image and image map tags for this dependency graph."""
        try:
            image_map = self.renderGraphvizGraph('cmapx').decode('UTF-8')
        except (ProblemRenderingGraph, OSError), error:
            # The subprocess or command can raise errors that might not
            # occur if we used a Python bindings for GraphViz. Instead
            # of rendering an image map, return an explanation that the
            # image's links are broken.
            log_oops(error, self.request)
            if isinstance(error, OSError):
                # An OSError can be random. The image map may generate
                # if the user reloads the page.
                extra_help = u' Reload the page to link the image.'
            else:
                extra_help = u''
            image_map = (
                u'<p class="error message">'
                u'There was an error linking the dependency tree to its '
                u'specs.' + extra_help + u'</p>')
        return (u'<img src="deptree.png" usemap="#deptree" />\n' + image_map)


class SpecificationTreeDotOutput(SpecificationTreeGraphView):

    def render(self):
        """Render the dep tree as a DOT file.

        This is useful for experimenting with the node layout offline.
        """
        self.request.response.setHeader('Content-type', 'text/plain')
        return self.getDotFileText()


class SpecificationLinkBranchView(LaunchpadFormView):
    """A form used to link a branch to this specification."""

    schema = ISpecificationBranch
    field_names = ['branch']
    label = _('Link branch to blueprint')

    def validate(self, data):
        branch = data.get('branch')
        if branch:
            branchlink = self.context.getBranchLink(branch)
            if branchlink is not None:
                self.setFieldError('branch', 'This branch has already '
                                   'been linked to the blueprint')

    @action(_('Continue'), name='continue')
    def continue_action(self, action, data):
        self.context.linkBranch(branch=data['branch'],
                                registrant=self.user)

    @property
    def next_url(self):
        return canonical_url(self.context)

    @property
    def cancel_url(self):
        return canonical_url(self.context)


class SpecificationSetView(AppFrontPageSearchView, HasSpecificationsView):
    """View for the Blueprints index page."""

    label = 'Blueprints'

    @safe_action
    @action('Find blueprints', name="search")
    def search_action(self, action, data):
        """Redirect to the proper search page based on the scope widget."""
        # For the scope to be absent from the form, the user must
        # build the query string themselves - most likely because they
        # are a bot. In that case we just assume they want to search
        # all projects.
        scope = self.widgets['scope'].getScope()
        if scope is None or scope == 'all':
            # Use 'All projects' scope.
            url = '/'
        else:
            url = canonical_url(
                self.widgets['scope'].getInputValue())
        search_text = data['search_text']
        if search_text is not None:
            url += '?searchtext=' + search_text
        self.next_url = url


@component.adapter(ISpecification, Interface, IWebServiceClientRequest)
@implementer(IFieldHTMLRenderer)
def starter_xhtml_representation(context, field, request):
    """Render the starter as XHTML to populate the page using AJAX."""
    def render(value=None):
        # The value is a webservice link to the object, we want field value.
        starter = context.starter
        if starter is None:
            return ''
        date_formatter = DateTimeFormatterAPI(context.date_started)
        return "%s %s" % (
            format_link(starter), date_formatter.displaydate())
    return render


@component.adapter(ISpecification, Interface, IWebServiceClientRequest)
@implementer(IFieldHTMLRenderer)
def completer_xhtml_representation(context, field, request):
    """Render the completer as XHTML to populate the page using AJAX."""
    def render(value=None):
        # The value is a webservice link to the object, we want field value.
        completer = context.completer
        if completer is None:
            return ''
        date_formatter = DateTimeFormatterAPI(context.date_completed)
        return "%s %s" % (
            format_link(completer), date_formatter.displaydate())
    return render
