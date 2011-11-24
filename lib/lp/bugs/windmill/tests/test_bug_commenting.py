# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for the bug tag entry UI."""

__metaclass__ = type
__all__ = []

from uuid import uuid1

from lp.bugs.windmill.testing import BugsWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.windmill import lpuser


class TestBugCommenting(WindmillTestCase):

    layer = BugsWindmillLayer
    suite_name = 'Bug commenting'

    def test_bug_commenting(self):
        """Test commenting on bugs."""
        client, start_url = self.getClientFor('/bugs/1', user=lpuser.NO_PRIV)
        client.waits.forElement(jquery=u"('input#field\\.actions\\.save')")

        # Generate a unique piece of text, so we can run the test multiple
        # times, without resetting the db.
        new_comment_text = str(uuid1())
        client.type(text=new_comment_text, id="field.comment")
        client.click(jquery=u"('input[id=\"field\\.actions\\.save\"]')[0]")
        client.waits.forElement(
            jquery=u'("div.bug-comment p:contains(\'%s\')")' %
                new_comment_text)
