# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `PersonDeactivateJob`."""

__metaclass__ = type

from zope.component import getUtility
from zope.interface.verify import verifyObject

from lp.registry.interfaces.persontransferjob import (
    IPersonDeactivateJob,
    IPersonDeactivateJobSource,
    )
from lp.services.identity.interfaces.account import AccountStatus
from lp.testing import TestCaseWithFactory
from lp.testing.dbuser import dbuser
from lp.testing.layers import DatabaseFunctionalLayer


class TestPersonDeactivateJob(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def makeJob(self):
        return getUtility(IPersonDeactivateJobSource).create(
            person=self.factory.makePerson(), comment='Because I Can')

    def test_interface(self):
        verifyObject(IPersonDeactivateJob, self.makeJob())

    def test_deactivate(self):
        job = self.makeJob()
        with dbuser('person-merge-job'):
            job.run()
        self.assertEquals(
            AccountStatus.DEACTIVATED, job.person.account_status)
        self.assertEquals('Because I Can', job.person.account_status_comment)
