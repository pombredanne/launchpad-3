# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Browser views for sources list entries."""

from zope.schema import Choice
from zope.app.form.utility import setUpWidget
from zope.app.form.interfaces import IInputWidget
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

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

    def initialize(self):
        self.terms = [SimpleTerm(s, s.name, s.title)
                 for s in self.context.valid_series]
        field = Choice(__name__='series', title=_("Distro Series"),
                       vocabulary=SimpleVocabulary(self.terms), required=True)
        setUpWidget(self, 'series',  field, IInputWidget)
        self.series_widget.extra = "onChange='updateSeries(this);'"

    @property
    def plain_series_widget(self):
        """Render a <select> control with no <div>s around it."""
        return self.series_widget.renderValue(None)

    @property
    def sources_in_more_than_one_series(self):
        """Whether this archive has sources in more than one distro series."""
        return len(self.terms) > 1

    @property
    def default_series_name(self):
        """Return the name of the default series.

        If there are packages in this PPA, return the latest series in
        which packages are published. If not, return the name of the
        current series.
        """
        if len(self.terms) == 0:
            return self.context.distribution.currentseries.name
        return self.terms[0].value.name


