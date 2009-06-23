SET client_min_messages=ERROR;

CREATE INDEX revisionauthor__lower_email__idx ON RevisionAuthor(lower(email));
CREATE INDEX HWSubmission__lower_raw_emailaddress__idx
    ON HWSubmission(lower(raw_emailaddress));

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 55, 2);
