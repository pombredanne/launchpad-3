# This file is based on src/zope/app/form/browser/editview.py from
# Zope X3, with modifications Copyright 2004-2005 Canonical Ltd, as
# noted below.

"""editview.py -- editview for the Launchpad application."""

__metaclass__ = type

from datetime import datetime
from transaction import get_transaction

from zope.app.i18n import ZopeMessageIDFactory as _
from zope.app.form.browser.editview import EditView
from zope.app.form.utility import setUpEditWidgets, applyWidgetsChanges, \
    getWidgetsData
from zope.app.form.browser.submit import Update
from zope.app.form.interfaces import WidgetsError
from zope.event import notify

from canonical.launchpad.event.sqlobjectevent import SQLObjectModifiedEvent, \
    SQLObjectToBeModifiedEvent

class SQLObjectEditView(EditView):
    """An editview that publishes an SQLObjectModifiedEvent, that provides
    a copy of the SQLObject before and after the object was modified with
    an edit form, so that listeners can figure out *what* changed."""

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

        status = ''

        content = self.adapted

        if Update in self.request:
            changed = False
            try:
                # This is a really important event for handling bug
                # privacy.  If we can see that a bug is about to be
                # set private, we need to ensure that all implicit
                # subscriptions are turned explicit before any more
                # processing is done, otherwise implicit subscribers
                # can never set a bug private. Once bug.private ==
                # True, any further access to the bug attributes are
                # prevented to all but explicit subscribers!
                #
                # -- Brad Bollenbach, 2005-03-22
                new_values = getWidgetsData(self, self.schema, self.fieldNames)
                notify(SQLObjectToBeModifiedEvent(content, new_values))

                # a little bit of hocus pocus to be able to take a
                # (good enough, for our purposes) snapshot of what
                # an SQLObject looked like at a certain point in time,
                # so that we can see what changed later
                class Snapshot:
                    pass
                content_before_modification = Snapshot()
                for name in self.schema.names():
                    setattr(
                        content_before_modification,
                        name, getattr(content, name))

                changed = applyWidgetsChanges(self, self.schema,
                    target=content, names=self.fieldNames)
                # We should not generate events when an adapter is used.
                # That's the adapter's job.
                if changed and self.context is self.adapted:
                    notify(
                        SQLObjectModifiedEvent(
                            content, content_before_modification,
                            self.fieldNames, self.request.principal))
            except WidgetsError, errors:
                self.errors = errors
                status = _("An error occured.")
                get_transaction().abort()
            else:
                setUpEditWidgets(self, self.schema, source=self.adapted,
                                 ignoreStickyValues=True, names=self.fieldNames)
                if changed:
                    self.changed()
                    formatter = self.request.locale.dates.getFormatter(
                        'dateTime', 'medium')
                    status = _("Updated on ${date_time}")
                    status.mapping = {'date_time': formatter.format(
                        datetime.utcnow())}

        self.update_status = status
        return status

