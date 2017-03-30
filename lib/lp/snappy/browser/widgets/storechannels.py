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

from lp import _
from lp.app.errors import UnexpectedFormData
from lp.app.validators import LaunchpadValidationError
from lp.app.widgets.itemswidgets import LabeledMultiCheckBoxWidget
from lp.services.webapp.interfaces import (
    IAlwaysSubmittedWidget,
    ISingleLineWidgetLayout,
    )
from lp.snappy.validators.channels import (
    channel_components_delimiter,
    split_channel_name,
    )


@implementer(ISingleLineWidgetLayout, IAlwaysSubmittedWidget, IInputWidget)
class StoreChannelsWidget(BrowserWidget, InputWidget):

    template = ViewPageTemplateFile("templates/storechannels.pt")
    display_label = False
    _separator = channel_components_delimiter
    _default_track = 'latest'
    _widgets_set_up = False

    def __init__(self, field, value_type, request):
        # We don't use value_type.
        super(StoreChannelsWidget, self).__init__(field, request)

    def setUpSubWidgets(self):
        if self._widgets_set_up:
            return
        fields = [
            TextLine(__name__="track", title=u"Track", required=False,
                     description=_(
                         "Track defines a series for your software. "
                         "If not specified, the default track ('latest') is "
                         "assumed.")
                     ),
            List(__name__="risks", title=u"Risk", required=False,
                 value_type=Choice(vocabulary="SnapStoreChannel"),
                 description=_(
                     "Risks denote the stability of your software.")),
            ]

        self.risks_widget = CustomWidgetFactory(LabeledMultiCheckBoxWidget)
        for field in fields:
            setUpWidget(
                self, field.__name__, field, IInputWidget, prefix=self.name)
        self.risks_widget.orientation = 'horizontal'
        self._widgets_set_up = True

    @property
    def has_risks_vocabulary(self):
        risks_widget = getattr(self, 'risks_widget', None)
        return risks_widget and bool(risks_widget.vocabulary)

    def buildChannelName(self, track, risk):
        """Return channel name composed from given track and risk."""
        channel = risk
        if track and track != self._default_track:
            channel = track + self._separator + risk
        return channel

    def splitChannelName(self, channel):
        """Return extracted track and risk from given channel name."""
        try:
            track, risk = split_channel_name(channel)
        except ValueError:
            raise AssertionError("Not a valid value: %r" % channel)
        return track, risk

    def setRenderedValue(self, value):
        """See `IWidget`."""
        self.setUpSubWidgets()
        if value:
            # NOTE: atm target channels must belong to the same track
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
