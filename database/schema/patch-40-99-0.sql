SET client_min_messages=ERROR;

CREATE TABLE SupportContact (
    id SERIAL PRIMARY KEY,
    product INT REFERENCES Product(id),
    distribution INT REFERENCES Distribution(id),
    sourcepackagename INT REFERENCES SourcePackageName(id),
    person INT NOT NULL REFERENCES Person(id)
    );

/* XXX: The following constraints should be added to SupportContact:

          - Either product or distribution has to be set, but not both

          - (product, person) should be uniqe

          - (distribution, sourcepackagename=NULL, person) should be
            unique

          - (distribution, sourcepackagename!=NULL, person) should be
            unique

          - If product is not NULL, sourcepackagename has to be NULL.
*/

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 99, 0);

