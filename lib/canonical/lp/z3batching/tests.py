##############################################################################
#
# Copyright (c) 2003 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bug Tracker Mail Subscription and Mailer Tests

$Id: tests.py,v 1.3 2004/04/29 15:43:47 fdrake dead $
"""
import unittest

from canonical.lp.z3batching import Batch
from canonical.lp.z3batching.interfaces import IBatch

class BatchTest(unittest.TestCase):

    def getData(self):
        return ['one', 'two', 'three', 'four', 'five', 'six',
                'seven', 'eight', 'nine', 'ten']

    def test_Interface(self):
        self.failUnless(IBatch.providedBy(Batch([], 0, 0)))

    def test_constructor(self):
        batch = Batch(self.getData(), 9, 3)
        self.assertRaises(IndexError, Batch, self.getData(), start=10, size=3)

    def test__len__(self):
        batch = Batch(self.getData(), 0, 3)
        self.assertEqual(len(batch), 3)
        batch = Batch(self.getData(), 9, 3)
        self.assertEqual(len(batch), 1)

    def test__getitem__(self):
        batch = Batch(self.getData(), 0, 3)
        self.assertEqual(batch[0], 'one')
        self.assertEqual(batch[1], 'two')
        self.assertEqual(batch[2], 'three')
        batch = Batch(self.getData(), 3, 3)
        self.assertEqual(batch[0], 'four')
        self.assertEqual(batch[1], 'five')
        self.assertEqual(batch[2], 'six')
        batch = Batch(self.getData(), 9, 3)
        self.assertRaises(IndexError, batch.__getitem__, 3)
        
    def test__iter__(self):
        batch = Batch(self.getData(), 0, 3)
        self.assertEqual(list(iter(batch)), ['one', 'two', 'three'])
        batch = Batch(self.getData(), 9, 3)
        self.assertEqual(list(iter(batch)), ['ten'])

    def test__contains__(self):
        batch = Batch(self.getData(), 0, 3)
        self.assert_(batch.__contains__('one'))
        self.assert_(batch.__contains__('two'))
        self.assert_(batch.__contains__('three'))
        self.assert_(not batch.__contains__('four'))
        batch = Batch(self.getData(), 6, 3)
        self.assert_(not batch.__contains__('one'))
        self.assert_(batch.__contains__('seven'))
        self.assert_(not batch.__contains__('ten'))

    def test_nextBatch(self):
        next = Batch(self.getData(), 0, 3).nextBatch()
        self.assertEqual(list(iter(next)), ['four', 'five', 'six'])
        nextnext = next.nextBatch()
        self.assertEqual(list(iter(nextnext)), ['seven', 'eight', 'nine'])
        next = Batch(self.getData(), 9, 3).nextBatch()
        self.assertEqual(next, None)

    def test_prevBatch(self):
        prev = Batch(self.getData(), 9, 3).prevBatch()
        self.assertEqual(list(iter(prev)), ['seven', 'eight', 'nine'])
        prevprev = prev.prevBatch()
        self.assertEqual(list(iter(prevprev)), ['four', 'five', 'six'])
        prev = Batch(self.getData(), 0, 3).prevBatch()
        self.assertEqual(prev, None)

    def test_batchRoundTrip(self):
        batch = Batch(self.getData(), 0, 3).nextBatch()
        self.assertEqual(list(iter(batch.nextBatch().prevBatch())),
                         list(iter(batch)))

    def test_first_last(self):
        batch = Batch(self.getData(), 0, 3)
        self.assertEqual(batch.first(), 'one')
        self.assertEqual(batch.last(), 'three')
        batch = Batch(self.getData(), 9, 3)
        self.assertEqual(batch.first(), 'ten')
        self.assertEqual(batch.last(), 'ten')
        
    def test_total(self):
        batch = Batch(self.getData(), 0, 3)
        self.assertEqual(batch.total(), 10)
        batch = Batch(self.getData(), 6, 3)
        self.assertEqual(batch.total(), 10)
    
    def test_startNumber(self):
        batch = Batch(self.getData(), 0, 3)
        self.assertEqual(batch.startNumber(), 1)
        batch = Batch(self.getData(), 9, 3)
        self.assertEqual(batch.startNumber(), 10)

    def test_endNumber(self):
        batch = Batch(self.getData(), 0, 3)
        self.assertEqual(batch.endNumber(), 3)
        batch = Batch(self.getData(), 9, 3)
        self.assertEqual(batch.endNumber(), 10)
        

def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(BatchTest),
        ))

if __name__ == '__main__':
    unittest.main()
