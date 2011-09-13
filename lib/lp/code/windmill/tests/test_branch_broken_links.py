# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for links between branches and bugs or specs."""

__metaclass__ = type

import transaction
import windmill
from zope.security.proxy import removeSecurityProxy

from lp.code.windmill.testing import CodeWindmillLayer
from lp.testing import (
    login,
    WindmillTestCase,
    )
from lp.testing.windmill.constants import SLEEP


LOGIN_LINK = (
    u'//div[@id="add-comment-login-first"]')


class TestBranchLinks(WindmillTestCase):
    """Test the rendering of broken branch links."""

    layer = CodeWindmillLayer
    suite_name = "Broken branch links"

    BUG_TEXT_TEMPLATE = u"""
    Here is the bug. Which branches are valid?
    Valid: %s
    Invalid %s
    """

    BRANCH_URL_TEMPLATE = "lp:%s"

    def make_product_and_valid_links(self):
        branch = self.factory.makeProductBranch()
        valid_branch_url = self.BRANCH_URL_TEMPLATE % branch.unique_name
        product = self.factory.makeProduct()
        product_branch = self.factory.makeProductBranch(product=product)
        naked_product = removeSecurityProxy(product)
        naked_product.development_focus.branch = product_branch
        valid_product_url = self.BRANCH_URL_TEMPLATE % product.name

        return (naked_product, [
            valid_branch_url,
            valid_product_url,
        ])

    def make_invalid_links(self):
        product = self.factory.makeProduct()
        distro = self.factory.makeDistribution()
        person = self.factory.makePerson()
        branch = self.factory.makeBranch(private=True, owner=person)
        naked_branch = removeSecurityProxy(branch)
        return dict([
            (self.BRANCH_URL_TEMPLATE % 'foo', "No such product: 'foo'."),
            (self.BRANCH_URL_TEMPLATE % product.name,
                "%s has no linked branch." % product.name),
            (self.BRANCH_URL_TEMPLATE % ('%s/bar' % product.name),
                "No such product series: 'bar'."),
            (self.BRANCH_URL_TEMPLATE % ('%s' % naked_branch.unique_name),
                "No such branch: '%s'." % naked_branch.unique_name),
            (self.BRANCH_URL_TEMPLATE % distro.name,
                "%s cannot have linked branches." % distro.name),
            ])

    def test_invalid_url_rendering(self):
        naked_product, valid_links = self.make_product_and_valid_links()
        invalid_links = self.make_invalid_links()

        from lp.testing import ANONYMOUS
        login(ANONYMOUS)
        client = self.client
        bug_description = self.BUG_TEXT_TEMPLATE % (
            ', '.join(valid_links), ', '.join(invalid_links.keys()))
        bug = self.factory.makeBug(product=naked_product,
                                        title="The meaning of life is broken",
                                        description=bug_description)
        transaction.commit()

        bug_url = (
            windmill.settings['TEST_URL'] + '%s/+bug/%s'
            % (naked_product.name, bug.id))
        client.open(url=bug_url)
        client.waits.forElement(xpath=LOGIN_LINK)

        # Let the Ajax call run
        client.waits.sleep(milliseconds=SLEEP)

        code = """
            var good_a = windmill.testWin().document.getElementsByClassName(
                            'branch-short-link', 'a');
            var good_links = [];
            for( i=0; i<good_a.length; i++ ) {
                good_links.push(good_a[i].innerHTML);
            }

            var bad_a = windmill.testWin().document.getElementsByClassName(
                            'invalid-link', 'a');
            var bad_links = {};
            for( i=0; i<bad_a.length; i++ ) {
                bad_links[bad_a[i].innerHTML] = bad_a[i].title;
            }


            var result = {};
            result.good = good_links;
            result.bad = bad_links;
            result
        """
        raw_result = client.commands.execJS(js=code)
        result = raw_result['result']
        result_valid_links = result['good']
        result_invalid_links = result['bad']
        self.assertEqual(set(invalid_links.keys()),
                         set(result_invalid_links.keys()))
        for (href, title) in invalid_links.items():
            self.assertEqual(title, result_invalid_links[href])
        self.assertEqual(set(valid_links), set(result_valid_links))
