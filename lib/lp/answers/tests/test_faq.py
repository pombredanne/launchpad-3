# Copyright 2010-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for IFAQ"""

__metaclass__ = type

import transaction
from zope.component import getUtility

from lp.answers.interfaces.faq import CannotDeleteFAQ
from lp.answers.model.faq import FAQ
from lp.registry.interfaces.person import IPersonSet
from lp.services.database.interfaces import IStore
from lp.services.webapp.authorization import check_permission
from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.testing import (
    admin_logged_in,
    login_person,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestFAQPermissions(TestCaseWithFactory):
    """Test who can edit FAQs."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestFAQPermissions, self).setUp()
        target = self.factory.makeProduct()
        self.owner = target.owner
        with person_logged_in(self.owner):
            self.faq = self.factory.makeFAQ(target=target)

    def addAnswerContact(self, answer_contact):
        """Add the test person to the faq target's answer contacts."""
        language_set = getUtility(ILanguageSet)
        answer_contact.addLanguage(language_set['en'])
        self.faq.target.addAnswerContact(answer_contact, answer_contact)

    def assertCanEdit(self, user, faq):
        """Assert that the user can edit an FAQ."""
        can_edit = check_permission('launchpad.Edit', faq)
        self.assertTrue(can_edit, 'User cannot edit %s' % faq)

    def assertCannotEdit(self, user, faq):
        """Assert that the user cannot edit an FAQ."""
        can_edit = check_permission('launchpad.Edit', faq)
        self.assertFalse(can_edit, 'User can edit edit %s' % faq)

    def test_owner_can_edit(self):
        # The owner of an FAQ target can edit its FAQs.
        login_person(self.owner)
        self.assertCanEdit(self.owner, self.faq)

    def test_direct_answer_contact_cannot_edit(self):
        # A direct answer contact for an FAQ target cannot edit its FAQs.
        direct_answer_contact = self.factory.makePerson()
        login_person(direct_answer_contact)
        self.addAnswerContact(direct_answer_contact)
        self.assertCannotEdit(direct_answer_contact, self.faq)

    def test_indirect_answer_contact_cannot_edit(self):
        # A indirect answer contact (a member of a team that is an answer
        # contact) for an FAQ target cannot edit its FAQs.
        indirect_answer_contact = self.factory.makePerson()
        direct_answer_contact = self.factory.makeTeam()
        with person_logged_in(direct_answer_contact.teamowner):
            direct_answer_contact.addMember(
                indirect_answer_contact, direct_answer_contact.teamowner)
            self.addAnswerContact(direct_answer_contact)
        login_person(indirect_answer_contact)
        self.assertCannotEdit(indirect_answer_contact, self.faq)

    def test_nonparticipating_user_cannot_edit(self):
        # A user that is not an owner of an FAQ target cannot edit its FAQs.
        nonparticipant = self.factory.makePerson()
        login_person(nonparticipant)
        self.assertCannotEdit(nonparticipant, self.faq)

    def test_registry_can_edit(self):
        # A member of ~registry can edit any FAQ.
        expert = self.factory.makePerson(
            member_of=[getUtility(IPersonSet).getByName('registry')])
        login_person(expert)
        self.assertCanEdit(expert, self.faq)

    def test_direct_answer_contact_cannot_delete(self):
        # Answer contacts are broad, and deletion is irreversible, so
        # they cannot do it themselves.
        direct_answer_contact = self.factory.makePerson()
        with person_logged_in(direct_answer_contact):
            self.addAnswerContact(direct_answer_contact)
            self.assertFalse(check_permission('launchpad.Delete', self.faq))

    def test_registry_can_delete(self):
        # A member of ~registry can delete any FAQ.
        expert = self.factory.makePerson(
            member_of=[getUtility(IPersonSet).getByName('registry')])
        with person_logged_in(expert):
            self.assertTrue(check_permission('launchpad.Delete', self.faq))


class TestFAQ(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_destroySelf(self):
        # An FAQ can be deleted.
        with admin_logged_in():
            faq = self.factory.makeFAQ()
            faq.destroySelf()
            transaction.commit()
            self.assertIs(None, IStore(FAQ).get(FAQ, faq.id))

    def test_destroySelf_rejected_if_questions_linked(self):
        # Questions must be unlinked before a FAQ is deleted.
        with admin_logged_in():
            faq = self.factory.makeFAQ()
            question = self.factory.makeQuestion()
            question.linkFAQ(self.factory.makePerson(), faq, "foo")
            self.assertRaises(CannotDeleteFAQ, faq.destroySelf)
            transaction.commit()
            self.assertEqual(faq, IStore(FAQ).get(FAQ, faq.id))
