SET client_min_messages=ERROR;

-- Remove arch-related fields from ProductSeries

alter table productseries drop column targetarcharchive;
alter table productseries drop column targetarchcategory;
alter table productseries drop column targetarchbranch;
alter table productseries drop column targetarchversion;

-- Remove the WHUI bkrepository field too

alter table productseries drop column bkrepository;


-- Reinstate the no_empty_string constraint that referred to the deleted fields

alter table productseries add constraint no_empty_strings check (cvsroot <> ''::text AND cvsmodule <> ''::text AND cvsbranch <> ''::text AND svnrepository <> ''::text);

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 22, 0);
