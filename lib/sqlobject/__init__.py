# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Expose the Storm SQLObject compatibility layer."""

__metaclass__ = type

from storm.sqlobject import *

# Provide the same interface from these other locations.
import sys
sys.modules['sqlobject.joins'] = sys.modules['sqlobject']
sys.modules['sqlobject.sqlbuilder'] = sys.modules['sqlobject']
del sys

def sqlrepr(obj, dbname=None):
    assert dbname in [None, 'postgres']
    from storm.databases.postgres import compile
    return compile(obj)
