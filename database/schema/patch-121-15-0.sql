SET client_min_messages=ERROR;

CREATE TABLE OAuthConsumer (
    id SERIAL PRIMARY KEY,
    date_created timestamp without time zone NOT NULL
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    -- Misbehaving consumers will be disabled by admins
    disabled boolean NOT NULL DEFAULT FALSE,
    key text NOT NULL UNIQUE,
    -- In the first round the secret won't be used as we'll create consumers
    -- automatically.
    secret text
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
    date_expires timestamp without time zone,
    date_created timestamp without time zone NOT NULL
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    date_reviewed timestamp without time zone,
    key text UNIQUE NOT NULL,
    secret text NOT NULL,
    CONSTRAINT reviewed_request CHECK (
        date_reviewed IS NULL = person IS NULL = permission IS NULL)
);

CREATE INDEX oauthrequesttoken__consumer__idx
    ON OAuthRequestToken(consumer);

CREATE INDEX oauthrequesttoken__person__idx
    ON OAuthRequestToken(person) WHERE person IS NOT NULL;

-- Needed to prune old tokens never used efficiently.
CREATE INDEX oauthrequesttoken__date_created__idx
    ON OAuthRequestToken(date_created);

CREATE TABLE OAuthAccessToken (
    id SERIAL PRIMARY KEY,
    consumer integer NOT NULL REFERENCES OAuthConsumer,
    person integer NOT NULL REFERENCES Person,
    permission integer NOT NULL,
    date_created timestamp without time zone NOT NULL
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    date_expires timestamp without time zone,
    key text UNIQUE NOT NULL,
    secret text NOT NULL
);

CREATE INDEX oauthaccesstoken__consumer__idx
    ON OAuthAccessToken(consumer);

CREATE INDEX oauthaccesstoken__person__idx
    ON OAuthAccessToken(person);

CREATE INDEX oauthaccesstoken__date_expires__idx
    ON OAuthAccessToken(date_expires) WHERE date_expires IS NOT NULL;

CREATE TABLE OAuthNonce (
    id serial PRIMARY KEY,
    request_timestamp timestamp without time zone
        NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    consumer integer NOT NULL REFERENCES OAuthConsumer,
    nonce text UNIQUE NOT NULL
);

CREATE INDEX oauthnonce__consumer__request_timestamp__idx
    ON OAuthNonce(consumer, request_timestamp);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 15, 0);
