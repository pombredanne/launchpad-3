# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for links between branches and bugs or specs."""

__metaclass__ = type
__all__ = []

import unittest

import windmill

from canonical.launchpad.windmill.testing import lpuser
from canonical.launchpad.windmill.testing.constants import (
    FOR_ELEMENT,
    PAGE_LOAD,
    SLEEP,
    )

from lp.code.windmill.testing import CodeWindmillLayer
from lp.testing import WindmillTestCase


CREATE_QUESTION_BUTTON = (
    u'//input[@id="field.actions.continue" and @class="button"]')
ADD_TEXT_BUTTON = (
    u'//input[@id="field.actions.add" and @class="button"]')

ADD_COMMENT_BUTTON = (
    u'//input[@id="field.actions.comment" and @class="button"]')


class TestBranchBugLinks(WindmillTestCase):
    """Test the rendering of broken branch links."""

    layer = CodeWindmillLayer
    suite_name = "Broken branch links"

    question_text_template = u"""
    Here is the question. Which branches are valid?
    Valid: %s
    Invalid %s
    """

    def test_invalid_url_rendering(self):
        """Link a bug from the branch page."""
        client = self.client

        lpuser.FOO_BAR.ensure_login(client)

        start_url = (
            windmill.settings['TEST_URL'] + '/firefox/+addquestion')
        client.open(url=start_url)
        #client.waits.forPageLoad(timeout=PAGE_LOAD)
        client.waits.forElement(xpath=CREATE_QUESTION_BUTTON)
        client.type(text='The meaning of life', id=u'field.title')
        client.click(xpath=CREATE_QUESTION_BUTTON)

        client.waits.forElement(xpath=ADD_TEXT_BUTTON)
        valid_links = ['lp:~mark/firefox/release-0.8', 'lp:gnome-terminal/trunk']
        invalid_links = []#'lp:foo']
        question_text = self.question_text_template % (
            ', '.join(valid_links), ', '.join(invalid_links)
        )
        client.type(text=question_text, id=u'field.description')
        client.click(xpath=ADD_TEXT_BUTTON)

        client.waits.forElement(xpath=ADD_COMMENT_BUTTON)

        # Let the Ajax call run
        client.waits.sleep(milliseconds=SLEEP)

        code = """
            var good_a = windmill.testWin().document.getElementsByClassName('branch-short-link', 'a');
            var good_links = [];
            for( i=0; i<good_a.length; i++ ) {
                good_links.push(good_a[i].innerHTML);
            }

            var bad_a = windmill.testWin().document.getElementsByClassName('invalid-link', 'a');
            var bad_links = [];
            for( i=0; i<bad_a.length; i++ ) {
                bad_links.push(bad_a[i].innerHTML);
            }


            var result = {};
            result.good = good_links;
            result.bad = bad_links;
            result
        """
        raw_result = self.client.commands.execJS(js=code)
        self.assertEqual(True, 'result' in raw_result.keys(), raw_result)
        result = raw_result['result']
        result_valid_links = result['good']
        result_invalid_links = result['bad']
        self.assertEqual(len(invalid_links), len(result_invalid_links))
        self.assertEqual(set(invalid_links), set(result_invalid_links))
        self.assertEqual(len(valid_links), len(result_valid_links))
        self.assertEqual(set(valid_links), set(result_valid_links))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
