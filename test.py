#!/usr/bin/env python2.3
##############################################################################
#
# Copyright (c) 2004 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
# arch-tag: e7f23c0d-41de-4ddf-9bfa-72544de70f92
"""Test script

$Id: test.py 25177 2004-06-02 13:17:31Z jim $
"""
import sys, os

here = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(here, 'lib'))

import zope.app.tests.test

if __name__ == '__main__':
    zope.app.tests.test.process_args()
