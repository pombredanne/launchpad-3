# Copyright Canonical Limited
# Author: Daniel Silverstone <daniel.silverstone@canonical.com>

# Buildd utilities

class DBNote2:
    def __init__(self):
        self.notes = {}

    def __getitem__(self, id):
        self.notes.setdefault(id,{})
        return self.notes[id]
    


class DBNote:
    def __init__(self):
        self.notes = {}

    def __getitem__(self, idx):
        if isinstance(idx, type):
            self.notes.setdefault(idx, DBNote2())
            return self.notes[idx]
        self.notes.setdefault(type(idx), DBNote2())
        return self.notes[type(idx)][idx.id]

notes = DBNote()


# DBNote[Builder][12]["Hello"] == DBNote[thisbuilder]["Hello"]

