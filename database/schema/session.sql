/* This script sets up the session database */

CREATE TABLE Secret (secret text);
INSERT INTO Secret VALUES ('thooper thpetial theqwet');

CREATE TABLE SessionData (
    client_id     text PRIMARY KEY,
    last_accessed timestamp with time zone
        NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

CREATE TABLE SessionPkgData (
    client_id  text NOT NULL REFERENCES SessionData(client_id),
    product_id text NOT NULL,
    key        text NOT NULL,
    pickle     bytea NOT NULL,
    CONSTRAINT sessiondata_key UNIQUE (client_id, product_id, key)
    );

GRANT SELECT, INSERT, UPDATE, DELETE ON SessionData TO session;
GRANT SELECT, INSERT, UPDATE, DELETE oN SessionPkgData TO session;
GRANT SELECT ON Secret TO session;


