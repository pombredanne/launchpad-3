# Copyright 2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'StoreChannelsWidget',
    ]

from z3c.ptcompat import ViewPageTemplateFile
from zope.formlib.interfaces import IInputWidget, WidgetInputError
from zope.formlib.utility import setUpWidget
from zope.formlib.widget import (
    BrowserWidget,
    CustomWidgetFactory,
    InputErrors,
    InputWidget,
    )
from zope.interface import implementer
from zope.schema import (
    Choice,
    List,
    TextLine,
    )

from lp.app.errors import UnexpectedFormData
from lp.app.validators import LaunchpadValidationError
from lp.app.widgets.itemswidgets import LabeledMultiCheckBoxWidget
from lp.services.webapp.interfaces import (
    IAlwaysSubmittedWidget,
    ISingleLineWidgetLayout,
    )


@implementer(ISingleLineWidgetLayout, IAlwaysSubmittedWidget, IInputWidget)
class StoreChannelsWidget(BrowserWidget, InputWidget):

    template = ViewPageTemplateFile("templates/storechannels.pt")
    display_label = False
    _separator = '/'
    _default_track = 'latest'
    _widgets_set_up = False

    def __init__(self, field, value_type, request):
        super(StoreChannelsWidget, self).__init__(field, request)

    def setUpSubWidgets(self):
        if self._widgets_set_up:
            return
        fields = [
            TextLine(__name__="track", title=u"Track", required=False),
            List(__name__="risks", title=u"Risks", required=False,
                 value_type=Choice(vocabulary="SnapStoreChannel")),
            ]

        self.risks_widget = CustomWidgetFactory(LabeledMultiCheckBoxWidget)
        for field in fields:
            setUpWidget(
                self, field.__name__, field, IInputWidget, prefix=self.name)
        self._widgets_set_up = True

    def buildChannelName(self, track, risk):
        """Return channel name composed from given track and risk."""
        channel = risk
        if track and track != self._default_track:
            channel = track + self._separator + risk
        return channel

    def splitChannelName(self, channel):
        """Return extracted track and risk from given channel name."""
        components = channel.split(self._separator)
        if len(components) == 2:
            track, risk = components
        elif len(components) == 1:
            track = None
            risk = components[0]
        else:
            raise AssertionError("Not a valid value: %r" % channel)
        return track, risk

    def setRenderedValue(self, value):
        """See `IWidget`."""
        self.setUpSubWidgets()
        if value:
            tracks = set()
            risks = []
            for channel in value:
                track, risk = self.splitChannelName(channel)
                tracks.add(track)
                risks.append(risk)
            if len(tracks) != 1:
                raise AssertionError("Not a valid value: %r" % value)
            track = tracks.pop()
            self.track_widget.setRenderedValue(track)
            self.risks_widget.setRenderedValue(risks)
        else:
            self.track_widget.setRenderedValue(None)
            self.risks_widget.setRenderedValue(None)

    def hasInput(self):
        """See `IInputWidget`."""
        return ("%s.risks" % self.name) in self.request.form

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
        risks = self.risks_widget.getInputValue()
        track = self.track_widget.getInputValue()
        if track and self._separator in track:
            error_msg = "Track name cannot include '%s'." % self._separator
            raise WidgetInputError(
                self.name, self.label, LaunchpadValidationError(error_msg))
        channels = [self.buildChannelName(track, risk) for risk in risks]
        return channels

    def error(self):
        """See `IBrowserWidget`."""
        try:
            if self.hasInput():
                self.getInputValue()
        except InputErrors as error:
            self._error = error
        return super(StoreChannelsWidget, self).error()

    def __call__(self):
        """See `IBrowserWidget`."""
        self.setUpSubWidgets()
        return self.template()
