HERE=`pwd`


default:
	echo Usage: make [start|stop|restart]

start: start_lpmain start_authdb

stop: stop_lpmain stop_authdb

restart: stop start

start_lpmain:
	start-stop-daemon --start --background --pidfile=${HERE}/slon_lpmain_demo.pid --exec /usr/bin/slon --startas /bin/sh -- -c "slon -d 2 -p ${HERE}/slon_lpmain_demo.pid sl 'user=slony dbname=lpmain_demo' >> ${HERE}/slon_lpmain_demo.log"

start_authdb:
	start-stop-daemon --start --background --pidfile=${HERE}/slon_authdb_demo.pid --exec /usr/bin/slon --startas /bin/sh -- -c "slon -d 2 -p ${HERE}/slon_authdb_demo.pid sl 'user=slony dbname=authdb_demo' >> ${HERE}/slon_authdb_demo.log"

stop_lpmain:
	start-stop-daemon --stop --pidfile=${HERE}/slon_lpmain_demo.pid

stop_authdb:
	start-stop-daemon --stop --pidfile=${HERE}/slon_authdb_demo.pid

initialize:
	LPCONFIG=demo1 python2.4 ./initialize.py -d lpmain_demo -H localhost -U slony 2>&1 | tee initialize.out

