SET client_min_messages=ERROR;

ALTER TABLE LaunchpadDatabaseRevision
    ADD start_time timestamp without time zone DEFAULT (
        transaction_timestamp() AT TIME ZONE 'UTC'),
    ADD end_time timestamp without time zone DEFAULT (
        statement_timestamp() AT TIME ZONE 'UTC');

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 01, 1);

