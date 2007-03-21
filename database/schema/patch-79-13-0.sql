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
    ON OpenIdAuthorization(person, trust_root, date_expires, client_id);

/* Constraints to ensure our table does not needlessly bloat */
CREATE UNIQUE INDEX openidauthorization__person__client_id__trust_root__unq
    ON OpenIdAuthorization(person, client_id, trust_root)
    WHERE client_id IS NOT NULL;
CREATE UNIQUE INDEX openidauthorization__person__trust_root__unq
    ON OpenIdAuthorization(person, trust_root)
    WHERE client_id IS NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 13, 0);
