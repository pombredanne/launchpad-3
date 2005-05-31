validators in here should be trivial bits of code, such as name.py.
This is because they need to be kept in sync with their corresponding
database constraints.

bug.py doesn't meet this - if this really is the best place for it, then I
need to find somewhere else to keep the database constraints duplcates in
sync.

-- StuartBishop 20050523

