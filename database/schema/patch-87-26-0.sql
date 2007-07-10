SET client_min_messages=ERROR;

CREATE TABLE CodeImportMachine (
    id SERIAL PRIMARY KEY,
    date_created TIMESTAMP WITHOUT TIME ZONE
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    hostname text UNIQUE NOT NULL,
    online boolean NOT NULL
    );

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 26, 0);

