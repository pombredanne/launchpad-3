# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).


__metaclass__ = type


from unittest import TestLoader

from canonical.config import config
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.testing import DatabaseFunctionalLayer
from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.code.mail.sourcepackagerecipebuild import (
    SourcePackageRecipeBuildMailer)
from lp.testing import TestCaseWithFactory


class TestSourcePackageRecipeBuildMailer(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_generateEmail(self):
        """GenerateEmail produces the right headers and body."""
        person = self.factory.makePerson(name='person')
        cake = self.factory.makeSourcePackageRecipe(
            name=u'recipe', owner=person)
        pantry = self.factory.makeArchive(name='ppa')
        secret = self.factory.makeDistroSeries(name=u'distroseries')
        build = self.factory.makeSourcePackageRecipeBuild(
            recipe=cake, distroseries=secret, archive=pantry,
            status=BuildStatus.FULLYBUILT)
        IStore(build).flush()
        mailer = SourcePackageRecipeBuildMailer.forStatus(build)
        email = build.requester.preferredemail.email
        ctrl = mailer.generateEmail(email, build.requester)
        self.assertEqual('Successfully built: recipe for distroseries',
            ctrl.subject)
        body, footer = ctrl.body.split('\n-- \n')
        self.assertEqual(
            'Build person/recipe into ppa for distroseries: Successfully'
            ' built.\n', body
            )
        self.assertEqual(
            'http://code.launchpad.dev/~person/+recipe/recipe/+build/1\n'
            'You are the requester of the build.\n', footer)
        self.assertEqual(
            config.canonical.noreply_from_address, ctrl.from_addr)
        self.assertEqual(
            'Requester', ctrl.headers['X-Launchpad-Message-Rationale'])
        self.assertEqual(
            'recipe-build-status',
            ctrl.headers['X-Launchpad-Notification-Type'])
        self.assertEqual(
            'FULLYBUILT', ctrl.headers['X-Launchpad-Build-State'])


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
