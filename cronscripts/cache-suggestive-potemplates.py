#! /usr/bin/python2.5
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Refresh the SuggestivePOTemplate cache.

The SuggestivePOTemplate cache is a narrow, lightweight database table
containing only the ids of `POTemplate`s that can provide external
translation suggestions.
"""

import _pythonpath

__metaclass__ = type

from lp.translations.scripts.cachesuggestivepotemplates import (
    CacheSuggestivePOTemplates)

if __name__ == '__main__':
    script = CacheSuggestivePOTemplates(dbuser='suggestivepotemplates')
    script.lock_and_run()
