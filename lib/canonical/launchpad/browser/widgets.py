# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Customized widgets used in Launchpad."""

__metaclass__ = type

__all__ = ['TitleWidget', 'SummaryWidget', 'DescriptionWidget']

from zope.interface import implements

from zope.schema.interfaces import IText
from zope.app.form.browser import TextAreaWidget, TextWidget

class TitleWidget(TextWidget):
    """A launchpad title widget; a little wider than a normal Textline."""
    implements(IText)
    displayWidth = 60


class SummaryWidget(TextAreaWidget):
    """A widget to capture a summary."""
    implements(IText)
    width = 60
    height = 5


class DescriptionWidget(TextAreaWidget):
    """A widget to capture a description."""
    implements(IText)
    width = 60
    height = 10
