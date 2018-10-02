# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A widget for selecting source snap channels for builds."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'SnapBuildChannelsWidget',
    ]

from z3c.ptcompat import ViewPageTemplateFile
from zope.formlib.interfaces import IInputWidget
from zope.formlib.utility import setUpWidget
from zope.formlib.widget import (
    BrowserWidget,
    InputErrors,
    InputWidget,
    )
from zope.interface import implementer
from zope.schema import TextLine
from zope.security.proxy import isinstance as zope_isinstance

from lp.app.errors import UnexpectedFormData
from lp.services.features import getFeatureFlag
from lp.services.webapp.interfaces import (
    IAlwaysSubmittedWidget,
    ISingleLineWidgetLayout,
    )
from lp.snappy.interfaces.snap import SNAP_SNAPCRAFT_CHANNEL_FEATURE_FLAG


@implementer(ISingleLineWidgetLayout, IAlwaysSubmittedWidget, IInputWidget)
class SnapBuildChannelsWidget(BrowserWidget, InputWidget):

    template = ViewPageTemplateFile("templates/snapbuildchannels.pt")
    hint = False
    snap_names = ["core", "snapcraft"]
    _widgets_set_up = False

    def __init__(self, context, request):
        super(SnapBuildChannelsWidget, self).__init__(context, request)
        self.hint = (
            'The channels to use for build tools when building the snap '
            'package.\n')
        default_snapcraft_channel = (
            getFeatureFlag(SNAP_SNAPCRAFT_CHANNEL_FEATURE_FLAG) or "apt")
        if default_snapcraft_channel == "apt":
            self.hint += (
                'If unset, or if the channel for snapcraft is set to "apt", '
                'the default is to install snapcraft from the source archive '
                'using apt.')
        else:
            self.hint += (
                'If unset, the default is to install snapcraft from the "%s" '
                'channel.  Setting the channel for snapcraft to "apt" causes '
                'snapcraft to be installed from the source archive using '
                'apt.' % default_snapcraft_channel)

    def setUpSubWidgets(self):
        if self._widgets_set_up:
            return
        fields = [
            TextLine(
                __name__=snap_name, title="%s channel" % snap_name,
                required=False)
            for snap_name in self.snap_names
            ]
        for field in fields:
            setUpWidget(
                self, field.__name__, field, IInputWidget, prefix=self.name)
        self._widgets_set_up = True

    def setRenderedValue(self, value):
        """See `IWidget`."""
        self.setUpSubWidgets()
        if not zope_isinstance(value, dict):
            value = {}
        self.core_widget.setRenderedValue(value.get("core"))
        self.snapcraft_widget.setRenderedValue(value.get("snapcraft"))

    def hasInput(self):
        """See `IInputWidget`."""
        return any(
            "%s.%s" % (self.name, snap_name) in self.request.form
            for snap_name in self.snap_names)

    def hasValidInput(self):
        """See `IInputWidget`."""
        try:
            self.getInputValue()
            return True
        except (InputErrors, UnexpectedFormData):
            return False

    def getInputValue(self):
        """See `IInputWidget`."""
        self.setUpSubWidgets()
        channels = {}
        for snap_name in self.snap_names:
            widget = getattr(self, snap_name + "_widget")
            channel = widget.getInputValue()
            if channel:
                channels[snap_name] = channel
        return channels

    def error(self):
        """See `IBrowserWidget`."""
        try:
            if self.hasInput():
                self.getInputValue()
        except InputErrors as error:
            self._error = error
        return super(SnapBuildChannelsWidget, self).error()

    def __call__(self):
        """See `IBrowserWidget`."""
        self.setUpSubWidgets()
        return self.template()
