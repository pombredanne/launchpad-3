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
CREATE INDEX project__emblem__idx ON Project(emblem)
    WHERE emblem IS NOT NULL;
CREATE INDEX project__gotchi__idx ON Project(gotchi)
    WHERE gotchi IS NOT NULL;


ALTER TABLE Product ADD COLUMN homepage_content text;
ALTER TABLE Product ADD COLUMN emblem integer;
ALTER TABLE Product ADD CONSTRAINT product__emblem__fk
                       FOREIGN KEY (emblem)
                       REFERENCES LibraryFileAlias(id);
ALTER TABLE Product ADD COLUMN gotchi integer;
ALTER TABLE Product ADD CONSTRAINT product__gotchi__fk
                       FOREIGN KEY (gotchi)
                       REFERENCES LibraryFileAlias(id);
CREATE INDEX product__emblem__idx ON Product(emblem)
    WHERE emblem IS NOT NULL;
CREATE INDEX product__gotchi__idx ON Product(gotchi)
    WHERE gotchi IS NOT NULL;


ALTER TABLE Distribution ADD COLUMN homepage_content text;
ALTER TABLE Distribution ADD COLUMN emblem integer;
ALTER TABLE Distribution ADD CONSTRAINT distribution__emblem__fk
                       FOREIGN KEY (emblem)
                       REFERENCES LibraryFileAlias(id);
ALTER TABLE Distribution ADD COLUMN gotchi integer;
ALTER TABLE Distribution ADD CONSTRAINT distribution__gotchi__fk
                       FOREIGN KEY (gotchi)
                       REFERENCES LibraryFileAlias(id);
CREATE INDEX distribution__emblem__idx ON Distribution(emblem)
    WHERE emblem IS NOT NULL;
CREATE INDEX distribution__gotchi__idx ON Distribution(gotchi)
    WHERE gotchi IS NOT NULL;


ALTER TABLE Sprint ADD COLUMN homepage_content text;
ALTER TABLE Sprint ADD COLUMN emblem integer;
ALTER TABLE Sprint ADD CONSTRAINT sprint__emblem__fk
                       FOREIGN KEY (emblem)
                       REFERENCES LibraryFileAlias(id);
ALTER TABLE Sprint ADD COLUMN gotchi integer;
ALTER TABLE Sprint ADD CONSTRAINT sprint__gotchi__fk
                       FOREIGN KEY (gotchi)
                       REFERENCES LibraryFileAlias(id);
CREATE INDEX sprint__emblem__idx ON Sprint(emblem)
    WHERE emblem IS NOT NULL;
CREATE INDEX sprint__gotchi__idx ON Sprint(gotchi)
    WHERE gotchi IS NOT NULL;

-- Make existing gotchi/emblem columns match existing column names
-- to make shared code easier.
ALTER TABLE Person RENAME COLUMN hackergotchi TO gotchi;
DROP INDEX person_hackergotchi_idx;
CREATE INDEX person__gotchi__idx ON Person(gotchi) WHERE gotchi IS NOT NULL;
DROP INDEX person_emblem_idx;
CREATE INDEX person__emblem__idx ON Person(emblem) WHERE emblem IS NOT NULL;
ALTER TABLE Person DROP CONSTRAINT person_emblem_fk;
ALTER TABLE Person ADD CONSTRAINT person__emblem__fk
    FOREIGN KEY (emblem) REFERENCES LibraryFileAlias;
ALTER TABLE Person DROP CONSTRAINT person_hackergotchi_fk;
ALTER TABLE Person ADD CONSTRAINT person__gotchi__fk
    FOREIGN KEY (gotchi) REFERENCES LibraryFileAlias;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 10, 0);

