"""editview.py -- editview's for the Launchpad application."""
from datetime import datetime
from transaction import get_transaction

from zope.app.i18n import ZopeMessageIDFactory as _
from zope.app.form.browser.editview import EditView
from zope.app.form.utility import setUpEditWidgets, applyWidgetsChanges
from zope.app.form.browser.submit import Update
from zope.app.form.interfaces import WidgetsError
from zope.event import notify

from canonical.launchpad.event.sqlobjectevent import SQLObjectModifiedEvent

class SQLObjectEditView(EditView):
    """An editview that publishes an SQLObjectModifiedEvent, that provides
    a copy of the SQLObject before and after the object was modified with
    an edit form, so that listeners can figure out *what* changed."""

    def update(self):
        if self.update_status is not None:
            # We've been called before. Just return the status we previously
            # computed.
            return self.update_status

        status = ''

        content = self.adapted

        if Update in self.request:
            changed = False
            try:
                # a little bit of hocus pocus to be able to take a
                # (good enough, for our purposes) snapshot of what
                # an SQLObject looked like at a certain point in time,
                # so that we can see what changed later
                class Snapshot(object):
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
                    notify(SQLObjectModifiedEvent(
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

