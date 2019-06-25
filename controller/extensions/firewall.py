from pox.lib.recoco import Timer
import pox.openflow.libopenflow_01 as of
import pox.lib.packet as pkt
from pox.core import core

TIMER_INTERVAL = 2
UNLOCK_INTERVAL = 10
MAX_UDP_PACKETS = 50


class Firewall:
    def __init__(self, log):
        core.openflow.addListenerByName("FlowStatsReceived",
                                        self.handle_flow_stats)
        Timer(TIMER_INTERVAL, Firewall.take_statistics, recurring=True)
        Timer(UNLOCK_INTERVAL, self.unlock_all, recurring=True)
        self.locked_ips = set()
        self.log = log

    @staticmethod
    def take_statistics():
        for connection in core.openflow.connections:
            connection.send(of.ofp_stats_request(body=of.ofp_flow_stats_request()))

    def handle_flow_stats(self, event):
        stats = {}
        for f in event.stats:
            if f.match.dst_ip in self.locked_ips:
                continue
            if f.match.nw_proto == pkt.ipv4.UDP_PROTOCOL:
                if f.match.dst_ip not in stats:
                    stats[f.match.dst_ip] = 1
                else:
                    stats[f.match.dst_ip] += 1
                if stats[f.match.dst_ip] > MAX_UDP_PACKETS:
                    self.lock(f.match.dst_ip)

    def lock(self, dst_ip):
        self.log.info("Blocking %s", dst_ip)
        msg = of.ofp_flow_mod()
        msg.match.nw_proto = pkt.ipv4.UDP_PROTOCOL
        msg.priority = of.OFP_DEFAULT_PRIORITY + 1
        msg.match.nw_dst = dst_ip
        self.locked_ips.update([dst_ip])
        for connection in core.openflow.connections:
            connection.send(msg)

    def unlock_all(self):
        for dst_ip in self.locked_ips:
            msg = of.ofp_flow_mod()
            msg.match.nw_proto = pkt.ipv4.UDP_PROTOCOL
            msg.priority = of.OFP_DEFAULT_PRIORITY + 2
            msg.match.nw_dst = dst_ip
            msg.command = of.OFPFC_DELETE
            for connection in core.openflow.connections:
                connection.send(msg)
            self.locked_ips.remove(dst_ip)

