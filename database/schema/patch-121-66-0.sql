SET client_min_messages=ERROR;

ALTER TABLE OAuthRequestToken
    ADD COLUMN product INTEGER REFERENCES Product(id),
    ADD COLUMN project INTEGER REFERENCES Project(id),
    ADD COLUMN distribution INTEGER REFERENCES Distribution(id),
    ADD COLUMN sourcepackagename INTEGER REFERENCES SourcePackageName(id);

CREATE INDEX oauthrequesttoken__product__idx
    ON OAuthRequestToken (product) WHERE product IS NOT NULL;

CREATE INDEX oauthrequesttoken__project__idx
    ON OAuthRequestToken (project) WHERE project IS NOT NULL;

CREATE INDEX oauthrequesttoken__distribution__sourcepackagename__idx
    ON OAuthRequestToken (distribution, sourcepackagename)
    WHERE distribution IS NOT NULL;

ALTER TABLE OAuthRequestToken ADD CONSTRAINT sourcepackagename_needs_distro
    CHECK (sourcepackagename IS NULL OR distribution IS NOT NULL);

ALTER TABLE OAuthRequestToken ADD CONSTRAINT just_one_context
    CHECK (null_count(ARRAY[product, project, distribution]) >= 2);

ALTER TABLE OAuthAccessToken
    ADD COLUMN product INTEGER REFERENCES Product(id),
    ADD COLUMN project INTEGER REFERENCES Project(id),
    ADD COLUMN distribution INTEGER REFERENCES Distribution(id),
    ADD COLUMN sourcepackagename INTEGER REFERENCES SourcePackageName(id);

CREATE INDEX oauthaccesstoken__product__idx
    ON OAuthAccessToken (product) WHERE product IS NOT NULL;

CREATE INDEX oauthaccesstoken__project__idx
    ON OAuthAccessToken (project) WHERE project IS NOT NULL;

CREATE INDEX oauthaccesstoken__distribution__sourcepackagename__idx
    ON OAuthAccessToken (distribution, sourcepackagename)
    WHERE distribution IS NOT NULL;

ALTER TABLE OAuthAccessToken ADD CONSTRAINT sourcepackagename_needs_distro
    CHECK (sourcepackagename IS NULL OR distribution IS NOT NULL);


ALTER TABLE OAuthAccessToken ADD CONSTRAINT just_one_context
    CHECK (null_count(ARRAY[product, project, distribution]) >= 2);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 66, 0);

