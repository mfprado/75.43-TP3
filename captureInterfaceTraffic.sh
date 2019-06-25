interface=${1:-sw1-eth1}
echo "Interface: $interface"

docker-compose exec mininet tcpdump -C 1000 -v -i $interface -w /tmp/tcpdump/tcpdump.pcap
