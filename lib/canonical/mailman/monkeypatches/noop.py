"""Fake the MTA interface required by Mailman when creating and deleting
lists.  There is no MTA interface required, so this just no-ops everything.
"""

from Mailman.MTA.Manual import makelock

def create(mlist, cgi=False, nolock=False, quite=False):
    pass

def remove(mlist, cgi=False):
    pass
