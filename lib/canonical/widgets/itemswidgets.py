# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Widgets dealing with a choice of options."""

__metaclass__ = type

__all__ = [
    'LaunchpadDropdownWidget',
    'LabeledMultiCheckBoxWidget',
    'LaunchpadRadioWidget',
    'LaunchpadRadioWidgetWithDescription',
    'CheckBoxMatrixWidget',
    ]

import math

from zope.schema.interfaces import IChoice
from zope.app.form.browser import MultiCheckBoxWidget
from zope.app.form.browser.itemswidgets import DropdownWidget, RadioWidget
from zope.app.form.browser.widget import renderElement

from canonical.lazr.enum import IEnumeratedType

class LaunchpadDropdownWidget(DropdownWidget):
    """A Choice widget that doesn't encloses itself in <div> tags."""

    def _div(self, cssClass, contents, **kw):
        return contents


class LabeledMultiCheckBoxWidget(MultiCheckBoxWidget):
    """MultiCheckBoxWidget which wraps option labels with proper
    <label> elements.
    """

    _joinButtonToMessageTemplate = (
        u'<label style="font-weight: normal">%s&nbsp;%s</label>')

    def __init__(self, field, vocabulary, request):
        # XXX flacoste 2006-07-23 Workaround Zope3 bug #545:
        # CustomWidgetFactory passes wrong arguments to a MultiCheckBoxWidget
        if IChoice.providedBy(vocabulary):
            vocabulary = vocabulary.vocabulary
        MultiCheckBoxWidget.__init__(self, field, vocabulary, request)


# XXX Brad Bollenbach 2006-08-10 bugs=56062: This is a hack to
# workaround Zope's RadioWidget not properly selecting the default value.
class LaunchpadRadioWidget(RadioWidget):
    """A widget to work around a bug in RadioWidget."""

    _joinButtonToMessageTemplate = (
        u'<label style="font-weight: normal">%s&nbsp;%s</label>')

    def _div(self, cssClass, contents, **kw):
        return contents

    def renderItems(self, value):
        """Render the items with the correct radio button selected."""
        # XXX Brad Bollenbach 2006-08-11: Workaround the fact that
        # value is a value taken directly from the form, when it should
        # instead have been already converted to a vocabulary term, to
        # ensure the code in the rest of this method will select the
        # appropriate radio button.
        if value == self._missing:
            value = self.context.missing_value

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

        return items


class LaunchpadRadioWidgetWithDescription(LaunchpadRadioWidget):
    """Display the enumerated type description after the label.

    If the value of the vocabulary terms have a description this
    is shown as text on a line under the label.
    """

    _labelWithDescriptionTemplate = (
        u'''<tr>
              <td rowspan="2">%s</td>
              <td><label for="%s">%s</label></td>
            </tr>
            <tr>
              <td>%s</td>
            </tr>
         ''')
    _labelWithoutDescriptionTemplate = (
        u'''<tr>
              <td>%s</td>
              <td><label for="%s">%s</label></td>
            </tr>
         ''')

    def __init__(self, field, vocabulary, request):
        """Initialize the widget."""
        assert IEnumeratedType.providedBy(vocabulary), (
            'The vocabulary must implement IEnumeratedType')
        super(LaunchpadRadioWidgetWithDescription, self).__init__(
            field, vocabulary, request)

    def _renderRow(self, text, form_value, id, elem):
        """Render the table row for the widget depending on description."""
        if form_value != self._missing:
            vocab_term = self.vocabulary.getTermByToken(form_value)
            description = vocab_term.value.description
        else:
            description = None

        if description is None:
            return self._labelWithoutDescriptionTemplate % (elem, id, text)
        else:
            return self._labelWithDescriptionTemplate % (
                elem, id, text, description)

    def renderItem(self, index, text, value, name, cssClass):
        """Render an item of the list."""
        id = '%s.%s' % (name, index)
        elem = renderElement(u'input',
                             value=value,
                             name=name,
                             id=id,
                             cssClass=cssClass,
                             type='radio')
        return self._renderRow(text, value, id, elem)

    def renderSelectedItem(self, index, text, value, name, cssClass):
        """Render a selected item of the list."""
        id = '%s.%s' % (name, index)
        elem = renderElement(u'input',
                             value=value,
                             name=name,
                             id=id,
                             cssClass=cssClass,
                             checked="checked",
                             type='radio')
        return self._renderRow(text, value, id, elem)

    def renderValue(self, value):
        # Render the items in a table to align the descriptions.
        rendered_items = self.renderItems(value)
        return (
            '<table class="radio-button-widget">%s</table>'
            % ''.join(rendered_items))


class CheckBoxMatrixWidget(LabeledMultiCheckBoxWidget):
    """A CheckBox widget which organizes the inputs in a grid.

    The column_count attribute can be set in the view to change
    the number of columns in the matrix.
    """

    column_count = 1

    def renderValue(self, value):
        """Render the checkboxes inside a <table>."""
        rendered_items = self.renderItems(value)
        html = ['<table>']
        if self.orientation == 'horizontal':
            for i in range(0, len(rendered_items), self.column_count):
                html.append('<tr>')
                for j in range(0, self.column_count):
                    index = i + j
                    if index >= len(rendered_items):
                        break
                    html.append('<td>%s</td>' % rendered_items[index])
                html.append('</tr>')
        else:
            row_count = int(math.ceil(
                len(rendered_items) / float(self.column_count)))
            for i in range(0, row_count):
                html.append('<tr>')
                for j in range(0, self.column_count):
                    index = i + (j * row_count)
                    if index >= len(rendered_items):
                        break
                    html.append('<td>%s</td>' % rendered_items[index])
                html.append('</tr>')

        html.append('</table>')
        return '\n'.join(html)

