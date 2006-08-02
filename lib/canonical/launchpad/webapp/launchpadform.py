# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Launchpad Form View Classes
"""

__docformat__ = 'restructuredtext'

__all__ = [
    'LaunchpadFormView',
    ]

import transaction
from zope.app.form.interfaces import WidgetsError
from zope.formlib import form

from canonical.launchpad import _
from canonical.launchpad.webapp.publisher import LaunchpadView


class LaunchpadFormView(LaunchpadView):

    # the prefix used for all form inputs.
    prefix = 'field'

    # the form schema
    schema = None
    # subset of fields to use
    field_names = None
    # dictionary mapping field names to custom widgets
    custom_widgets = None

    # the next URL to redirect to on successful form submission
    next_url = None

    label = ''

    errors = ()
    top_of_page_errors = ()
    actions = ()

    def initialize(self):
        self.setUpFields()
        self.setUpWidgets()

        # validation performed before Zope 3 validation
        try:
            self.validateFromRequest()
        except WidgetsError, errors:
            self.errors = errors
            self._abort()
            return
            
        data = {}
        errors, action = form.handleSubmit(self.actions, data, self._validate)

        if errors:
            action.failure(data, errors)
            self._abort()
        elif errors is not None:
            action.success(data)
            if self.next_url:
                self.request.response.redirect(self.next_url)

    def _abort(self):
        """Abort the form edit.

        This will be called in the case of a validation error.
        """
        # XXX: 20060802 jamesh
        # This should really be dooming the transaction rather than
        # aborting.  What we really want is to prevent more work being
        # done and then committed.
        transaction.abort()

    def setUpFields(self):
        assert self.schema is not None, "Schema must be set for LaunchpadFormView"
        # XXX: 20060802 jamesh
        # expose omit_readonly=True ??
        self.form_fields = form.Fields(self.schema)
        if self.field_names is not None:
            self.form_fields = self.form_fields.select(*self.field_names)

        if self.custom_widgets is not None:
            for (field_name, widget_factory) in self.custom_widgets.items():
                self.form_fields[field_name].custom_widget = widget_factory

    def setUpWidgets(self):
        # XXX: 20060802 jamesh
        # do we want to do anything with ignore_request?
        self.widgets = form.setUpWidgets(
            self.form_fields, self.prefix, self.context, self.request,
            data=self.initial_values, ignore_request=False)

    @property
    def initial_values(self):
        """Override this in your subclass if you want any widgets to have
        initial values.
        """
        return {}

    def _validate(self, action, data):
        widget_errors = form.getWidgetsData(self.widgets, self.prefix, data)
        form_errors = form.checkInvariants(self.form_fields, data)
        try:
            self.validate(data)
        except WidgetsError, errors:
            form_errors += errors

        self.errors = widget_errors + form_errors
        self.top_of_page_errors = form_errors
        return self.errors

    @property
    def error_count(self):
        # this should use ngettext if we ever translate Launchpad's UI
        if len(self.errors) == 0:
            return ''
        elif len(self.errors) == 1:
            return 'There is 1 error'
        else:
            return 'There are %d errors' % len(self.errors)

    def validateFromRequest(self):
        """Validate the data, using self.request directly.

        Override this method if you want to do validation *before* Zope 3 widget
        validation is done.
        """

    def validate(self, data):
        """Validate the form.

        If errors are encountered, a WidgetsError exception is raised.

        Returns a dict of fieldname:value pairs if all form data
        submitted is valid.

        Override this method if you want to do validation *after* Zope 3 widget
        validation has already been done.
        """
        pass
