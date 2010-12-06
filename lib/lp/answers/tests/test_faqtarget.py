# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for IFAQTarget"""

__metaclass__ = type

from zope.component import getUtility

from canonical.testing.layers import DatabaseFunctionalLayer
from canonical.launchpad.webapp.authorization import check_permission
from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.testing import (
    login_person,
    person_logged_in,
    TestCaseWithFactory,
    )


class BaseIFAQTargetTests:
    """Common tests for all IFAQTargets."""

    layer = DatabaseFunctionalLayer

    def addAnswerContact(self, answer_contact):
        language_set = getUtility(ILanguageSet)
        answer_contact.addLanguage(language_set['en'])
        self.target.addAnswerContact(answer_contact)

    def assertCanEdit(self, user, target):
        can_edit = check_permission('launchpad.Append', target)
        self.assertTrue(can_edit, 'User cannot edit FAQs for %s' % target)

    def assertCannotEdit(self, user, target):
        can_edit = check_permission('launchpad.Append', target)
        self.assertFalse(can_edit, 'User can edit FAQs for %s' % target)

    def test_owner_can_edit(self):
        login_person(self.owner)
        self.assertCanEdit(self.owner, self.target)

    def test_direct_answer_contact_can_edit(self):
        direct_answer_contact = self.factory.makePerson()
        login_person(direct_answer_contact)
        self.addAnswerContact(direct_answer_contact)
        self.assertCanEdit(direct_answer_contact, self.target)

    def test_indirect_answer_contact_can_edit(self):
        indirect_answer_contact = self.factory.makePerson()
        direct_answer_contact = self.factory.makeTeam()
        with person_logged_in(direct_answer_contact.teamowner):
            direct_answer_contact.addMember(
                indirect_answer_contact, direct_answer_contact.teamowner)
            self.addAnswerContact(direct_answer_contact)
        login_person(indirect_answer_contact)
        self.assertCanEdit(indirect_answer_contact, self.target)

    def test_nonparticipating_user_cannot_edit(self):
        nonparticipant = self.factory.makePerson()
        login_person(nonparticipant)
        self.assertCannotEdit(nonparticipant, self.target)


class TestDistributionPermissions(BaseIFAQTargetTests, TestCaseWithFactory):

    def setUp(self):
        super(TestDistributionPermissions, self).setUp()
        self.target = self.factory.makeDistribution()
        self.owner = self.target.owner


class TestProductPermissions(BaseIFAQTargetTests, TestCaseWithFactory):

    def setUp(self):
        super(TestProductPermissions, self).setUp()
        self.target = self.factory.makeProduct()
        self.owner = self.target.owner
