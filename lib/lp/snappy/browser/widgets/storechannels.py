# Copyright 2017-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'StoreChannelsWidget',
    ]

from z3c.ptcompat import ViewPageTemplateFile
from zope.formlib.interfaces import (
    IInputWidget,
    WidgetInputError,
    )
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
    _separator = channel_components_delimiter
    _default_track = 'latest'
    _widgets_set_up = False

    def __init__(self, field, value_type, request):
        # We don't use value_type.
        super(StoreChannelsWidget, self).__init__(field, request)
        # disable help_text for the global widget
        self.hint = None

    def setUpSubWidgets(self):
        if self._widgets_set_up:
            return
        fields = [
            TextLine(
                __name__="track", title=u"Track", required=False,
                description=_(
                    "Track defines a series for your software. "
                    "If not specified, the default track ('latest') is "
                    "assumed.")),
            List(
                __name__="risks", title=u"Risk", required=False,
                value_type=Choice(vocabulary="SnapStoreChannel"),
                description=_("Risks denote the stability of your software.")),
            TextLine(
                __name__="branch", title=u"Branch", required=False,
                description=_(
                    "Branches provide users with an easy way to test bug "
                    "fixes.  They are temporary and created on demand.  If "
                    "not specified, no branch is used.")),
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

    def buildChannelName(self, track, risk, branch):
        """Return channel name composed from given track, risk, and branch."""
        channel = risk
        if track and track != self._default_track:
            channel = self._separator.join((track, channel))
        if branch:
            channel = self._separator.join((channel, branch))
        return channel

    def splitChannelName(self, channel):
        """Return extracted track, risk, and branch from given channel name."""
        try:
            track, risk, branch = split_channel_name(channel)
        except ValueError:
            raise AssertionError("Not a valid value: %r" % channel)
        return track, risk, branch

    def setRenderedValue(self, value):
        """See `IWidget`."""
        self.setUpSubWidgets()
        if value:
            # NOTE: atm target channels must belong to the same track and
            # branch
            tracks = set()
            branches = set()
            risks = []
            for channel in value:
                track, risk, branch = self.splitChannelName(channel)
                tracks.add(track)
                risks.append(risk)
                branches.add(branch)
            if len(tracks) != 1 or len(branches) != 1:
                raise AssertionError("Not a valid value: %r" % value)
            track = tracks.pop()
            self.track_widget.setRenderedValue(track)
            self.risks_widget.setRenderedValue(risks)
            branch = branches.pop()
            self.branch_widget.setRenderedValue(branch)
        else:
            self.track_widget.setRenderedValue(None)
            self.risks_widget.setRenderedValue(None)
            self.branch_widget.setRenderedValue(None)

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
        track = self.track_widget.getInputValue()
        risks = self.risks_widget.getInputValue()
        branch = self.branch_widget.getInputValue()
        if track and self._separator in track:
            error_msg = "Track name cannot include '%s'." % self._separator
            raise WidgetInputError(
                self.name, self.label, LaunchpadValidationError(error_msg))
        if branch and self._separator in branch:
            error_msg = "Branch name cannot include '%s'." % self._separator
            raise WidgetInputError(
                self.name, self.label, LaunchpadValidationError(error_msg))
        channels = [
            self.buildChannelName(track, risk, branch) for risk in risks]
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
