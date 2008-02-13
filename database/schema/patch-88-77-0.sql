SET client_min_messages=ERROR;

CREATE TABLE OAuthConsumer (
    id SERIAL PRIMARY KEY,
    key text NOT NULL UNIQUE,
    -- In the first round the secret won't be used as we'll create consumers
    -- automatically.
    secret text, 
    date_created timestamp without time zone,
    disabled boolean DEFAULT FALSE  -- Misbehaving consumers will be disabled
);

-- The request token is created when the consumer (third part application)
-- starts the oauth workflow.  Once the user logs into Launchpad and
-- allows the given application to access LP on his behalf, we flag the
-- request token as authorized.
-- After this we (or the user) tells the application that the token has
-- been authorized.  When the application comes back to us to exchange the
-- request token for an access token, we create an OAuthAccessToken and then
-- delete this one so that it's never used again.  The request token is
-- deleted because it can't be used again and we don't need it around.
-- (this is specified in section 6.3.2 of the OAuth Core spec)
-- In order to delete the request token at the same time that we exchange it
-- for an access token we need to store the permission in the request token
-- even though it's only necessary in the acess token.
CREATE TABLE OAuthRequestToken (
    id SERIAL PRIMARY KEY,
    consumer integer NOT NULL REFERENCES OAuthConsumer,
    person integer REFERENCES Person,
    -- 'permission' is an enumeration which can be one of:
    --   * Not authorized
    --   * Read public data
    --   * Read/Write public data
    --   * Read public and private data
    --   * Read/Write public and private data
    permission integer,
    key text UNIQUE,
    date_created timestamp without time zone,
    secret text NOT NULL
);

CREATE TABLE OAuthAccessToken (
    id SERIAL PRIMARY KEY,
    consumer integer NOT NULL REFERENCES OAuthConsumer,
    person integer NOT NULL REFERENCES Person,
    permission integer NOT NULL,
    key text UNIQUE,
    date_created timestamp without time zone,
    expiration_date timestamp without time zone,
    secret text NOT NULL
);

CREATE TABLE OAuthNonce (
    nonce text UNIQUE,
    request_timestamp timestamp without time zone,
    consumer integer NOT NULL REFERENCES OAuthConsumer
);

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 77, 0);
