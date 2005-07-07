# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'SQLObjectAddView',
    ]

from zope.app.form.browser.add import AddView
from zope.app.form.interfaces import WidgetsError
from zope.schema.interfaces import ValidationError
from zope.event import notify
from zope.app.event.objectevent import ObjectModifiedEvent

from canonical.launchpad.event.sqlobjectevent import SQLObjectCreatedEvent

class SQLObjectAddView(AddView):
    """An AddView for SQLObjects."""

    def createAndAdd(self, data):
        """Add the desired object using the data in the data argument.

        The data argument is a dictionary with the data entered in the form.
        """

        # XXX: Brad Bollenbach, 2005-04-01: I'm doing the painful task of
        # copying and pasting this method directly from AddView, changing
        # only the event that is published. By doing this, I'm able to
        # publish an ISQLObjectCreatedEvent that has the user as one of
        # its attributes (which is really important for things like, e.g.
        # bug notification emails.)
        #
        # It would be much nicer if I could override the event publishing
        # by overriding just one little method on this class.

        args = []
        if self._arguments:
            for name in self._arguments:
                args.append(data[name])

        kw = {}
        if self._keyword_arguments:
            for name in self._keyword_arguments:
                if name in data:
                    kw[str(name)] = data[name]

        content = self.create(*args, **kw)
        adapted = self.schema(content)

        errors = []

        if self._set_before_add:
            for name in self._set_before_add:
                if name in data:
                    field = self.schema[name]
                    try:
                        field.set(adapted, data[name])
                    except ValidationError:
                        errors.append(sys.exc_info()[1])

        if errors:
            raise WidgetsError(*errors)

        notify(SQLObjectCreatedEvent(content))

        content = self.add(content)

        adapted = self.schema(content)

        if self._set_after_add:
            # XXX: Brad Bollenbach, 2005-04-01: What's with publishing
            # an ObjectModifiedEvent on an add? I don't understand this
            # code.
            for name in self._set_after_add:
                if name in data:
                    field = self.schema[name]
                    try:
                        field.set(adapted, data[name])
                    except ValidationError:
                        errors.append(sys.exc_info()[1])

            # We've modified the object, so we need to pubish an
            # object-modified event:
            notify(ObjectModifiedEvent(content))

        if errors:
            raise WidgetsError(*errors)

        return content
