set client_min_messages=ERROR;

CREATE INDEX emailaddress_person_status_idx ON EmailAddress(person, status);

-- Used when we ORDER BY karma DESC, id DESC
CREATE INDEX person_karma_id_idx on Person(karma,id);

-- And this is now redundant
DROP INDEX person_karma_idx;

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 46, 0);

