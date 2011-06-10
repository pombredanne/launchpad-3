# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from canonical.testing.layers import LaunchpadFunctionalLayer


class TestAnnotations(unittest.TestCase):
    layer = LaunchpadFunctionalLayer

    def test_case(self):
        from canonical.launchpad.webapp.zodb import handle_before_traversal
        db = self.zodb_db
        connection = db.open()
        root = connection.root()
        handle_before_traversal(root)
        from canonical.launchpad.interfaces.launchpad import IZODBAnnotation
        from lp.bugs.model.bug import Bug
        from lp.registry.model.product import Product
        bug = Bug.get(1)
        bug_annotations = IZODBAnnotation(bug)
        bug_annotations['soyuz.message'] = "a message on a bug"
        product = Product.get(2)
        product_annotations = IZODBAnnotation(product)
        product_annotations['soyuz.message'] = "a message on a product"

        self.assertEquals(bug_annotations['soyuz.message'],
                          'a message on a bug')

        # Whitebox: Check that zodb data structures are as expected.
        from canonical.launchpad.webapp.zodb import zodbconnection
        all_annotations = zodbconnection.annotations
        self.assertEquals(len(all_annotations), 2)
        self.assertEquals(all_annotations['Bug']['1']['soyuz.message'],
                          'a message on a bug')
        self.assertEquals(all_annotations['Product']['2']['soyuz.message'],
                          'a message on a product')


def test_suite():
    suite = unittest.TestSuite()
    # XXX daniels 2004-12-14:
    #     Commented out because although the test passes when it is run
    #     on its own, there is an odd interaction when it is run with other
    #     tests: the rdb transaction is closed too early.
    ##suite.addTest(unittest.makeSuite(TestAnnotations))
    return suite
