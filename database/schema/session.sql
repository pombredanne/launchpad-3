-- Create tables used by the Z3 PostgreSQL session storage.
--
-- The PostgreSQL user that the session machinery connects as needs to be
-- granted the following permissions:
--   GRANT SELECT, INSERT, UPDATE, DELETE ON SessionData TO z3session;
--   GRANT SELECT, INSERT, UPDATE, DELETE oN SessionPkgData TO z3sessionuser;
--   GRANT SELECT ON Secret TO z3session;

SET client_min_messages=ERROR;

CREATE TABLE Secret (secret text);
COMMENT ON TABLE Secret IS 'The Zope3 session machinery uses a secret to cryptographically sign the tokens, stopping people creating arbitrary tokens and detecting corrupt or modified tokens. This secret is stored in this table where it can be accessed by all Z3 instances using the database';

INSERT INTO Secret VALUES ('thooper thpetial theqwet');

CREATE TABLE SessionData (
    client_id     text PRIMARY KEY,
    last_accessed timestamp with time zone
        NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
COMMENT ON TABLE SessionData IS 'Stores session tokens (the client_id) and the last accessed timestamp. The precision of the last access time is dependant on configuration in the Z3 application servers.';

CREATE INDEX sessiondata_last_accessed_idx ON SessionData(last_accessed);

CREATE TABLE SessionPkgData (
    client_id  text NOT NULL
        REFERENCES SessionData(client_id) ON DELETE CASCADE,
    product_id text NOT NULL,
    key        text NOT NULL,
    pickle     bytea NOT NULL,
    CONSTRAINT sessiondata_key UNIQUE (client_id, product_id, key)
    );
COMMENT ON TABLE SessionPkgData IS 'Stores the actual session data as a Python pickle.';

