SET client_min_messages=ERROR;

CREATE TABLE Announcement (
    id serial PRIMARY KEY,
    date_created timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    date_announced timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    registrant integer NOT NULL REFERENCES Person(id),
    product integer REFERENCES Product(id),
    distribution integer REFERENCES Distribution(id),
    project integer REFERENCES Project(id),
    title text NOT NULL,
    summary text,
    url text,
    active boolean NOT NULL DEFAULT TRUE,
    CONSTRAINT valid_url CHECK (valid_absolute_url(url)),
    CONSTRAINT has_target CHECK (
        product IS NOT NULL OR project IS NOT NULL
        OR distribution IS NOT NULL
        )
    );

-- Indexes for lookups
CREATE INDEX announcement__product__active__idx ON Announcement(product, active)
    WHERE product IS NOT NULL;
CREATE INDEX announcement__project__active__idx ON Announcement(project, active)
    WHERE project IS NOT NULL;
CREATE INDEX announcement__distribution__active__idx
    ON Announcement(distribution, active) WHERE distribution IS NOT NULL;

-- Indexes for people merge
CREATE INDEX announcement__registrant__idx ON Announcement(registrant);

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 22, 0);

