/* Script to patch a tsearch2 installation so that backup and dump work
   sanely. The tsearch2 that ships with PostgreSQL 7.4 uses OIDs as keys,
   which doesn't survive a dump and restore. This aptch fixes the problem

   This patch was downloaded from the tsearch2 home page
   http://www.sai.msu.su/~megera/postgres/gist/tsearch/V2/
*/
BEGIN;

-- altering columns for table pg_ts_dict and pg_ts_parser
-- add the new columns and their types, then update with old values

ALTER TABLE pg_ts_dict ADD COLUMN dict_init_tmp REGPROCEDURE;
UPDATE pg_ts_dict SET dict_init_tmp = dict_init;

ALTER TABLE pg_ts_dict ADD COLUMN dict_lexize_tmp REGPROCEDURE;
UPDATE pg_ts_dict SET dict_lexize_tmp = dict_lexize;
ALTER TABLE pg_ts_dict ALTER COLUMN dict_lexize_tmp SET NOT NULL;

ALTER TABLE pg_ts_parser ADD COLUMN prs_start_tmp REGPROCEDURE;
UPDATE pg_ts_parser SET prs_start_tmp = prs_start;
ALTER TABLE pg_ts_parser ALTER COLUMN prs_start_tmp SET NOT NULL;

ALTER TABLE pg_ts_parser ADD COLUMN prs_nexttoken_tmp REGPROCEDURE;
UPDATE pg_ts_parser SET prs_nexttoken_tmp = prs_nexttoken;
ALTER TABLE pg_ts_parser ALTER COLUMN prs_nexttoken_tmp SET NOT NULL;

ALTER TABLE pg_ts_parser ADD COLUMN prs_end_tmp REGPROCEDURE;
UPDATE pg_ts_parser SET prs_end_tmp = prs_end;
ALTER TABLE pg_ts_parser ALTER COLUMN prs_end_tmp SET NOT NULL;

ALTER TABLE pg_ts_parser ADD COLUMN prs_headline_tmp REGPROCEDURE;
UPDATE pg_ts_parser SET prs_headline_tmp = prs_headline;
ALTER TABLE pg_ts_parser ALTER COLUMN prs_headline_tmp SET NOT NULL;

ALTER TABLE pg_ts_parser ADD COLUMN prs_lextype_tmp REGPROCEDURE;
UPDATE pg_ts_parser SET prs_lextype_tmp = prs_lextype;
ALTER TABLE pg_ts_parser ALTER COLUMN prs_lextype_tmp SET NOT NULL;

-- drop the old columns, and rename the new ones

ALTER TABLE pg_ts_dict DROP COLUMN dict_init;
ALTER TABLE pg_ts_dict RENAME COLUMN dict_init_tmp TO dict_init;

ALTER TABLE pg_ts_dict DROP COLUMN dict_lexize;
ALTER TABLE pg_ts_dict RENAME COLUMN dict_lexize_tmp TO dict_lexize;

ALTER TABLE pg_ts_parser DROP COLUMN prs_start;
ALTER TABLE pg_ts_parser RENAME COLUMN prs_start_tmp TO prs_start;

ALTER TABLE pg_ts_parser DROP COLUMN prs_nexttoken;
ALTER TABLE pg_ts_parser RENAME COLUMN prs_nexttoken_tmp TO prs_nexttoken;

ALTER TABLE pg_ts_parser DROP COLUMN prs_end;
ALTER TABLE pg_ts_parser RENAME COLUMN prs_end_tmp TO prs_end;

ALTER TABLE pg_ts_parser DROP COLUMN prs_headline;
ALTER TABLE pg_ts_parser RENAME COLUMN prs_headline_tmp TO prs_headline;

ALTER TABLE pg_ts_parser DROP COLUMN prs_lextype;
ALTER TABLE pg_ts_parser RENAME COLUMN prs_lextype_tmp TO prs_lextype;

END;
