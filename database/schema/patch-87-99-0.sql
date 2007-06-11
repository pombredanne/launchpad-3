SET client_min_messages=ERROR;

CREATE TABLE Entitlement (
    id SERIAL PRIMARY KEY,
    team int NOT NULL REFERENCES Person,
    date_created timestamp WITHOUT TIME ZONE NOT NULL
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    date_starts timestamp WITHOUT TIME ZONE NOT NULL,
    date_expires timestamp WITHOUT TIME ZONE NOT NULL,
    entitlement_type integer NOT NULL,
    quota integer NOT NULL,
    amount_used integer DEFAULT 0 NOT NULL
);

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 99, 0);
