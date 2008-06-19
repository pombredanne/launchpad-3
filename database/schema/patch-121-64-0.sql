SET client_min_messages=ERROR;

-- Update the schema to store information about the Relying Parties (RP)
-- used by Persons.

-- Create a table to record person-relying party relationships.
CREATE TABLE OpenIDRPSummary (
    id SERIAL PRIMARY KEY,
    account INTEGER NOT NULL
        REFERENCES Account(id),
    openid_identifier text NOT NULL,
    trust_root text NOT NULL,
    date_created TIMESTAMP without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    date_last_used TIMESTAMP without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    total_logins INTEGER NOT NULL
        DEFAULT 1,
    CONSTRAINT openidrpsummary__account__trust_root__openid_identifier__key
        UNIQUE (account, trust_root, openid_identifier)
);

-- Not needed, as the unique index created by the
-- openidrpsummary__person__trust_root__identifier__key can be used.
--CREATE INDEX openidrpsummary__person__idx
--    ON openidrpsummary(person);

CREATE INDEX openidrpsummary__trust_root__idx
    ON openidrpsummary(trust_root);

CREATE INDEX openidrpsummary__openid_identifier__idx
    ON openidrpsummary(openid_identifier);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 64, 0);
