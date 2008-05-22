SET client_min_messages=ERROR;

ALTER TABLE Branch
ADD COLUMN stacked_on_branch integer REFERENCES Branch (id);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
