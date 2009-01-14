SET client_min_messages=ERROR;

ALTER TABLE Entitlement
    ADD COLUMN Distribution integer REFERENCES Distribution,
    ADD COLUMN Product integer REFERENCES Product,
    ADD COLUMN Project integer REFERENCES Project,
    ALTER COLUMN Person DROP NOT NULL;

ALTER TABLE Entitlement
    ADD CONSTRAINT only_one_target CHECK (
        null_count(ARRAY[person, product, project, distribution]) = 3);

CREATE INDEX entitlement__distribution__idx ON Entitlement(distribution)
    WHERE distribution IS NOT NULL;
CREATE INDEX entitlement__product__idx ON Entitlement(product)
    WHERE product IS NOT NULL;
CREATE INDEX entitlement__project__idx ON Entitlement(project)
    WHERE project  IS NOT NULL;

ALTER TABLE PillarName ADD COLUMN alias_for integer;
ALTER TABLE PillarName ADD CONSTRAINT pillarname__alias_for__fk
    FOREIGN KEY (alias_for) REFERENCES PillarName;
CREATE INDEX pillarname__alias_for__idx on PillarName(alias_for)
    WHERE alias_for IS NOT NULL;

ALTER TABLE PillarName DROP CONSTRAINT only_one_target;
ALTER TABLE PillarName
    ADD CONSTRAINT only_one_target CHECK (
        null_count(ARRAY[product, project, distribution, alias_for]) = 3);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 19, 0);
