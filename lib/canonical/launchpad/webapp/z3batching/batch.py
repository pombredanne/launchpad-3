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
# Some parts Copyright 2005 Canonical Ltd.
#
##############################################################################

"""
Zope-derived Batching Support
"""

from zope.interface import implements
from interfaces import IBatch

from sqlos.interfaces import ISelectResults

from canonical.cachedproperty import cachedproperty

# The base batch size, which can be overridden by users of _Batch such
# as BatchNavigator. In Launchpad, we override it via a config option.
BATCH_SIZE = 50

class _Batch(object):
    implements(IBatch)

    def __init__(self, results, start=0, size=None, _listlength=None):
        if results is None:
            results = []
        self.list = results

        # We only check the length of the list once, because if the
        # list is a SelectResults from SQLObject, list.count() hits
        # the database each time.
        if _listlength is None:
            if ISelectResults.providedBy(results):
                listlength = results.count()
            else:
                listlength = len(results)
        else:
            listlength = _listlength
        self.listlength = listlength

        if size is None:
            size = BATCH_SIZE
        self.size = size

        if start >= listlength:
            self.trueSize = 0
        elif start+size >= listlength:
            self.trueSize = listlength-start
        else:
            self.trueSize = size

        if listlength == 0:
            start = -1

        self.start = start
        if self.trueSize == 0:
            self.end = start
        else:
            self.end = start+self.trueSize-1

    def __len__(self):
        if self.trueSize < 0:
            return 0
        else:
            return self.trueSize

    def __getitem__(self, key):
        if key >= self.trueSize:
            raise IndexError, 'batch index out of range'
        # When self.start is negative (IOW, when we are batching over an
        # empty list) we need to raise IndexError here; otherwise, the
        # attempt to slice below will, on objects which don't implement
        # __len__, raise a mysterious exception directly from python.
        if self.start < 0:
            raise IndexError, 'batch is empty'
        return self.list[self.start+key]

    @cachedproperty
    def sliced_list(self):
        # We use a cachedproperty here to avoid self.__iter__ giving us
        # new objects every time; in certain cases (such as SQLObject)
        # this can be expensive.
        return list(self.list[self.start:self.end+1])

    def __iter__(self):
        if self.start < 0:
            # as in __getitem__, we need to avoid slicing with negative
            # indices in this code
            return iter([])
        return iter(self.sliced_list)

    def first(self):
        return self[0]

    def last(self):
        return self[self.trueSize-1]

    def __contains__(self, item):
        return item in self.__iter__()

    def nextBatch(self):
        start = self.start + self.size
        if start >= self.listlength:
            return None
        return _Batch(self.list, start, self.size, _listlength=self.listlength)

    def prevBatch(self):
        # The only case in which we should /not/ offer a previous batch
        # is when we are already at position zero, which also happens
        # when the list is empty.
        if self.start == 0:
            return None
        if self.start > self.listlength:
            return self.lastBatch()
        else:
            start = self.start - self.size
        if start < 0:
            # This situation happens, for instance, when you have a
            # 20-item batch and you manually set your start to 15;
            # in this case, hopping back one batch would be starting at
            # -5, which doesn't really make sense.
            start = 0
        return _Batch(self.list, start, self.size, _listlength=self.listlength)

    def firstBatch(self):
        return _Batch(self.list, 0, size=self.size,
                      _listlength=self.listlength)

    def lastBatch(self):
        # Return the last possible batch for this dataset, at the
        # correct offset.
        last_index = self.listlength - 1
        last_batch_start = last_index - (last_index % self.size)
        if last_batch_start < 0:
            last_batch_start = 0
        return _Batch(self.list, last_batch_start, size=self.size,
                      _listlength=self.listlength)

    def total(self):
        return self.listlength

    def startNumber(self):
        return self.start+1

    def endNumber(self):
        return self.end+1

