SET client_min_messages=ERROR;

CREATE TABLE OpenIdAuthorization (
    id SERIAL PRIMARY KEY,
    person int NOT NULL REFERENCES Person,
    client_id text,
    date_created timestamp WITHOUT TIME ZONE NOT NULL
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    date_expires timestamp WITHOUT TIME ZONE NOT NULL,
    trust_root text NOT NULL
);

/* Support for
    SELECT * FROM OpenIdAuthorization
    WHERE
        AND person = 1
        AND trust_root = 'http://example.com';
        AND expires >= CURRENT_TIMESTAMP IN TIME ZONE 'UTC'
        AND (client_id IS NULL OR client_id = 'ZZZZZ')
*/
CREATE INDEX
    openidauthorization__person__trust_root__date_expires__client_id__idx
    ON OpenIDAuthorization(person, trust_root, date_expires, client_id);

/* Constraints to ensure our table does not needlessly bloat */
CREATE UNIQUE INDEX openidauthorization__person__client_id__trust_root__unq
    ON OpenIDAuthorization(person, client_id, trust_root)
    WHERE client_id IS NOT NULL;
CREATE UNIQUE INDEX openidauthorization__person__trust_root__unq
    ON OpenIDAuthorization(person, trust_root)
    WHERE client_id IS NULL;

/* Tables used by the openid.store.sqlstore.PostgreSQLStore class */

/* Our nonces are stored in the user's session
CREATE TABLE OpenIDNonces (
    nonce CHAR(8) UNIQUE PRIMARY KEY,
    expires INTEGER
);
*/

CREATE TABLE OpenIDAssociations (
    server_url VARCHAR(2047),
    handle VARCHAR(255),
    secret BYTEA,
    issued INTEGER,
    lifetime INTEGER,
    assoc_type VARCHAR(64),
    PRIMARY KEY (server_url, handle),
    CONSTRAINT secret_length_constraint CHECK (LENGTH(secret) <= 128)
);

/* Not used either??

CREATE TABLE OpenIDSettings (
    setting VARCHAR(128) UNIQUE PRIMARY KEY,
    value BYTEA,
    CONSTRAINT value_length_constraint CHECK (LENGTH(value) <= 20)
);
*/

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 00, 1);
