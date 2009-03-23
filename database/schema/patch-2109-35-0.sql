SET client_min_messages=ERROR;

-- Copied from openid/store/sqlstore.py, just like the existing
-- OpenIDAssociations.  This is what the python openid package expects the
-- table to look like.
CREATE TABLE OpenIDNonce (
    server_url VARCHAR(2047) NOT NULL,
    timestamp INTEGER NOT NULL,
    salt CHAR(40) NOT NULL,
    PRIMARY KEY (server_url, timestamp, salt)
    );

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 35, 0);
