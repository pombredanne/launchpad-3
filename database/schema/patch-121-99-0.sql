SET client_min_messages=ERROR;

ALTER TABLE Branch
ADD COLUMN stacked_on_branch integer REFERENCES Branch (id);

CREATE INDEX branch__stacked_on_branch__idx ON Branch(stacked_on_branch)
WHERE stacked_on_branch IS NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
