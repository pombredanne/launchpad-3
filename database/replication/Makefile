HERE=`pwd`

default:
	echo Usage: make [start|stop|restart]

start:
	./slon_ctl.py start

stop:
	./slon_ctl.py stop

restart: stop start

initialize:
	LPCONFIG=demo1 python2.4 ./initialize.py -d lpmain_demo -H localhost -U slony 2>&1 | tee initialize.out

