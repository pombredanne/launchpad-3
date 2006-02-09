SET client_min_messages=ERROR;

CREATE INDEX specification_owner_idx on Specification(owner);

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 15, 1);

