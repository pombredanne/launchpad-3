SET client_min_messages=ERROR;

-- Rename OpenIDAssociations to OpenIDAssociation
CREATE TABLE OpenIDAssociation (
    server_url VARCHAR(2047) NOT NULL,
    handle VARCHAR(255) NOT NULL,
    secret BYTEA,
    issued INTEGER,
    lifetime INTEGER,
    assoc_type VARCHAR(64),
    PRIMARY KEY (server_url, handle),
    CONSTRAINT secret_length_constraint CHECK (length(secret) <= 128)
);
INSERT INTO OpenIDAssociation
    (server_url, handle, secret, issued, lifetime, assoc_type)
SELECT server_url, handle, secret, issued, lifetime, assoc_type
FROM OpenIDAssociations
WHERE issued + lifetime > EXTRACT(
    EPOCH FROM CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - interval '1 day');
-- Can't drop tables now. Switch schema for upgrade.py to detect and handle.
ALTER TABLE OpenIDAssociations SET SCHEMA todrop;


-- Copied from openid/store/sqlstore.py, just like the existing
-- OpenIDAssociations.  This is what the python openid package expects the
-- table to look like.
CREATE TABLE OpenIDNonce (
    server_url VARCHAR(2047) NOT NULL,
    timestamp INTEGER NOT NULL,
    salt CHAR(40) NOT NULL,
    PRIMARY KEY (server_url, timestamp, salt)
);


-- The consumers, like shipit, shouldn't be sharing tables with the
-- server which is being split out.
CREATE TABLE OpenIDConsumerNonce (
    server_url VARCHAR(2047) NOT NULL,
    timestamp INTEGER NOT NULL,
    salt CHAR(40) NOT NULL,
    PRIMARY KEY (server_url, timestamp, salt)
);

CREATE TABLE OpenIDConsumerAssociation (
    server_url VARCHAR(2047) NOT NULL,
    handle VARCHAR(255) NOT NULL,
    secret BYTEA,
    issued INTEGER,
    lifetime INTEGER,
    assoc_type VARCHAR(64),
    PRIMARY KEY (server_url, handle),
    CONSTRAINT secret_length_constraint CHECK (length(secret) <= 128)
);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 35, 0);
