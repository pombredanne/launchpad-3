SET client_min_messages=ERROR;

-- Update the schema to store information about the Relying Parties (RP)
-- used by Persons.

-- Create a table to record person-relying party relationships.
CREATE TABLE OpenIDRPSummary (
    id SERIAL PRIMARY KEY,
    person INTEGER NOT NULL
        REFERENCES Person(id),
    identifier text NOT NULL,
    trust_root text NOT NULL,
    date_created TIMESTAMP without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    date_last_used TIMESTAMP without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    total_logins INTEGER NOT NULL
        DEFAULT 1,
    CONSTRAINT openidrpsummary__person__trust_root__identifier__key
        UNIQUE (person, trust_root, identifier)
);

CREATE INDEX openidrpsummary__person__idx
    ON openidrpsummary(person);

CREATE INDEX openidrpsummary__trust_root__idx
    ON openidrpsummary(trust_root);

CREATE INDEX openidrpsummary__identifier__idx
    ON openidrpsummary(identifier);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 97, 0);
