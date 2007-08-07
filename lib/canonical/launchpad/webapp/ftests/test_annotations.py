# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from canonical.launchpad.ftests.harness import LaunchpadFunctionalTestCase
import unittest

class TestAnnotations(LaunchpadFunctionalTestCase):

    def test_case(self):
        from canonical.launchpad.webapp.zodb import handle_before_traversal
        db = self.zodb_db
        connection = db.open()
        root = connection.root()
        handle_before_traversal(root)
        from canonical.launchpad.interfaces import IZODBAnnotation
        from canonical.launchpad.database import Bug
        from canonical.launchpad.database import Product
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

