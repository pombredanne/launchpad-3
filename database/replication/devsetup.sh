# Script to initialize a Slony-I cluster on a dev box. Does not setup
# /etc/slony1 configs (yet).
sudo /etc/init.d/slony1 stop
dropdb launchpad_dev
dropdb launchpad_dev_slave1
createdb launchpad_dev_slave1 || exit 1
make -C ~/lp/replication/database/schema || exit 1
sudo /etc/init.d/slony1 start || exit 1
./initialize.py -vv
