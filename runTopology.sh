levels=${1:-1}
docker-compose exec mininet mn --custom /tmp/topology/datacenter.py --topo datacenter,$levels  --mac --arp --switch ovsk --controller remote

