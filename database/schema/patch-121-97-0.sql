SET client_min_messages=ERROR;

-- Update the schema to store information about the Relying Parties (RP)
-- used by Persons.

-- Create a table to record person-relying party relationships.
CREATE TABLE OpenIDRPSummary (
    id SERIAL PRIMARY KEY,
    person INTEGER NOT NULL
        REFERENCES Person(id),
    trust_root text NOT NULL,
    identifier text NOT NULL,
    date_created TIMESTAMP without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    date_last_used TIMESTAMP without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    total_logins INTEGER NOT NULL
        DEFAULT 1,
    CONSTRAINT openidrpsummary__person__trust_root__identifier__key
        UNIQUE (person, trust_root, identifier)
);

CREATE UNIQUE INDEX openidrpsummary__person__idx
    ON openidrpsummary USING btree (person);

CREATE UNIQUE INDEX openidrpsummary__trust_root__idx
    ON openidrpsummary USING btree (trust_root);

CREATE UNIQUE INDEX openidrpsummary__identifier__idx
    ON openidrpsummary USING btree (identifier);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 97, 0);
