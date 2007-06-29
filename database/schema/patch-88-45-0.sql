SET client_min_messages=ERROR;

CREATE TABLE CodeImportMachine (
    id SERIAL PRIMARY KEY,
    date_created TIMESTAMP WITHOUT TIME ZONE
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    hostname text UNIQUE,
    online boolean
    );

-- XXX Put a proper patch number here.
-- 2007-06-29 Michael Hudson
INSERT INTO LaunchpadDatabaseRevision VALUES (88, 45, 0);

