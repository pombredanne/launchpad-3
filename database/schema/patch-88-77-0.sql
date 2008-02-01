SET client_min_messages=ERROR;

CREATE TABLE OAuthConsumer (
    id SERIAL PRIMARY KEY,
    -- XXX: Do we need to associate this with a person/projuct?
    -- Maybe we should have the columns but make them optional.
    -- Also, at the time any user authorizes a given request token, it
    -- should also be reasonable to associate that token's consumer with the
    -- user, if the consumer is not yet associated with any project or person.
    -- That shouldn't be a problem since it's very likely that the application
    -- author will be the first one to test it against launchpad.
    -- Or maybe we should require users to register the application they want to
    -- use to access Launchpad.  That sounds more reasonable.
    person integer NOT NULL REFERENCES Person,
    product integer REFERENCES Product,
    name text NOT NULL UNIQUE,
    key text NOT NULL UNIQUE,
    secret text,  -- In the first round this won't be used.
    date_created timestamp without time zone,
    displayname text NOT NULL -- Not sure we need a displayname
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
    permission integer, -- Enumeration (Read/Write, Public/Private)
    -- This is a tri-state column where NULL means the user hasn't yet
    -- granted or refused access to the given consumer.  Only request tokens
    -- with authorized==TRUE can be turned into access tokens when the consumer
    -- asks for them.
    authorized boolean,
    key text UNIQUE,
    date_created timestamp without time zone,
    secret text NOT NULL
);

CREATE TABLE OAuthAccessToken (
    id SERIAL PRIMARY KEY,
    consumer integer NOT NULL REFERENCES OAuthConsumer,
    person integer NOT NULL REFERENCES Person,
    permission integer NOT NULL, -- Enumeration (Read/Write, Public/Private)
    key text UNIQUE,
    date_created timestamp without time zone,
    expiration_date timestamp without time zone,
    secret text NOT NULL
);

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 77, 0);
