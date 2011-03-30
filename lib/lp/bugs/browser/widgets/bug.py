# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    "BugTagsFrozenSetWidget",
    "BugTagsWidget",
    "BugWidget",
    "LargeBugTagsWidget",
    ]

import re

from zope.app.form.browser.textwidgets import (
    IntWidget,
    TextAreaWidget,
    TextWidget,
    )
from zope.app.form.interfaces import (
    ConversionError,
    WidgetInputError,
    )
from zope.component import getUtility
from zope.schema.interfaces import ConstraintNotSatisfied

from lp.app.errors import NotFoundError
from lp.app.validators import LaunchpadValidationError
from lp.bugs.interfaces.bug import IBugSet


class BugWidget(IntWidget):
    """A widget for displaying a field that is bound to an IBug."""

    def _toFormValue(self, value):
        """See zope.app.form.widget.SimpleInputWidget."""
        if value == self.context.missing_value:
            return self._missing
        else:
            return value.id

    def _toFieldValue(self, input):
        """See zope.app.form.widget.SimpleInputWidget."""
        if input == self._missing:
            return self.context.missing_value
        else:
            input = input.strip()
            # Bug ids are often prefixed with '#', but getByNameOrID
            # doesn't accept such ids.
            if input.startswith('#'):
                input = input[1:]
            try:
                return getUtility(IBugSet).getByNameOrID(input)
            except (NotFoundError, ValueError):
                raise ConversionError("Not a valid bug number or nickname.")


class BugTagsWidgetBase:
    """Base class for bug tags widgets."""

    def _tagsFromFieldValue(self, tags):
        """Package up the tags for display.

        Override this to provide custom ordering for example.

        :return: `None` if there are no tags, else an iterable of tags.
        """
        if tags is None or len(tags) == 0:
            return None
        else:
            return tags

    def _tagsToFieldValue(self, tags):
        """Package up the tags for the field.

        :param tags: `None` if the submitted data was missing, otherwise an
            iterable of tags.
        """
        if tags is None:
            return []
        else:
            return sorted(set(tags))

    def _toFormValue(self, value):
        """Convert a list of strings to a single, space separated, string."""
        tags = self._tagsFromFieldValue(value)
        if tags is None:
            return self._missing
        else:
            return u" ".join(tags)

    def _toFieldValue(self, input):
        """Convert a space separated string to a list of strings."""
        input = input.strip()
        if input == self._missing:
            return self._tagsToFieldValue(None)
        else:
            return self._tagsToFieldValue(
                tag.lower() for tag in re.split(r'[,\s]+', input)
                if len(tag) != 0)

    def getInputValue(self):
        try:
            return self._getInputValue()
        except WidgetInputError, input_error:
            # The standard error message isn't useful at all. We look to
            # see if it's a ConstraintNotSatisfied error and change it
            # to a better one. For simplicity, we care only about the
            # first error.
            validation_errors = input_error.errors
            for validation_error in validation_errors.args[0]:
                if isinstance(validation_error, ConstraintNotSatisfied):
                    self._error = WidgetInputError(
                        input_error.field_name, input_error.widget_title,
                        LaunchpadValidationError(
                            "'%s' isn't a valid tag name. Tags must start "
                            "with a letter or number and be lowercase. The "
                            'characters "+", "-" and "." are also allowed '
                            "after the first character."
                            % validation_error.args[0]))
                raise self._error
            else:
                raise

    def _getInputValue(self):
        raise NotImplementedError('_getInputValue must be overloaded')


class BugTagsWidget(BugTagsWidgetBase, TextWidget):
    """A widget for editing bug tags in a `List` field."""

    def __init__(self, field, value_type, request):
        # We don't use value_type.
        TextWidget.__init__(self, field, request)

    def _getInputValue(self):
        return TextWidget.getInputValue(self)


class BugTagsFrozenSetWidget(BugTagsWidget):
    """A widget for editing bug tags in a `FrozenSet` field."""

    def _tagsFromFieldValue(self, tags):
        """Order the tags for display.

        The field value is assumed to be unordered.
        """
        if tags is None or len(tags) == 0:
            return None
        else:
            return sorted(tags)

    def _tagsToFieldValue(self, tags):
        """Return a `frozenset` of tags."""
        if tags is None:
            return frozenset()
        else:
            return frozenset(tags)


class LargeBugTagsWidget(BugTagsWidgetBase, TextAreaWidget):
    """A large widget for editing bug tags in a `List` field."""

    def __init__(self, field, value_type, request):
        # We don't use value_type.
        TextAreaWidget.__init__(self, field, request)

    def _getInputValue(self):
        return TextAreaWidget.getInputValue(self)
