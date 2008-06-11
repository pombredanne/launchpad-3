SET client_min_messages=ERROR;

-- Update the schema to store information about the Relying Parties (RP)
-- used by Persons.

-- XXX sinzui 2008-06-11: I considered replacing the trust_root column
-- in OpenIDAuthorizations and OpenIDRPConfig with a FK to a new RP entity.
-- I chose to defer that until after the Launchpad has adopted the new
-- OpenID identifier. Normalising the data entails more work than I think
-- we want to undertake for Launchpad 2.0. I'm not certain an RP object
-- viable either.

-- Create a table to log person-relying party relationships.
-- This table overlaps OpenIDAuthorization, where it is unlikely to
-- contain a transient authorizations, this table will.
CREATE TABLE OpenIDRPSummary (
    id SERIAL PRIMARY KEY,
    person INTEGER NOT NULL
        REFERENCES Person(id),
    trust_root text NOT NULL,
    date_created TIMESTAMP without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    date_last_used TIMESTAMP without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    last_client_id text,
    total_logins INTEGER NOT NULL
        DEFAULT 1
);

CREATE UNIQUE INDEX openidrpsummary__relying_party__person__unq
  ON openidrpsummary USING btree (person, trust_root);


INSERT INTO LaunchpadDatabaseRevision VALUES (121, 97, 0);
