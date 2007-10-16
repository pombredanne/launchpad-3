# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

# This file is based on src/zope/app/form/browser/editview.py from
# Zope X3, with modifications Copyright 2004-2005 Canonical Ltd, as
# noted below.

"""editview.py -- editview for the Launchpad application."""

__metaclass__ = type

__all__ = [
    'SQLObjectEditView',
    ]

from datetime import datetime

import transaction
from zope.app.form.browser.editview import EditView
from zope.app.form.utility import (
        setUpEditWidgets, applyWidgetsChanges,  getWidgetsData
        )
from zope.app.form.browser.submit import Update
from zope.app.form.interfaces import WidgetsError
from zope.event import notify
from zope.interface import providedBy

from canonical.launchpad import _
from canonical.launchpad.event import SQLObjectModifiedEvent
from canonical.launchpad.webapp.generalform import NoRenderingOnRedirect
from canonical.launchpad.webapp.snapshot import Snapshot

class SQLObjectEditView(EditView, NoRenderingOnRedirect):
    """An editview that publishes an SQLObjectModifiedEvent, that provides
    a copy of the SQLObject before and after the object was modified with
    an edit form, so that listeners can figure out *what* changed."""

    top_of_page_errors = ()

    def validate(self, data):
        """Validate the form.

        Override this to do any validation that must take into account the
        value of multiple widgets.

        To indicate any problem, this method should raise WidgetError(errors),
        where errors is a list of LaunchpadValidationError objects.
        """
        pass

    def update(self):
        # This method's code is mostly copy-and-pasted from
        # EditView.update due to the fact that we want to change the
        # semantics of the event notification to make it easy to do
        # things like figure out what /changed/ on a bug. The bits
        # we've customized in this method collect the previous and new
        # values of a modified object, and notify
        # SQLObjectModifiedEvent subscribers with that data.
        if self.update_status is not None:
            # We've been called before. Just return the status we previously
            # computed.
            return self.update_status

        self.update_status = ''

        content = self.adapted

        if Update in self.request:
            was_changed = False
            new_values = None
            try:
                new_values = getWidgetsData(self, self.schema, self.fieldNames)
            except WidgetsError, errors:
                self.errors = errors
                transaction.abort()
                return self.update_status

            try:
                self.validate(new_values)
            except WidgetsError, errors:
                self.top_of_page_errors = errors
                transaction.abort()
                return self.update_status

            # a little bit of hocus pocus to be able to take a
            # (good enough, for our purposes) snapshot of what
            # an SQLObject looked like at a certain point in time,
            # so that we can see what changed later
            content_before_modification = Snapshot(
                content, providing=providedBy(content))

            try:
                was_changed = applyWidgetsChanges(
                    self, self.schema, target=content, names=self.fieldNames)
            except WidgetsError, errors:
                self.errors = errors
                transaction.abort()
                return self.update_status

            # We should not generate events when an adapter is used.
            # That's the adapter's job.
            if was_changed and self.context is self.adapted:
                notify(
                    SQLObjectModifiedEvent(
                        content, content_before_modification,
                        self.fieldNames))

            setUpEditWidgets(self, self.schema, source=self.adapted,
                             ignoreStickyValues=True, names=self.fieldNames)
            if was_changed:
                self.changed()
                formatter = self.request.locale.dates.getFormatter(
                    'dateTime', 'medium')
                self.update_status = _(
                        "Updated on ${date_time}", mapping={
                        'date_time': formatter.format(datetime.utcnow())
                        })

            return self.update_status

    def __call__(self):
        #XXX: SQLObjectEditView doesn't define __call__(), but somehow
        #     NoRenderingOnRedirect.__call__() won't be called unless we
        #     define this method and call it explicitly. It's probably
        #     due to some ZCML magic which should be removed.
        #     -- Bjorn Tillenius, 2006-02-22
        return NoRenderingOnRedirect.__call__(self)
