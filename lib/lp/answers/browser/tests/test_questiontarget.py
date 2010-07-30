# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test questiontarget views."""

__metaclass__ = type

import os

from canonical.testing import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory
from lp.testing.views import create_initialized_view


class TestSearchQuestionsView(TestCaseWithFactory):
    """Test the behaviour of SearchQuestionsView."""

    layer = DatabaseFunctionalLayer

    def test_template_product_official_answers_unknown(self):
        target = self.factory.makeProduct()
        view = create_initialized_view(target, '+questions')
        file_name = os.path.basename(view.template.filename)
        self.assertEqual('unknown-support.pt', file_name)

    def test_template_person(self):
        person = self.factory.makePerson()
        view = create_initialized_view(person, '+questions')
        file_name = os.path.basename(view.template.filename)
        self.assertEqual('question-listing.pt', file_name)
