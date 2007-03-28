# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Browser views for items that can be displayed as images."""

__metaclass__ = type

__all__ = [
    'ImageAddView',
    'ImageChangeView',
    ]

from canonical.widgets.image import ImageChangeWidget
from canonical.launchpad.webapp import custom_widget, LaunchpadFormView

class ImageAddView(LaunchpadFormView):

    custom_widget('icon', ImageChangeWidget, ImageChangeWidget.ADD_STYLE)
    custom_widget('logo', ImageChangeWidget, ImageChangeWidget.ADD_STYLE)
    custom_widget('mugshot', ImageChangeWidget, ImageChangeWidget.ADD_STYLE)


class ImageChangeView(LaunchpadFormView):

    custom_widget('icon', ImageChangeWidget, ImageChangeWidget.EDIT_STYLE)
    custom_widget('logo', ImageChangeWidget, ImageChangeWidget.EDIT_STYLE)
    custom_widget('mugshot', ImageChangeWidget, ImageChangeWidget.EDIT_STYLE)


