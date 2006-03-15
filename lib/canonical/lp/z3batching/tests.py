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
"""Batch tests.
"""
import unittest

from canonical.lp.z3batching import _Batch
from canonical.lp.z3batching.interfaces import IBatch

class BatchTest(unittest.TestCase):

    def getData(self):
        return ['one', 'two', 'three', 'four', 'five', 'six',
                'seven', 'eight', 'nine', 'ten']

    def test_Interface(self):
        self.failUnless(IBatch.providedBy(_Batch([], 0, 0)))

    def test_constructor(self):
        _Batch(self.getData(), 9, 3)
        # A start that's larger than the length should still construct a working
        # (but empty) batch.
        _Batch(self.getData(), start=99, size=3)

    def test__len__(self):
        batch = _Batch(self.getData(), 0, 3)
        self.assertEqual(len(batch), 3)
        batch = _Batch(self.getData(), 9, 3)
        self.assertEqual(len(batch), 1)
        batch = Batch(self.getData(), 99, 3)
        self.assertEqual(len(batch), 0)

    def test__getitem__(self):
        batch = _Batch(self.getData(), 0, 3)
        self.assertEqual(batch[0], 'one')
        self.assertEqual(batch[1], 'two')
        self.assertEqual(batch[2], 'three')
        batch = _Batch(self.getData(), 3, 3)
        self.assertEqual(batch[0], 'four')
        self.assertEqual(batch[1], 'five')
        self.assertEqual(batch[2], 'six')
        batch = _Batch(self.getData(), 9, 3)
        self.assertRaises(IndexError, batch.__getitem__, 3)
        
    def test__iter__(self):
        batch = _Batch(self.getData(), 0, 3)
        self.assertEqual(list(iter(batch)), ['one', 'two', 'three'])
        batch = _Batch(self.getData(), 9, 3)
        self.assertEqual(list(iter(batch)), ['ten'])
        batch = Batch(self.getData(), 99, 3)
        self.assertEqual(list(iter(batch)), [])

    def test__contains__(self):
        batch = _Batch(self.getData(), 0, 3)
        self.assert_(batch.__contains__('one'))
        self.assert_(batch.__contains__('two'))
        self.assert_(batch.__contains__('three'))
        self.assert_(not batch.__contains__('four'))
        batch = _Batch(self.getData(), 6, 3)
        self.assert_(not batch.__contains__('one'))
        self.assert_(batch.__contains__('seven'))
        self.assert_(not batch.__contains__('ten'))

    def test_nextBatch(self):
        next = _Batch(self.getData(), 0, 3).nextBatch()
        self.assertEqual(list(iter(next)), ['four', 'five', 'six'])
        nextnext = next.nextBatch()
        self.assertEqual(list(iter(nextnext)), ['seven', 'eight', 'nine'])
        next = _Batch(self.getData(), 9, 3).nextBatch()
        self.assertEqual(next, None)
        next = Batch(self.getData(), 99, 3).nextBatch()
        self.assertEqual(next, None)

    def test_prevBatch(self):
        prev = _Batch(self.getData(), 9, 3).prevBatch()
        self.assertEqual(list(iter(prev)), ['seven', 'eight', 'nine'])
        prevprev = prev.prevBatch()
        self.assertEqual(list(iter(prevprev)), ['four', 'five', 'six'])
        prev = _Batch(self.getData(), 0, 3).prevBatch()
        self.assertEqual(prev, None)
        last = Batch(self.getData(), 99, 3).prevBatch()
        self.assertEqual(list(iter(last)), ['ten'])

    def test_batchRoundTrip(self):
        batch = _Batch(self.getData(), 0, 3).nextBatch()
        self.assertEqual(list(iter(batch.nextBatch().prevBatch())),
                         list(iter(batch)))

    def test_first_last(self):
        batch = _Batch(self.getData(), 0, 3)
        self.assertEqual(batch.first(), 'one')
        self.assertEqual(batch.last(), 'three')
        batch = _Batch(self.getData(), 9, 3)
        self.assertEqual(batch.first(), 'ten')
        self.assertEqual(batch.last(), 'ten')
        
    def test_total(self):
        batch = _Batch(self.getData(), 0, 3)
        self.assertEqual(batch.total(), 10)
        batch = _Batch(self.getData(), 6, 3)
        self.assertEqual(batch.total(), 10)
        batch = Batch(self.getData(), 99, 3)
        self.assertEqual(batch.total(), 10)
    
    def test_startNumber(self):
        batch = _Batch(self.getData(), 0, 3)
        self.assertEqual(batch.startNumber(), 1)
        batch = _Batch(self.getData(), 9, 3)
        self.assertEqual(batch.startNumber(), 10)
        batch = Batch(self.getData(), 99, 3)
        self.assertEqual(batch.startNumber(), 100)

    def test_endNumber(self):
        batch = _Batch(self.getData(), 0, 3)
        self.assertEqual(batch.endNumber(), 3)
        batch = _Batch(self.getData(), 9, 3)
        self.assertEqual(batch.endNumber(), 10)
        batch = Batch(self.getData(), 99, 3)
        self.assertEqual(batch.endNumber(), 100)
        

def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(BatchTest),
        ))

if __name__ == '__main__':
    unittest.main()
