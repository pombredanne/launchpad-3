SET client_min_messages=ERROR;

ALTER TABLE Person RENAME COLUMN emblem TO icon;
ALTER TABLE person_emblem_idx RENAME TO person__icon__idx;
ALTER TABLE Person DROP CONSTRAINT person_emblem_fk;
ALTER TABLE Person ADD CONSTRAINT person__icon__fk
    FOREIGN KEY (icon) REFERENCES LibraryFileAlias;

ALTER TABLE Person RENAME COLUMN gotchi_heading TO logo;
ALTER TABLE person__gotchi_heading__idx RENAME TO person__logo__idx;
ALTER TABLE Person DROP CONSTRAINT person__gotchi_heading__fk;
ALTER TABLE Person ADD CONSTRAINT person__logo__fk
    FOREIGN KEY (logo) REFERENCES LibraryFileAlias;

ALTER TABLE Person RENAME COLUMN gotchi TO mugshot;
ALTER TABLE person_hackergotchi_idx RENAME TO person__mugshot__idx;
ALTER TABLE Person DROP CONSTRAINT person_hackergotchi_fk;
ALTER TABLE Person ADD CONSTRAINT person__mugshot__fk
    FOREIGN KEY (mugshot) REFERENCES LibraryFileAlias;


ALTER TABLE Sprint RENAME COLUMN emblem TO icon;
ALTER TABLE sprint__emblem__idx RENAME TO sprint__icon__idx;
ALTER TABLE Sprint DROP CONSTRAINT sprint__emblem__fk;
ALTER TABLE Sprint ADD CONSTRAINT sprint__icon__fk
    FOREIGN KEY (icon) REFERENCES LibraryFileAlias;

ALTER TABLE Sprint RENAME COLUMN gotchi_heading TO logo;
ALTER TABLE sprint__gotchi_heading__idx RENAME TO sprint__logo__idx;
ALTER TABLE Sprint DROP CONSTRAINT sprint__gotchi_heading__fk;
ALTER TABLE Sprint ADD CONSTRAINT sprint__logo__fk
    FOREIGN KEY (logo) REFERENCES LibraryFileAlias;

ALTER TABLE Sprint RENAME COLUMN gotchi TO mugshot;
ALTER TABLE sprint__gotchi__idx RENAME TO sprint__mugshot__idx;
ALTER TABLE Sprint DROP CONSTRAINT sprint__gotchi__fk;
ALTER TABLE Sprint ADD CONSTRAINT sprint__mugshot__fk
    FOREIGN KEY (mugshot) REFERENCES LibraryFileAlias;


ALTER TABLE Product RENAME COLUMN emblem TO icon;
ALTER TABLE product__emblem__idx RENAME TO product__icon__idx;
ALTER TABLE Product DROP CONSTRAINT product__emblem__fk;
ALTER TABLE Product ADD CONSTRAINT product__icon__fk
    FOREIGN KEY (icon) REFERENCES LibraryFileAlias;

ALTER TABLE Product RENAME COLUMN gotchi_heading TO logo;
ALTER TABLE product__gotchi_heading__idx RENAME TO product__logo__idx;
ALTER TABLE Product DROP CONSTRAINT product__gotchi_heading__fk;
ALTER TABLE Product ADD CONSTRAINT product__logo__fk
    FOREIGN KEY (logo) REFERENCES LibraryFileAlias;

ALTER TABLE Product RENAME COLUMN gotchi TO mugshot;
ALTER TABLE product__gotchi__idx RENAME TO product__mugshot__idx;
ALTER TABLE Product DROP CONSTRAINT product__gotchi__fk;
ALTER TABLE Product ADD CONSTRAINT product__mugshot__fk
    FOREIGN KEY (mugshot) REFERENCES LibraryFileAlias;


ALTER TABLE Project RENAME COLUMN emblem TO icon;
ALTER TABLE project__emblem__idx RENAME TO project__icon__idx;
ALTER TABLE Project DROP CONSTRAINT project__emblem__fk;
ALTER TABLE Project ADD CONSTRAINT project__icon__fk
    FOREIGN KEY (icon) REFERENCES LibraryFileAlias;

ALTER TABLE Project RENAME COLUMN gotchi_heading TO logo;
ALTER TABLE project__gotchi_heading__idx RENAME TO project__logo__idx;
ALTER TABLE Project DROP CONSTRAINT project__gotchi_heading__fk;
ALTER TABLE Project ADD CONSTRAINT project__logo__fk
    FOREIGN KEY (logo) REFERENCES LibraryFileAlias;

ALTER TABLE Project RENAME COLUMN gotchi TO mugshot;
ALTER TABLE project__gotchi__idx RENAME TO project__mugshot__idx;
ALTER TABLE Project DROP CONSTRAINT project__gotchi__fk;
ALTER TABLE Project ADD CONSTRAINT project__mugshot__fk
    FOREIGN KEY (mugshot) REFERENCES LibraryFileAlias;


ALTER TABLE Distribution RENAME COLUMN emblem TO icon;
ALTER TABLE distribution__emblem__idx RENAME TO distribution__icon__idx;
ALTER TABLE Distribution DROP CONSTRAINT distribution__emblem__fk;
ALTER TABLE Distribution ADD CONSTRAINT distribution__icon__fk
    FOREIGN KEY (icon) REFERENCES LibraryFileAlias;

ALTER TABLE Distribution RENAME COLUMN gotchi_heading TO logo;
ALTER TABLE distribution__gotchi_heading__idx RENAME TO distribution__logo__idx;
ALTER TABLE Distribution DROP CONSTRAINT distribution__gotchi_heading__fk;
ALTER TABLE Distribution ADD CONSTRAINT distribution__logo__fk
    FOREIGN KEY (logo) REFERENCES LibraryFileAlias;

ALTER TABLE Distribution RENAME COLUMN gotchi TO mugshot;
ALTER TABLE distribution__gotchi__idx RENAME TO distribution__mugshot__idx;
ALTER TABLE Distribution DROP CONSTRAINT distribution__gotchi__fk;
ALTER TABLE Distribution ADD CONSTRAINT distribution__mugshot__fk
    FOREIGN KEY (mugshot) REFERENCES LibraryFileAlias;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 8, 0);

