# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Widgets related to IBugTask."""

__metaclass__ = type

import os
from xml.sax.saxutils import escape

from zope.component import getUtility
from zope.interface import implements, Interface
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.form.browser.itemswidgets import RadioWidget
from zope.app.form.browser.widget import BrowserWidget, renderElement
from zope.app.form.interfaces import (
    IDisplayWidget, IInputWidget, InputErrors, WidgetInputError,
    ConversionError)
from zope.schema.interfaces import ValidationError, InvalidValue
from zope.app.form import Widget, CustomWidgetFactory
from zope.app.form.utility import setUpWidget

from canonical.launchpad import _
from canonical.launchpad.fields import URIField
from canonical.launchpad.interfaces import (
    IBugWatchSet, IDistributionSet, ILaunchBag, NoBugTrackerFound,
    NotFoundError, UnrecognizedBugTrackerURL)
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.interfaces import UnexpectedFormData
from canonical.widgets.itemswidgets import LaunchpadRadioWidget
from canonical.widgets.popup import SinglePopupWidget
from canonical.widgets.textwidgets import StrippedTextWidget, URIWidget

class BugTaskAssigneeWidget(Widget):
    """A widget for setting the assignee on an IBugTask."""

    implements(IInputWidget)

    __call__ = ViewPageTemplateFile(
        "../launchpad/templates/bugtask-assignee-widget.pt")

    def __init__(self, context, vocabulary, request):
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
        self.setUpNames()

    def setUpNames(self):
        """Set up the the names used by this widget."""
        self.assigned_to = "%s.assigned_to" % self.name
        self.assign_to_me = "%s.assign_to_me" % self.name
        self.assign_to_nobody = "%s.assign_to_nobody" % self.name
        self.assign_to = "%s.assign_to" % self.name
        self.assignee_chooser_widget.onKeyPress = (
            "selectWidget('%s', event)" % self.assign_to)

    def setPrefix(self, prefix):
        Widget.setPrefix(self, prefix)
        self.assignee_chooser_widget.setPrefix(prefix)
        self.setUpNames()

    def validate(self):
        """
        This method used to be part of zope.app.form.interfaces.IInputWidget
        in Zope 3.0, but is no longer part of the interface in Zope 3.2
        """
        # If the user has chosen to assign this bug to somebody else,
        # ensure that they actually provided a valid input value for
        # the assignee field.
        if self.request.form_ng.getOne(self.name + ".option") == self.assign_to:
            if not self.assignee_chooser_widget.hasInput():
                raise WidgetInputError(
                        self.name, self.label,
                        ValidationError("Missing value for assignee")
                        )
            if not self.assignee_chooser_widget.hasValidInput():
                raise WidgetInputError(
                        self.name, self.label,
                        ValidationError("Assignee not found")
                        )
            #try:
                # A ConversionError is expected if the user provides
                # an assignee value that doesn't exist in the
                # assignee_chooser_widget's vocabulary.
            #except ConversionError:
                # Turn the ConversionError into a WidgetInputError.
            #    raise WidgetInputError(
            #        self.assignee_chooser_widget.name,
            #        self.assignee_chooser_widget.label,
            #        ValidationError("Assignee not found"))

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

        form = self.request.form_ng

        assignee_option = form.getOne(self.name + ".option")
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
        assignee_field = self.context
        bugtask = assignee_field.context
        new_assignee = self.getInputValue()

        if bugtask.assignee != new_assignee:
            bugtask.transitionToAssignee(new_assignee)
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
            return bugtask.assignee.unique_displayname

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
        selected_option = self.request.form_ng.getOne(self.name + ".option")
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


class BugWatchEditForm(Interface):
    """Form field definition for the bug watch widget.

    Used to edit the bug watch on the bugtask edit page.
    """

    url = URIField(
        title=_('URL'), required=True,
        allowed_schemes=['http', 'https'],
        description=_("""The URL at which to view the remote bug."""))


class BugTaskBugWatchWidget(RadioWidget):
    """A widget for linking a bug watch to a bug task."""

    def __init__(self, field, vocabulary, request):
        RadioWidget.__init__(self, field, vocabulary, request)
        self.url_widget = CustomWidgetFactory(URIWidget)
        setUpWidget(
            self, 'url', BugWatchEditForm['url'], IInputWidget,
            context=field.context)
        self.setUpJavascript()

    def setUpJavascript(self):
        """Set up JS to select the "new bugwatch" option automatically."""
        select_js = "selectWidget('%s.%s', event)" % (
            self.name, self._new_bugwatch_value)
        self.url_widget.extra = 'onKeyPress="%s"' % select_js

    def setPrefix(self, prefix):
        RadioWidget.setPrefix(self, prefix)
        self.url_widget.setPrefix(prefix)
        self.setUpJavascript()

    _messageNoValue = "None, the status of the bug is updated manually."
    _new_bugwatch_value = 'NEW'

    def _toFieldValue(self, form_value):
        """Convert the textual token to a field value.

        If the form value is _new_bugwatch_value, create a new bug
        watch, otherwise look up an existing one.
        """
        if form_value == self._new_bugwatch_value:
            try:
                url = self.url_widget.getInputValue()
                bugtracker, remote_bug = getUtility(
                    IBugWatchSet).extractBugTrackerAndBug(url)
                bugtask = self.context.context
                return bugtask.bug.addWatch(
                    bugtracker, remote_bug, getUtility(ILaunchBag).user)
            except WidgetInputError, error:
                # Prefix the error with the widget name, since the error
                # will be display at the top of the page, and not right
                # next to the widget.
                raise WidgetInputError(
                    self.context.__name__, self.label,
                    'Remote Bug: %s' % error.doc())
            except (NoBugTrackerFound, UnrecognizedBugTrackerURL), error:
                raise WidgetInputError(
                    self.context.__name__, self.label,
                    'Invalid bug tracker URL.')
        else:
            return RadioWidget._toFieldValue(self, form_value)

    def _getFormValue(self):
        """Return the form value.

        We have to override this method in this class since the original
        one uses getInputValue(), which it shouldn't do.
        """
        if not self._renderedValueSet():
            return self.request.form_ng.getOne(self.name, self._missing)
        else:
            return self._toFormValue(self._data)

    def _div(self, cssClass, contents, **kw):
        """Don't render a div tag."""
        return contents

    def _joinButtonToMessage(self, option_tag, label, input_id):
        """Join the input tag with the label."""
        here = os.path.dirname(__file__)
        template_path = os.path.join(
            here, 'templates', 'bugtask-bugwatch-widget.txt')
        row_template = open(template_path).read()
        return row_template % {
            'input_tag': option_tag,
            'input_id': input_id,
            'input_label': label}

    #XXX: Bjorn Tillenius 2006-04-26:
    #     This method is mostly copied from RadioWidget.renderItems() and
    #     modified to actually work. RadioWidget.renderItems() should be
    #     fixed upstream so that we can override it and only do the last
    #     part locally, the part after "# Add an option for creating...".
    #     http://www.zope.org/Collectors/Zope3-dev/592
    def renderItems(self, value):
        """Render the items with with the correct radio button selected."""
        # XXX: Bjorn Tillenius 2006-04-26
        #      This works around the fact that we incorrectly gets the form
        #      value instead of a valid field value.
        if value == self._missing:
            value = self.context.missing_value
        elif (isinstance(value, basestring) and
              value != self._new_bugwatch_value):
            value = self._toFieldValue(value)
        # check if we want to select first item, the previously selected item
        # or the "no value" item.
        no_value = None
        if (value == self.context.missing_value
            and getattr(self, 'firstItem', False)
            and len(self.vocabulary) > 0
            and self.context.required):
                # Grab the first item from the iterator:
                values = [iter(self.vocabulary).next().value]
        elif value != self.context.missing_value:
            values = [value]
        else:
            # the "no value" option will be checked
            no_value = 'checked'
            values = []

        items = self.renderItemsWithValues(values)
        if not self.context.required:
            kwargs = {
                'index': None,
                'text': self.translate(self._messageNoValue),
                'value': '',
                'name': self.name,
                'cssClass': self.cssClass}
            if no_value:
                option = self.renderSelectedItem(**kwargs)
            else:
                option = self.renderItem(**kwargs)
            items.insert(0, option)

        # Add an option for creating a new bug watch.
        option_text = (
            '<div>URL: %s</div>' % self.url_widget())
        if value == self._new_bugwatch_value:
            option = self.renderSelectedItem(
                self._new_bugwatch_value, option_text,
                self._new_bugwatch_value, self.name, self.cssClass)
        else:
            option = self.renderItem(
                self._new_bugwatch_value, option_text,
                self._new_bugwatch_value, self.name, self.cssClass)
        items.append(option)

        return items

    def renderItem(self, index, text, value, name, cssClass):
        """Render an item.

        We override this method to use the _joinButtonToMessage method
        instead of the _joinButtonToMessageTemplate which doesn't have
        access to the id.
        """
        id = '%s.%s' % (name, index)
        elem = renderElement(u'input',
                             value=value,
                             name=name,
                             id=id,
                             cssClass=cssClass,
                             type='radio')
        return self._joinButtonToMessage(elem, text, input_id=id)

    def renderSelectedItem(self, index, text, value, name, cssClass):
        """Render a selected item.

        We override this method to use the _joinButtonToMessage method
        instead of the _joinButtonToMessageTemplate which doesn't have
        access to the id.
        """
        id = '%s.%s' % (name, index)
        elem = renderElement(u'input',
                             value=value,
                             name=name,
                             id=id,
                             cssClass=cssClass,
                             checked="checked",
                             type='radio')
        return self._joinButtonToMessage(elem, text, input_id=id)

    def renderValue(self, value):
        """Render the widget with the selected value.

        The original renderValue separates the items with either
        '&nbsp;' or '<br />' which isn't suitable for us.
        """
        rendered_items = self.renderItems(value)
        return renderElement(
            'table', cssClass=self.cssClass,
            contents='\n'.join(rendered_items))


class BugTaskSourcePackageNameWidget(SinglePopupWidget):
    """A widget for associating a bugtask with a SourcePackageName.

    It accepts both binary and source package names.
    """

    def getDistribution(self):
        """Get the distribution used for package validation.

        The package name has be to published in the returned distribution.
        """
        field = self.context
        distribution = field.context.distribution
        if distribution is None and field.context.distroseries is not None:
            distribution = field.context.distroseries.distribution
        assert distribution is not None, (
            "BugTaskSourcePackageNameWidget should be used only for"
            " bugtasks on distributions or on distribution series.")
        return distribution

    def _toFieldValue(self, input):
        if not input:
            return self.context.missing_value

        distribution = self.getDistribution()

        try:
            source, binary = distribution.guessPackageNames(input)
        except NotFoundError:
            try:
                return self.convertTokensToValues([input])[0]
            except InvalidValue:
                raise ConversionError(
                    "Launchpad doesn't know of any source package named"
                    " '%s' in %s." % (input, distribution.displayname))
        return source


class BugTaskAlsoAffectsSourcePackageNameWidget(
    BugTaskSourcePackageNameWidget):
    """Package widget for +distrotask.

    This widgets works the same as `BugTaskSourcePackageNameWidget`,
    except that it gets the distribution from the request.
    """

    def getDistribution(self):
        """See `BugTaskSourcePackageNameWidget`"""
        distribution_name = self.request.form.get('field.distribution')
        if distribution_name is None:
            raise UnexpectedFormData(
                "field.distribution wasn't in the request")
        distribution = getUtility(IDistributionSet).getByName(
            distribution_name)
        if distribution is None:
            raise UnexpectedFormData(
                "No such distribution: %s" % distribution_name)
        return distribution


class AssigneeDisplayWidget(BrowserWidget):
    """A widget for displaying an assignee."""

    implements(IDisplayWidget)

    def __init__(self, context, vocabulary, request):
        super(AssigneeDisplayWidget, self).__init__(context, request)

    def __call__(self):
        assignee_field = self.context
        bugtask = assignee_field.context
        if self._renderedValueSet():
            assignee = self._data
        else:
            assignee = assignee_field.get(bugtask)
        if assignee:
            person_img = renderElement(
                'img', style="padding-bottom: 2px", src="/@@/person", alt="")
            return renderElement(
                'a', href=canonical_url(assignee),
                contents="%s %s" % (person_img, escape(assignee.browsername)))
        else:
            if bugtask.target_uses_malone:
                return renderElement('i', contents='not assigned')
            else:
                return renderElement('i', contents='unknown')


class DBItemDisplayWidget(BrowserWidget):
    """A widget for displaying a bugtask dbitem."""

    implements(IDisplayWidget)

    def __init__(self, context, vocabulary, request):
        super(DBItemDisplayWidget, self).__init__(context, request)

    def __call__(self):
        dbitem_field = self.context
        bugtask = dbitem_field.context
        if self._renderedValueSet():
            dbitem = self._data
        else:
            dbitem = dbitem_field.get(bugtask)
        if dbitem:
            return renderElement(
                'span', contents=dbitem.title,
                cssClass="%s%s" % (dbitem_field.__name__, dbitem.name))
        else:
            return renderElement('span', contents='&mdash;')


class NewLineToSpacesWidget(StrippedTextWidget):
    """A widget that replaces new line characters with spaces."""

    def _toFieldValue(self, input):
        value = StrippedTextWidget._toFieldValue(self, input)
        if value is not self.context.missing_value:
            lines = value.splitlines()
            value = ' '.join(lines)
        return value


class NominationReviewActionWidget(LaunchpadRadioWidget):
    """Widget for choosing a nomination review action.

    It renders a radio box with no label for each option.
    """
    orientation = "horizontal"

    # The label will always be the empty string.
    _joinButtonToMessageTemplate = '%s%s'

    def textForValue(self, term):
        return u''
