
/*
  There still seem to be a few vestigial "bugsystem" objects around, this fragment
  should clean those up for good.
*/

ALTER TABLE bugsystem_pkey RENAME TO bugtracker_pkey;
ALTER TABLE bugsystemtype_name_key RENAME TO bugtrackertype_name_key;
ALTER TABLE bugsystemtype_pkey RENAME TO bugtrackertype_pkey;

