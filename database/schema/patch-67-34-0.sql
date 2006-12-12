SET client_min_messages=ERROR;

ALTER TABLE Project ADD COLUMN homepage_content text;
ALTER TABLE Project ADD COLUMN emblem integer;
ALTER TABLE Project ADD CONSTRAINT project__emblem__fk
                       FOREIGN KEY (emblem)
                       REFERENCES LibraryFileAlias(id);
ALTER TABLE Project ADD COLUMN gotchi integer;
ALTER TABLE Project ADD CONSTRAINT project__gotchi__fk
                       FOREIGN KEY (gotchi)
                       REFERENCES LibraryFileAlias(id);
ALTER TABLE Project ADD COLUMN gotchi_heading integer;
ALTER TABLE Project ADD CONSTRAINT project__gotchi_heading__fk
                       FOREIGN KEY (gotchi_heading)
                       REFERENCES LibraryFileAlias(id);
CREATE INDEX project__emblem__idx ON Project(emblem)
    WHERE emblem IS NOT NULL;
CREATE INDEX project__gotchi__idx ON Project(gotchi)
    WHERE gotchi IS NOT NULL;
CREATE INDEX project__gotchi_heading__idx ON Project(gotchi_heading)
    WHERE gotchi_heading IS NOT NULL;


ALTER TABLE Product ADD COLUMN homepage_content text;
ALTER TABLE Product ADD COLUMN emblem integer;
ALTER TABLE Product ADD CONSTRAINT product__emblem__fk
                       FOREIGN KEY (emblem)
                       REFERENCES LibraryFileAlias(id);
ALTER TABLE Product ADD COLUMN gotchi integer;
ALTER TABLE Product ADD CONSTRAINT product__gotchi__fk
                       FOREIGN KEY (gotchi)
                       REFERENCES LibraryFileAlias(id);
ALTER TABLE Product ADD COLUMN gotchi_heading integer;
ALTER TABLE Product ADD CONSTRAINT product__gotchi_heading__fk
                       FOREIGN KEY (gotchi_heading)
                       REFERENCES LibraryFileAlias(id);
CREATE INDEX product__emblem__idx ON Product(emblem)
    WHERE emblem IS NOT NULL;
CREATE INDEX product__gotchi__idx ON Product(gotchi)
    WHERE gotchi IS NOT NULL;
CREATE INDEX product__gotchi_heading__idx ON Product(gotchi_heading)
    WHERE gotchi_heading IS NOT NULL;


ALTER TABLE Distribution ADD COLUMN homepage_content text;
ALTER TABLE Distribution ADD COLUMN emblem integer;
ALTER TABLE Distribution ADD CONSTRAINT distribution__emblem__fk
                       FOREIGN KEY (emblem)
                       REFERENCES LibraryFileAlias(id);
ALTER TABLE Distribution ADD COLUMN gotchi integer;
ALTER TABLE Distribution ADD CONSTRAINT distribution__gotchi__fk
                       FOREIGN KEY (gotchi)
                       REFERENCES LibraryFileAlias(id);
ALTER TABLE Distribution ADD COLUMN gotchi_heading integer;
ALTER TABLE Distribution ADD CONSTRAINT distribution__gotchi_heading__fk
                       FOREIGN KEY (gotchi_heading)
                       REFERENCES LibraryFileAlias(id);
CREATE INDEX distribution__emblem__idx ON Distribution(emblem)
    WHERE emblem IS NOT NULL;
CREATE INDEX distribution__gotchi__idx ON Distribution(gotchi)
    WHERE gotchi IS NOT NULL;
CREATE INDEX distribution__gotchi_heading__idx ON Distribution(gotchi_heading)
    WHERE gotchi_heading IS NOT NULL;


ALTER TABLE Sprint ADD COLUMN homepage_content text;
ALTER TABLE Sprint ADD COLUMN emblem integer;
ALTER TABLE Sprint ADD CONSTRAINT sprint__emblem__fk
                       FOREIGN KEY (emblem)
                       REFERENCES LibraryFileAlias(id);
ALTER TABLE Sprint ADD COLUMN gotchi integer;
ALTER TABLE Sprint ADD CONSTRAINT sprint__gotchi__fk
                       FOREIGN KEY (gotchi)
                       REFERENCES LibraryFileAlias(id);
ALTER TABLE Sprint ADD COLUMN gotchi_heading integer;
ALTER TABLE Sprint ADD CONSTRAINT sprint__gotchi_heading__fk
                       FOREIGN KEY (gotchi_heading)
                       REFERENCES LibraryFileAlias(id);
CREATE INDEX sprint__emblem__idx ON Sprint(emblem)
    WHERE emblem IS NOT NULL;
CREATE INDEX sprint__gotchi__idx ON Sprint(gotchi)
    WHERE gotchi IS NOT NULL;
CREATE INDEX sprint__gotchi_heading__idx ON Sprint(gotchi_heading)
    WHERE gotchi_heading IS NOT NULL;

ALTER TABLE Person RENAME COLUMN hackergotchi TO gotchi;
ALTER TABLE Person ADD COLUMN gotchi_heading integer;
ALTER TABLE Person ADD CONSTRAINT person__gotchi_heading__fk
                       FOREIGN KEY (gotchi_heading)
                       REFERENCES LibraryFileAlias(id);
CREATE INDEX person__gotchi_heading__idx ON Person(gotchi_heading)
    WHERE gotchi_heading IS NOT NULL;

UPDATE Person SET emblem = NULL 
    WHERE teamowner IS NULL AND emblem IS NOT NULL;
ALTER TABLE Person ADD CONSTRAINT people_have_no_emblems
    CHECK (emblem IS NULL OR teamowner IS NOT NULL);

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 34, 0);
