# Copyright 2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from testtools.matchers import Equals

from lp.testing import (
    admin_logged_in,
    login_person,
    record_two_runs,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import HasQueryCount
from lp.testing.views import create_initialized_view


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
