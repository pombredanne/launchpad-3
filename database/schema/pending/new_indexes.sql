SET client_min_messages=ERROR;

-- We often want to join on person, but only unmerged accounts.
CREATE INDEX person__id__key_unmerged ON Person(id) WHERE merged IS NULL;


