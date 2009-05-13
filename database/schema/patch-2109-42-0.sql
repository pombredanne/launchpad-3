SET client_min_messages=ERROR;

ALTER TABLE OAuthNonce
    ADD CONSTRAINT oauthnonce__access_token__fk
        FOREIGN KEY (access_token) REFERENCES OAuthAccessToken;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 42, 0);

