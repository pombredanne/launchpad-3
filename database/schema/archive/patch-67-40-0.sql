SET client_min_messages=ERROR;

CREATE TABLE OfficialBugTag (
    id serial PRIMARY KEY,
    tag text NOT NULL,
    distribution int REFERENCES Distribution,
    project int REFERENCES Project,
    product int REFERENCES Product,
    CONSTRAINT context_required CHECK
        (product IS NOT NULL OR distribution IS NOT NULL)
    );

CREATE UNIQUE INDEX officialbugtag__project__tag__key
    ON OfficialBugTag(project, tag)
    WHERE product IS NOT NULL;

CREATE UNIQUE INDEX officialbugtag__product__tag__key
    ON OfficialBugTag(product, tag)
    WHERE product IS NOT NULL;

CREATE UNIQUE INDEX officialbugtag__distribution__tag__key
    ON OfficialBugTag(distribution, tag)
    WHERE distribution IS NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 40, 0);

