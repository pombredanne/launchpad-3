SET client_min_messages=ERROR;

ALTER TABLE OAuthRequestToken
    ADD COLUMN product INTEGER REFERENCES Product(id);
ALTER TABLE OAuthRequestToken
    ADD COLUMN project INTEGER REFERENCES Project(id);
ALTER TABLE OAuthRequestToken
    ADD COLUMN distribution INTEGER REFERENCES Distribution(id);
ALTER TABLE OAuthRequestToken
    ADD COLUMN sourcepackagename INTEGER REFERENCES SourcePackageName(id);
ALTER TABLE OAuthRequestToken ADD CONSTRAINT sourcepackagename_needs_distro
    CHECK (sourcepackagename IS NULL OR distribution IS NOT NULL);
-- XXX: Is it possible to rewrite this in a simpler way?
ALTER TABLE OAuthRequestToken ADD CONSTRAINT context_constraint CHECK (
    (product IS NULL AND distribution IS NULL AND project IS NULL)
     OR (product IS NOT NULL AND distribution IS NULL AND project IS NULL)
     OR (distribution IS NOT NULL AND product IS NULL AND project IS NULL)
     OR (project IS NOT NULL AND product IS NULL AND distribution IS NULL));

ALTER TABLE OAuthAccessToken
    ADD COLUMN product INTEGER REFERENCES Product(id);
ALTER TABLE OAuthAccessToken
    ADD COLUMN project INTEGER REFERENCES Project(id);
ALTER TABLE OAuthAccessToken
    ADD COLUMN distribution INTEGER REFERENCES Distribution(id);
ALTER TABLE OAuthAccessToken
    ADD COLUMN sourcepackagename INTEGER REFERENCES SourcePackageName(id);
ALTER TABLE OAuthAccessToken ADD CONSTRAINT sourcepackagename_needs_distro
    CHECK (sourcepackagename IS NULL OR distribution IS NOT NULL);
-- XXX: Is it possible to rewrite this in a simpler way?
ALTER TABLE OAuthAccessToken ADD CONSTRAINT context_constraint CHECK (
    (product IS NULL AND distribution IS NULL AND project IS NULL)
     OR (product IS NOT NULL AND distribution IS NULL AND project IS NULL)
     OR (distribution IS NOT NULL AND product IS NULL AND project IS NULL)
     OR (project IS NOT NULL AND product IS NULL AND distribution IS NULL));

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 77, 0);
