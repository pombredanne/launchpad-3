# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'FeaturedProjectsWidget'
    ]

from canonical.widgets.itemswidgets import LabeledMultiCheckBoxWidget

class FeaturedProjectsWidget(LabeledMultiCheckBoxWidget):
    """Widget that lists all featured projects with checkboxes for selection."""

