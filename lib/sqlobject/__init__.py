# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Expose the Storm SQLObject compatibility layer."""

__metaclass__ = type

from storm.sqlobject import *

# Provide the same interface from these other locations.
import sys
sys.modules['sqlobject.joins'] = sys.modules['sqlobject']
sys.modules['sqlobject.sqlbuilder'] = sys.modules['sqlobject']
del sys

# This one is wrong, but CurrencyCol is only used in the bounty
# tracker so it isn't important.
CurrencyCol = FloatCol

def sqlrepr(obj, dbname=None):
    assert dbname in [None, 'postgres']
    from storm.databases.postgres import compile
    return compile(obj)
