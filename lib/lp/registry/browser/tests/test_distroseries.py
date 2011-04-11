# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `lp.registry.browser.distroseries`."""

__metaclass__ = type

from lxml import html

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    feature_flags,
    person_logged_in,
    set_feature_flag,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view


class TestDistroSeriesAddView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_submit(self):
        # When creating a new DistroSeries via DistroSeriesAddView, the title
        # is set to the same as the displayname (title is, in any case,
        # deprecated), the description is left empty, and parent_series is
        # None (DistroSeriesInitializeView takes care of setting that).
        user = self.factory.makePerson()
        distribution = self.factory.makeDistribution(owner=user)
        form = {
            "field.name": u"polished",
            "field.version": u"12.04",
            "field.displayname": u"Polished Polecat",
            "field.summary": u"Even The Register likes it.",
            "field.actions.create": u"Add Series",
            }
        with person_logged_in(user):
            create_initialized_view(distribution, "+addseries", form=form)
        distroseries = distribution.getSeries(u"polished")
        self.assertEqual(u"polished", distroseries.name)
        self.assertEqual(u"12.04", distroseries.version)
        self.assertEqual(u"Polished Polecat", distroseries.displayname)
        self.assertEqual(u"Polished Polecat", distroseries.title)
        self.assertEqual(u"Even The Register likes it.", distroseries.summary)
        self.assertEqual(u"", distroseries.description)
        self.assertIs(None, distroseries.parent_series)
        self.assertEqual(user, distroseries.owner)


class TestDistroSeriesInitializeView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_init(self):
        # There exists a +initseries view for distroseries.
        distroseries = self.factory.makeDistroSeries()
        view = create_initialized_view(distroseries, "+initseries")
        self.assertTrue(view)

    def test_is_derived_series_feature_enabled(self):
        # The feature is disabled by default, but can be enabled by setting
        # the soyuz.derived-series-ui.enabled flag.
        distroseries = self.factory.makeDistroSeries()
        view = create_initialized_view(distroseries, "+initseries")
        with feature_flags():
            self.assertFalse(view.is_derived_series_feature_enabled)
        with feature_flags():
            set_feature_flag(u"soyuz.derived-series-ui.enabled", u"true")
            self.assertTrue(view.is_derived_series_feature_enabled)

    def test_form_hidden_when_derived_series_feature_disabled(self):
        # The form is hidden when the feature flag is not set.
        distroseries = self.factory.makeDistroSeries()
        view = create_initialized_view(distroseries, "+initseries")
        with feature_flags():
            root = html.fromstring(view())
            self.assertEqual(
                [], root.cssselect("#initseries-form-container"))
            # Instead an explanatory message is shown.
            [message] = root.cssselect("p.error.message")
            self.assertIn(
                u"The Derivative Distributions feature is under development",
                message.text)

    def test_form_shown_when_derived_series_feature_enabled(self):
        # The form is shown when the feature flag is set.
        distroseries = self.factory.makeDistroSeries()
        view = create_initialized_view(distroseries, "+initseries")
        with feature_flags():
            set_feature_flag(u"soyuz.derived-series-ui.enabled", u"true")
            root = html.fromstring(view())
            self.assertNotEqual(
                [], root.cssselect("#initseries-form-container"))
            # A different explanatory message is shown for clients that don't
            # process Javascript.
            [message] = root.cssselect("p.error.message")
            self.assertIn(
                u"Javascript is required to use this page",
                message.text)
            self.assertIn(
                u"javascript-disabled",
                message.get("class").split())
