# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test approveSuggestion."""

__metaclass__ = type

from canonical.testing import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory


class ApproveSuggestionScenarioMixin:
    layer = DatabaseFunctionalLayer

    def test_approve_suggestion(self):
        # Approving a suggestion for an untranslated message makes it
        # translated, and sets the message's reviewer and review date.
        pofile = self.makePOFile()
        template = pofile.potemplate
        suggestion = self.makeSuggestion(pofile)
        reviewer = self.factory.makePerson()

        suggestion.approve(template, reviewer)

        traits = template.translation_side_traits
        self.assertTrue(traits.getFlag(suggestion))
        self.assertFalse(traits.other_side_traits.getFlag(suggestion))
        self.assertEqual(reviewer, suggestion.reviewer)

    def test_approve_translates_both_sides(self):
        # Approve a suggestion for a message that will be valid on both
        # sides.
        pass
    def test_approve_replaces_translation(self):
        # Approve a suggestion that replaces an existing translation.
        pass
    def test_approve_replaces_both_sides(self):
        pass
    def test_approve_replaces_and_translates(self):
        # Approving a suggestion to replace a translation on one side
        # can also provide a first translation on the other side.
        pass
    def test_approve_converges(self):
        pass
    def test_approve_replaces_diverged(self):
        pass
    def test_approve_one_side_ignores_other_side(self):
        pass
    def test_approve_replacing_diverged_ignores_shared(self):
        pass


class TestApproveSuggestionUpstream(ApproveSuggestionScenarioMixin,
                                    TestCaseWithFactory):
    pass
