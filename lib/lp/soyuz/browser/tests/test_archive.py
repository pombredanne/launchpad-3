# Copyright 2014-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from testtools.matchers import Equals
from zope.component import getUtility

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.buildmaster.interfaces.processor import IProcessorSet
from lp.services.webapp import canonical_url
from lp.testing import (
    admin_logged_in,
    login_person,
    record_two_runs,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing.matchers import HasQueryCount
from lp.testing.pages import extract_text
from lp.testing.views import create_initialized_view


class TestArchiveEditView(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestArchiveEditView, self).setUp()
        # None of the Ubuntu series in sampledata have amd64.  Add it to
        # breezy so that it shows up in the list of available processors.
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        proc_amd64 = getUtility(IProcessorSet).getByName("amd64")
        self.factory.makeDistroArchSeries(
            distroseries=ubuntu.getSeries("breezy-autotest"),
            architecturetag="amd64", processor=proc_amd64)

    def test_display_processors(self):
        ppa = self.factory.makeArchive()
        owner = login_person(ppa.owner)
        browser = self.getUserBrowser(
            canonical_url(ppa) + "/+edit", user=owner)
        processors = browser.getControl(name="field.processors")
        self.assertContentEqual(
            ["Intel 386 (386)", "AMD 64bit (amd64)", "HPPA Processor (hppa)"],
            [extract_text(option) for option in processors.displayOptions])
        self.assertContentEqual(["386", "amd64", "hppa"], processors.options)

    def test_edit_processors(self):
        ppa = self.factory.makeArchive()
        owner = login_person(ppa.owner)
        self.assertContentEqual(
            ["386", "amd64", "hppa"],
            [processor.name for processor in ppa.processors])
        browser = self.getUserBrowser(
            canonical_url(ppa) + "/+edit", user=owner)
        processors = browser.getControl(name="field.processors")
        self.assertContentEqual(["386", "amd64", "hppa"], processors.value)
        processors.value = ["386", "amd64"]
        browser.getControl("Save").click()
        login_person(ppa.owner)
        self.assertContentEqual(
            ["386", "amd64"],
            [processor.name for processor in ppa.processors])

    def test_edit_with_invisible_processor(self):
        # It's possible for existing archives to have an enabled processor
        # that's no longer usable with any non-obsolete distroseries, which
        # will mean it's hidden from the UI, but the non-admin
        # Archive.setProcessors isn't allowed to disable it.  Editing the
        # processor list of such an archive leaves the invisible processor
        # intact.
        proc_386 = getUtility(IProcessorSet).getByName("386")
        proc_amd64 = getUtility(IProcessorSet).getByName("amd64")
        proc_armel = self.factory.makeProcessor(
            name='armel', restricted=True, build_by_default=False)
        ppa = self.factory.makeArchive()
        with admin_logged_in():
            ppa.processors = [proc_386, proc_amd64, proc_armel]
        owner = login_person(ppa.owner)
        browser = self.getUserBrowser(
            canonical_url(ppa) + "/+edit", user=owner)
        processors = browser.getControl(name="field.processors")
        self.assertContentEqual(["386", "amd64"], processors.value)
        processors.value = ["amd64"]
        browser.getControl("Save").click()
        login_person(ppa.owner)
        self.assertContentEqual(
            ["amd64", "armel"],
            [processor.name for processor in ppa.processors])


class TestArchiveCopyPackagesView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_query_count(self):
        person = self.factory.makePerson()
        source = self.factory.makeArchive()

        def create_targets():
            self.factory.makeArchive(
                owner=self.factory.makeTeam(members=[person]))
            archive = self.factory.makeArchive()
            with admin_logged_in():
                archive.newComponentUploader(person, 'main')
        nb_objects = 2
        login_person(person)
        recorder1, recorder2 = record_two_runs(
            lambda: create_initialized_view(
                source, '+copy-packages', user=person),
            create_targets, nb_objects)
        self.assertThat(recorder2, HasQueryCount(Equals(recorder1.count)))
