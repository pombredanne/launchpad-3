'''
EXPERIMENTAL - DO NOT USE YET.

Comments to Stuart Bishop or launchpad mailing list.

A common location for data validation code.

These validators will be the same code that is installed as constraints into
the database, so applications that make use of them can ensure they won't
propagate illegal values into the database, raising SQL exceptions which
will confuse the users.

As such, these methods should be concise and have all execution paths
tested. They should not rely on any libraries beyond the standard library.

Changes or additions to these methods should be cleared with the
acting DBA, or preferably made my the acting DBA.
'''

