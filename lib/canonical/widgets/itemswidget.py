# Copyright 2006 Canonical Ltd.  All rights reserved.
#

"""Widgets for sequence fields."""

__metaclass__ = type

__all__ = [ 'LabeledMultiCheckBoxWidget' ]

from zope.schema.interfaces import IChoice
from zope.app.form.browser import MultiCheckBoxWidget


class LabeledMultiCheckBoxWidget(MultiCheckBoxWidget):
    """MultiCheckBoxWidget which wraps option labels with proper
    <label> elements."""

    _joinButtonToMessageTemplate = (
        u'<label style="font-weight: normal">%s&nbsp;%s</label>')

    def __init__(self, field, vocabulary, request):
        # XXXX flacoste 2006/07/23 Workaround Zope3 bug #545:
        # CustomWidgetFactory passes wrong arguments to a MultiCheckBoxWidget
        if IChoice.providedBy(vocabulary):
            vocabulary = vocabulary.vocabulary
        MultiCheckBoxWidget.__init__(self, field, vocabulary, request)

