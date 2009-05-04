SET client_min_messages=ERROR;

CREATE INDEX oauthnonce__request_timestamp__idx
    ON OAuthNonce(request_timestamp);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 44, 1);
