# Copyright Canonical Limited
# Author: Daniel Silverstone <daniel.silverstone@canonical.com>

"""Utility functions for the buildd master."""

# For more information on how to use this module, see
# lib/canonical/launchpad/doc/buildd-dbnotes.txt

# XXX dsilvers 2005-07-01: Can we replace all uses of notes with
# foo.non_db_attribute = 'bar' and perhaps also with properties on the
# instances which DTRT?

__metaclass__ = type

__all__ = ['notes']

class DBNote2:
    """Dictionary-style class which autovivifys real dicts based on
    ids used to index it."""

    def __init__(self):
        self.notes = {}

    def __getitem__(self, id):
        self.notes.setdefault(id,{})
        return self.notes[id]



class DBNote:
    """Dictionary-style class which takes in SQLObject instances or class
    names and returns dicts or DBNote2 class instances as appropriate.

    This class is designed to allow arbitrary annotations of SQLObjects
    without worrying about the fact that across transactions they might change
    their instance locations and thusly not be the same for keying in a dict.
    """

    def __init__(self):
        self.notes = {}

    def __getitem__(self, idx):
        if isinstance(idx, type):
            # It's a type, so it's an SQLObject class, so we return the DBNote2
            return self.notes.setdefault(idx, DBNote2())
        # It's not a type, so it's an SQLObject instance, we delve into the
        # DBNote2 and return the dict
        return self.notes.setdefault(type(idx), DBNote2())[idx.id]

# Import this in order to share the annotations around.
notes = DBNote()
