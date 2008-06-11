SET client_min_messages=ERROR;

-- Update the schema to store information about the Relying Parties (RP)
-- used by Persons.


-- Create a table to represent the basic RP.
-- It becomes the base for OpenIDRelyingParty, so the trust_root is
-- copied into the new table.
CREATE TABLE OpenIDRelyingParty (
    id SERIAL PRIMARY KEY,
    trust_root TEXT NOT NULL,
    date_created TIMESTAMP WITHOUT TIME ZONE
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL
);

INSERT INTO OpenIDRelyingParty (date_created, trust_root)
SELECT CURRENT_TIMESTAMP AT TIME ZONE 'UTC', trust_root
FROM OpenIDRPConfig;


-- Add a column to create a relationship between the basic table and
-- the config table. update the OpenIDRelyingParty id and set the
-- column to not null.
-- XXX sinzui 2008-06-11: We should drop the trust_root column, but I
-- chose to defer that until after the Launchpad has adopted the new
-- OpenID identifier.
ALTER TABLE OpenIDRPConfig
    ADD COLUMN relying_party INTEGER
        REFERENCES OpenIDRelyingParty(id);

UPDATE OpenIDRPConfig
SET relying_party = OpenIDRelyingParty.id
FROM OpenIDRelyingParty
WHERE OpenIDRPConfig.trust_root = OpenIDRelyingParty.trust_root;

-- XXX sinzui 2008-06-11: relying_party should never be null, but
-- updating the schema without a concurrent code change is fatal.
--ALTER TABLE OpenIDRPConfig
--    ALTER COLUMN relying_party SET NOT NULL;


-- Add a column to OpenIDAuthorization to link the current authorizations
-- to the base RP. This table is not used at this time so no other migration
-- is need to the DB.
ALTER TABLE OpenIDAuthorization
    ADD COLUMN relying_party INTEGER
        REFERENCES OpenIDRelyingParty(id);

-- XXX sinzui 2008-06-11: relying_party should never be null, but
-- updating the schema without a concurrent code change is fatal.
--ALTER TABLE OpenIDRPConfig
--    ALTER COLUMN relying_party SET NOT NULL;


-- Create a table to log person-relying party relationships.
-- XXX sinzui 2008-06-11: OpenIDAuthorization overlaps this table.
-- The date_last_used and login_count might be a method (query)
-- or a view.
CREATE TABLE OpenIDRPLog (
    id SERIAL PRIMARY KEY,
    relying_party INTEGER NOT NULL
        REFERENCES OpenIDRelyingParty(id),
    person INTEGER NOT NULL
        REFERENCES Person(id),
    date_created TIMESTAMP without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    date_last_used TIMESTAMP without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    login_count INTEGER NOT NULL
        DEFAULT 1
);

CREATE UNIQUE INDEX openidrplog__relying_party__person__unq
  ON openidrplog USING btree (relying_party, person);


INSERT INTO LaunchpadDatabaseRevision VALUES (121, 97, 0);
