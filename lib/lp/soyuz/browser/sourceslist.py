# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=F0401

"""Browser views for sources list entries."""

from zope.schema import Choice
from zope.app.form.utility import setUpWidget
from zope.app.form.interfaces import IInputWidget
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from z3c.ptcompat import ViewPageTemplateFile

from canonical.launchpad import _
from canonical.launchpad.webapp import LaunchpadView


class SourcesListEntries:
    """For rendering sources.list entries.

    Represents a set of distroseries in a distribution archive.
    """
    def __init__(self, distribution, archive_url, valid_series):
        self.distribution = distribution
        self.archive_url = archive_url
        self.valid_series = valid_series


class SourcesListEntriesView(LaunchpadView):
    """Renders sources.list entries with a Javascript menu."""

    __used_for__ = SourcesListEntries
    template = ViewPageTemplateFile('../templates/sources-list-entries.pt')

    def __init__(self, context, request, initially_without_selection=False,
        comment=None):
        self._initially_without_selection = initially_without_selection
        self.comment = comment
        super(SourcesListEntriesView, self).__init__(context, request)

    def initialize(self):
        self.terms = []
        for series in self.context.valid_series:
            distro_version = "%(distro_name)s %(distro_version)s" % {
                'distro_name': self.context.distribution.displayname,
                'distro_version': series.version
                }
            self.terms.append(SimpleTerm(series, series.name, distro_version))

        # If the call-site requested that the widget be displayed initially
        # without a selection, or we were not able to find a sensible
        # default series, then add an option to force the user to select
        # a distroseries.
        if self._initially_without_selection or self.default_series is None:
            self.terms.insert(0, SimpleTerm(
                None, 'YOUR_DISTRO_SERIES_HERE',"Choose your %s version" % (
                    self.context.distribution.displayname)))

        field = Choice(__name__='series', title=_("Distro Series"),
                       vocabulary=SimpleVocabulary(self.terms), required=True)
        setUpWidget(self, 'series',  field, IInputWidget)
        self.series_widget.extra = "onChange='updateSeries(this);'"

    @property
    def plain_series_widget(self):
        """Render a <select> control with no <div>s around it."""
        return self.series_widget.renderValue(self.default_series)

    @property
    def sources_in_more_than_one_series(self):
        """Whether this archive has sources in more than one distro series."""
        return len(self.terms) > 1

    @property
    def default_series(self):
        """Return the default series for this view."""
        # If we have not been provided with any valid distroseries, then
        # we return the currentseries of the distribution.
        if len(self.terms) == 0:
            return self.context.distribution.currentseries

        # If the caller has indicated that there should not be a default
        # distroseries selected then we return None.
        elif self._initially_without_selection:
            return None

        # Otherwise, if the request's user-agent includes the Ubuntu version
        # number, we check for a corresponding valid distroseries and, if one
        # is found, return it's name.
        user_agent = self.request.getHeader('HTTP_USER_AGENT')

        ubuntu_index = 0
        if user_agent is not None:
            ubuntu_index = user_agent.find('Ubuntu/')

        if ubuntu_index > 0:
            # Great, the browser is telling us the platform is Ubuntu.
            # Now grab the Ubuntu series/version number:
            version_index_start = ubuntu_index + 7
            version_index_end = user_agent.find(' ', version_index_start)
            version_number = user_agent[
                version_index_start:version_index_end]

            # Finally, check if this version is one of the available
            # distroseries for this archive:
            for term in self.terms:
                if (term.value is not None and
                    term.value.version == version_number):
                    return term.value

        # If we were not able to get the users distribution series, then
        # either they are running a different OS, or they are running a
        # very old version of Ubuntu, or they have explicitly tampered
        # with user-agent headers in their browser. In any case,
        # we won't try to guess a value, but instead force them to
        # select one.
        return None

    @property
    def default_series_name(self):
        """Return the name of the default series for this view."""
        series = self.default_series
        if series is not None:
            return series.name
        else:
            # Return the select value for the generic text noting to the
            # user that they should select a distroseries.
            return 'YOUR_DISTRO_SERIES_HERE'

