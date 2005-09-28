# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Widgets related to IBugTask."""

__metaclass__ = type

from zope.component import getUtility
from zope.interface import implements
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.form.interfaces import IInputWidget, InputErrors, ConversionError
from zope.schema.interfaces import ValidationError
from zope.app.form import Widget

from canonical.launchpad.interfaces import ILaunchBag
from canonical.widgets.popup import SinglePopupWidget
from canonical.widgets.exception import WidgetInputError

class BugTaskAssigneeWidget(Widget):
    """A widget for setting the assignee on an IBugTask."""

    implements(IInputWidget)

    __call__ = ViewPageTemplateFile(
        "../launchpad/templates/bugtask-assignee-widget.pt")

    def __init__(self, context, request):
        Widget.__init__(self, context, request)

        # This is a radio button widget so, since at least one radio
        # button will always be selected (and thus there will always
        # be input provided), we set required to False, to avoid
        # unnecessary 'required' UI connotations.
        #
        # See zope.app.form.interfaces.IInputWidget.
        self.required = False

        self.assignee_chooser_widget = SinglePopupWidget(
            context, context.vocabulary, request)
        self.assignee_chooser_widget.onKeyPress = "selectAssignTo(this, event)"

        # Set some values that will be used as values for the input
        # widgets.
        self.assigned_to = "assigned_to"
        self.assign_to_me = "assign_to_me"
        self.assign_to_nobody = "assign_to_nobody"
        self.assign_to = "assign_to"

    def validate(self):
        """See zope.app.form.interfaces.IInputWidget."""
        # If the user has chosen to assign this bug to somebody else,
        # ensure that they actually provided a valid input value for
        # the assignee field.
        if self.request.form.get(self.name + ".option") == self.assign_to:
            if not self.assignee_chooser_widget.hasInput():
                raise WidgetInputError(
                    self.name, self.label, ValidationError("Missing value for assignee"))

            try:
                # A ConversionError is expected if the user provides
                # an assignee value that doesn't exist in the
                # assignee_chooser_widget's vocabulary.
                self.assignee_chooser_widget.validate()
            except ConversionError:
                # Turn the ConversionError into a WidgetInputError.
                raise WidgetInputError(
                    self.assignee_chooser_widget.name,
                    self.assignee_chooser_widget.label,
                    ValidationError("Assignee not found"))

    def hasInput(self):
        """See zope.app.form.interfaces.IInputWidget."""
        field_name = self.name + ".option"
        return field_name in self.request.form

    def hasValidInput(self):
        """See zope.app.form.interfaces.IInputWidget."""
        try:
            self.validate()
            return True
        except InputErrors:
            return False

    def getInputValue(self):
        """See zope.app.form.interfaces.IInputWidget."""
        self.validate()

        form = self.request.form

        assignee_option = form.get(self.name + ".option")
        if assignee_option == self.assign_to:
            # The user has chosen to use the assignee chooser widget
            # to select an assignee.
            return self.assignee_chooser_widget.getInputValue()
        elif assignee_option == self.assign_to_me:
            # The user has choosen to 'take' this bug.
            return getUtility(ILaunchBag).user
        elif assignee_option == self.assigned_to:
            # This is effectively a no-op
            field = self.context
            bugtask = field.context
            return bugtask.assignee
        elif assignee_option == self.assign_to_nobody:
            return None

        raise WidgetInputError("Unknown assignee option chosen")

    def applyChanges(self, content):
        """See zope.app.form.interfaces.IInputWidget."""
        field = self.context
        value = self.getInputValue()

        if field.query(content, self) != value:
            field.set(content, value)
            return True
        else:
            return False

    def assignedToCurrentUser(self):
        """Is this IBugTask assigned to the currently logged in user?

        Returns True if yes, otherwise False.
        """
        current_user = getUtility(ILaunchBag).user
        if not current_user:
            return False

        field = self.context
        bugtask = field.context
        return current_user == bugtask.assignee

    def assignedToAnotherUser(self):
        """Is this IBugTask assigned to someone other than the current user?

        Returns True if yes, otherwise False.
        """
        field = self.context
        bugtask = field.context
        if not bugtask.assignee:
            # This IBugTask is not yet assigned to anyone.
            return False

        current_user = getUtility(ILaunchBag).user

        return current_user != bugtask.assignee

    def getAssigneeDisplayValue(self):
        """Return a display value for current IBugTask.assignee.

        If no IBugTask.assignee, return None.
        """
        field = self.context
        bugtask = field.context
        if bugtask.assignee:
            if bugtask.assignee.preferredemail is not None:
                return bugtask.assignee.preferredemail.email
            else:
                return bugtask.assignee.browsername

    def selectedRadioButton(self):
        """Return the radio button that should be selected.

        The return value will be one of:

            self.assigned_to
            self.assign_to_me
            self.assign_to_nobody
            self.assign_to
        """
        # Give form values in the request precedence in deciding which
        # radio button should be selected.
        selected_option = self.request.form.get(self.name + ".option")
        if selected_option:
            return selected_option

        # No value found in the request (e.g. the user might have just
        # clicked a link to arrive at this form), so let's figure out
        # which radio button makes sense to select. Note that
        # self.assign_to is no longer a possible return value, because
        # it doesn't make sense for this to be the selected radio
        # button when first entering the form.
        field = self.context
        bugtask = field.context
        assignee = bugtask.assignee
        if not assignee:
            return self.assign_to_nobody
        else:
            if assignee == getUtility(ILaunchBag).user:
                return self.assign_to_me
            else:
                return self.assigned_to

