# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Multiple step views."""

__metaclass__ = type
__all__ = [
    'MultiStepView',
    'StepView',
    ]


from zope.app.form.browser import TextWidget

from canonical.launchpad.webapp import (
    LaunchpadFormView, LaunchpadView, action, canonical_url, custom_widget)


class MultiStepView(LaunchpadView):
    """Meta-view for implementing a wizard-like multiple step views.

    This view implements a wizard-like workflow in which you specify the first
    step, and then each step is responsible for specifying the next one.  The
    next step should be None if we need to stay at the current step.

    Any views used as steps here must inherit from `StepView`.  The views are
    responsible for injecting state information into the request, for anything
    that subsequent views will need.
    """

    @property
    def step_one(self):
        """Return the view class for the first step in the wizard.

        :return: A subclass of `StepView`
        :rtype: `StepView`
        """
        raise NotImplementedError

    def initialize(self):
        """Initialize the view and handle stepping through sub-views."""
        view = self.step_one(self.context, self.request)
        # In fact we should be calling injectStepNameInRequest() after
        # initialize() in both cases, otherwise the form will be processed
        # when it's first rendered, thus showing warning/error messages before
        # the user submits it. For the first step, though, this won't happen
        # because the request won't contain the action name, but it also won't
        # contain the visited_steps key and thus the HTML won't contain the
        # hidden widget unless I inject before calling initialize().
        view.injectStepNameInRequest()
        view.initialize()
        while view.next_step is not None:
            view = view.next_step(self.context, self.request)
            view.initialize()
            view.injectStepNameInRequest()
        self.view = view

    def render(self):
        return self.view.render()


class StepView(LaunchpadFormView):
    """Base class for all steps in a mulit-step view.

    Subclasses must override `next_step`, `step_name` and `_field_names`.
    They must also define a `main_action()` method which processes the form
    data.

    If views want to do per-step validation, they should override
    `validateStep()`.

    If views want to change the label of their Continue button, they should
    override `main_action_label`.
    """
    custom_widget('visited_steps', TextWidget, visible=False)

    _field_names = []
    step_name = ''
    main_action_label = u'Continue'
    next_step = None

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
        """The action of the continue button.

        Check to see if the form should be processed.  If so, then
        `main_action()` is called.  Otherwise, it's the first time we're
        showing the step view and nothing will be processed.
        """
        if self.shouldProcess(data):
            return self.main_action(data)
        return None

    def validate(self, data):
        """Call `self.validateStep()` if the form should be processed.

        Subclasses /must not/ override this method.  They should override
        `validateStep()` if they have any custom validation they need to
        perform.
        """
        if self.shouldProcess(data):
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
            # We already visited this step, so there's no need to inject our
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
        return super(StepView, self).render()

    @property
    def cancel_url(self):
        """Return the URL for the current context, i.e. bug."""
        return canonical_url(self.context)
