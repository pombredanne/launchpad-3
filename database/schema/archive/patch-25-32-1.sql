set client_min_messages=error;

drop index one_launchpad_wikiname;
create unique index one_launchpad_wikiname on wikiname(person) where wiki = 'https://wiki.ubuntu.com/';

insert into launchpaddatabaserevision values (25, 32, 1);

