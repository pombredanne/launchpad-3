SET client_min_messages TO error;

/*
 * This patch is to split pomsgsets and potmsgsets to improve and simplify
 * the code that handles them.
 */

CREATE TABLE potmsgset (
    id serial NOT NULL,
    primemsgid integer NOT NULL,
    "sequence" integer NOT NULL,
    potemplate integer NOT NULL,
    commenttext text,
    filereferences text,
    sourcecomment text,
    flagscomment text
);

ALTER TABLE potmsgset ADD CONSTRAINT potmsgset_pkey PRIMARY KEY (id);
ALTER TABLE potmsgset ADD CONSTRAINT potmsgset_potemplate_key UNIQUE (potemplate, primemsgid);
ALTER TABLE potmsgset ADD CONSTRAINT potmsgset_primemsgid_fk FOREIGN KEY (primemsgid) REFERENCES pomsgid(id);
ALTER TABLE potmsgset ADD CONSTRAINT potmsgset_potemplate_fk FOREIGN KEY (potemplate) REFERENCES potemplate(id);

ALTER TABLE pomsgset DROP primemsgid;
ALTER TABLE pomsgset DROP potemplate;
ALTER TABLE pomsgset DROP filereferences;
ALTER TABLE pomsgset DROP sourcecomment;
ALTER TABLE pomsgset DROP flagscomment;

ALTER TABLE pomsgset ADD potmsgset integer;
ALTER TABLE pomsgset ALTER potmsgset SET NOT NULL;
ALTER TABLE pomsgset ALTER pofile SET NOT NULL;
ALTER TABLE pomsgset ADD CONSTRAINT pomsgset_pofile_key UNIQUE (pofile, potmsgset);
ALTER TABLE pomsgset ADD CONSTRAINT pomsgset_potmsgset_fk FOREIGN KEY(potmsgset) REFERENCES potmsgset(id);

ALTER TABLE pomsgidsighting RENAME pomsgset TO potmsgset;
ALTER TABLE pomsgidsighting DROP CONSTRAINT "$1";
ALTER TABLE pomsgidsighting ADD CONSTRAINT pomsgidsighting_potmsgset_key UNIQUE (potmsgset, pomsgid);
ALTER TABLE pomsgidsighting ADD CONSTRAINT pomsgidsighting_potmsgset_fk FOREIGN KEY (potmsgset) REFERENCES potmsgset(id);
