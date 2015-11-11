# Copyright 2012-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for distroseries translations initialization."""

__metaclass__ = type

from itertools import chain

from testtools.matchers import ContainsAll
import transaction
from zope.component import getUtility

from lp.services.database.multitablecopy import MultiTableCopy
from lp.services.log.logger import DevNullLogger
from lp.testing import TestCaseWithFactory
from lp.testing.faketransaction import FakeTransaction
from lp.testing.layers import ZopelessDatabaseLayer
from lp.translations.interfaces.potemplate import IPOTemplateSet
from lp.translations.model.distroseries_translations_copy import (
    copy_active_translations,
    )


class EarlyExit(Exception):
    """Exception used to force early exit from the copying code."""
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class TestDistroSeriesTranslationsCopying(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_does_not_overwrite_existing_pofile(self):
        # Sometimes a POFile we're about to copy to a new distroseries
        # has already been created there due to message sharing.  In
        # that case, the copying code leaves the existing POFile in
        # place and does not copy it.  (Nor does it raise an error.)
        existing_series = self.factory.makeDistroSeries(name='existing')
        new_series = self.factory.makeDistroSeries(
            name='new', distribution=existing_series.distribution)
        template = self.factory.makePOTemplate(distroseries=existing_series)
        pofile = self.factory.makePOFile(potemplate=template)
        self.factory.makeCurrentTranslationMessage(
            language=pofile.language, potmsgset=self.factory.makePOTMsgSet(
                potemplate=template))

        # Sabotage the pouring code so that when it's about to hit the
        # POFile table, it returns to us and we can simulate a race
        # condition.
        pour_table = MultiTableCopy._pourTable

        def pour_or_stop_at_pofile(self, holding_table, table, *args,
                                   **kwargs):
            args = (self, holding_table, table) + args
            if table.lower() == "pofile":
                raise EarlyExit(*args, **kwargs)
            else:
                return pour_table(*args, **kwargs)

        MultiTableCopy._pourTable = pour_or_stop_at_pofile
        try:
            copy_active_translations(
                existing_series, new_series, FakeTransaction(),
                DevNullLogger())
        except EarlyExit as e:
            pour_args = e.args
            pour_kwargs = e.kwargs
        finally:
            MultiTableCopy._pourTable = pour_table

        # Simulate another POFile being created for new_series while the
        # copier was working.
        new_template = new_series.getTranslationTemplateByName(template.name)
        new_pofile = self.factory.makePOFile(
            potemplate=new_template, language=pofile.language)

        # Now continue pouring the POFile table.
        pour_table(*pour_args, **pour_kwargs)

        # The POFile we just created in our race condition stays in
        # place.  There is no error.
        resulting_pofile = new_template.getPOFileByLang(pofile.language.code)
        self.assertEqual(new_pofile, resulting_pofile)

    def test_restricting_by_sourcepackagenames(self):
        # Factory-generated names are long enough to cause
        # MultiTableCopy to explode with relation name conflicts due to
        # truncation. Keep them short.
        distro = self.factory.makeDistribution(name='notbuntu')
        dapper = self.factory.makeDistroSeries(
            distribution=distro, name='dapper')
        spns = [self.factory.makeSourcePackageName() for i in range(3)]
        for spn in spns:
            self.factory.makePOTemplate(
                distroseries=dapper, sourcepackagename=spn)

        def get_template_spns(series):
            return [
                pot.sourcepackagename for pot in
                getUtility(IPOTemplateSet).getSubset(distroseries=series)]

        self.assertContentEqual(spns, get_template_spns(dapper))

        # We can copy the templates for just a subset of the source
        # package names.
        edgy = self.factory.makeDistroSeries(
            distribution=distro, name='edgy')
        self.assertContentEqual([], get_template_spns(edgy))
        copy_active_translations(
            dapper, edgy, transaction, DevNullLogger(), sourcepackagenames=[])
        self.assertContentEqual([], get_template_spns(edgy))
        copy_active_translations(
            dapper, edgy, transaction, DevNullLogger(),
            sourcepackagenames=[spns[0], spns[2]])
        self.assertContentEqual([spns[0], spns[2]], get_template_spns(edgy))

        # We can also explicitly copy the whole lot.
        feisty = self.factory.makeDistroSeries(
            distribution=distro, name='feisty')
        self.assertContentEqual([], get_template_spns(feisty))
        copy_active_translations(
            dapper, feisty, transaction, DevNullLogger(),
            sourcepackagenames=spns)
        self.assertContentEqual(spns, get_template_spns(feisty))

    def test_skip_duplicates(self):
        # Normally the target distroseries must be empty.
        # skip_duplicates=True works around this, simply by skipping any
        # templates whose source package names match templates already in
        # the target.
        distro = self.factory.makeDistribution(name='notbuntu')
        source_series = self.factory.makeDistroSeries(
            distribution=distro, name='source')
        target_series = self.factory.makeDistroSeries(
            distribution=distro, name='target')
        spns = [self.factory.makeSourcePackageName() for i in range(3)]
        for spn in spns:
            template = self.factory.makePOTemplate(
                distroseries=source_series, sourcepackagename=spn)
            self.factory.makePOFile(potemplate=template)
        target_templates = []
        target_pofiles = []
        for spn in spns[:2]:
            template = self.factory.makePOTemplate(
                distroseries=target_series, sourcepackagename=spn)
            target_templates.append(template)
            target_pofiles.append(self.factory.makePOFile(potemplate=template))

        def get_template_spns(series):
            return [
                pot.sourcepackagename for pot in
                getUtility(IPOTemplateSet).getSubset(distroseries=series)]

        self.assertContentEqual(spns[:2], get_template_spns(target_series))
        self.assertRaises(
            AssertionError, copy_active_translations,
            source_series, target_series, transaction, DevNullLogger())
        copy_active_translations(
            source_series, target_series, transaction, DevNullLogger(),
            skip_duplicates=True)
        self.assertContentEqual(spns, get_template_spns(target_series))
        # The original POTemplates in the target distroseries are untouched,
        # along with their POFiles.
        self.assertThat(
            list(getUtility(IPOTemplateSet).getSubset(
                distroseries=target_series)),
            ContainsAll(target_templates))
        self.assertContentEqual(
            target_pofiles,
            chain.from_iterable(pot.pofiles for pot in target_templates))
