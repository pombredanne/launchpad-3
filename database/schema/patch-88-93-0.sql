SET client_min_messages=ERROR;

CREATE TABLE NewsItem (
    id serial PRIMARY KEY,
    date_created timestamp without time zone
                 DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_announced timestamp without time zone
                 DEFAULT timezone('UTC'::text, now()),
    registrant integer NOT NULL REFERENCES Person(id),
    product integer REFERENCES Product(id),
    distribution integer REFERENCES Distribution(id),
    project integer REFERENCES Project(id),
    title text NOT NULL,
    summary text,
    url text,
    active boolean NOT NULL DEFAULT TRUE
    );

CREATE INDEX newsitem__product__idx ON NewsItem(product);
CREATE INDEX newsitem__project__idx ON NewsItem(project);
CREATE INDEX newsitem__distribution__idx ON NewsItem(distribution);

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 93, 0);

