# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Various helper functions for testing.."""

__metaclass__ = type
__all__ = [
    'remove_all_sample_data_branches',
]

from canonical.database.sqlbase import cursor


def remove_all_sample_data_branches():
    c = cursor()
    c.execute('delete from bugbranch')
    c.execute('delete from specificationbranch')
    c.execute('update productseries set user_branch=NULL, import_branch=NULL')
    c.execute('delete from branchrevision')
    c.execute('delete from branchsubscription')
    c.execute('delete from codeimportjob')
    c.execute('delete from codeimport')
    c.execute('delete from branch')
