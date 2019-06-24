from pox.core import core
import pox.openflow.discovery
import pox.openflow.spanning_tree
import pox.forwarding.l2_learning
from pox.lib.util import dpid_to_str
from extensions.switch import SwitchController
import pox.openflow.libopenflow_01 as of
from pox.lib.addresses import EthAddr, IPAddr
from pox.host_tracker.host_tracker import host_tracker
from extensions.ecmp_utils import ECMPUtil

log = core.getLogger()

class Controller:
  def __init__ (self):
    self.connections = set()
    self.switches = []
    self.topology = {}
    self.links_counter = 0
    self.host_tracker = host_tracker()
    self.hosts_by_switch = {}
    self.ecmp_util = ECMPUtil()

    # Esperando que los modulos openflow y openflow_discovery esten listos
    core.call_when_ready(self.startup, ('openflow', 'openflow_discovery'))

  def startup(self):
    """
    Esta funcion se encarga de inicializar el controller
    Agrega el controller como event handler para los eventos de
    openflow y openflow_discovery
    """
    core.openflow.addListeners(self)
    core.openflow_discovery.addListeners(self)
    log.info('Controller initialized')

  def _handle_ConnectionUp(self, event):
    """
    Esta funcion es llamada cada vez que un nuevo switch establece conexion
    Se encarga de crear un nuevo switch controller para manejar los eventos de cada switch
    """
    log.info("Switch %s has come up.", dpid_to_str(event.dpid))
    if (event.connection not in self.connections):
      self.connections.add(event.connection)
      self.topology[event.dpid] = set()

      sw = SwitchController(event.dpid, event.connection, self)
      self.switches.append(sw)

  def _handle_LinkEvent(self, event):
      """
      Esta funcion es llamada cada vez que openflow_discovery descubre un nuevo enlace
      """
      link = event.link
      self.links_counter += 1
      log.info("Link has been discovered from %s,%s to %s,%s", dpid_to_str(link.dpid1), link.port1, dpid_to_str(link.dpid2), link.port2)
      log.info("The discovered link is the %dth link"%self.links_counter)

      self.topology[link.dpid1].add((link.dpid2, link.port1))
      self.log_topology()
      self.ecmp_util.update(self.topology)

  def ecmp_path(self, switch_origin, switch_destination):
    return self.ecmp_util.get_path(switch_origin, switch_destination)

  def log_topology(self):
    log.info("The resultant topology after the discovery is: ")
    for switch, adjacents in self.topology.items():
        log.info('switch: ' + str(switch) + ' have this adjacents: ' + str(list(adjacents)))


  def write_on_tables(self, path, source_mac_address, destination_mac_address):
    for i in range(0, len(path) - 1):
      print("path", path)
      dpid_switch = path[i][0]
      next_hop = path[i][1]
      switch_controller = self.get_switch_by_dpid(dpid_switch)
      switch_controller.write_on_table((source_mac_address, destination_mac_address), next_hop)

  def get_switch_by_dpid(self, dpid):
      for switch in self.switches:
        if dpid == switch.get_dpid():
            return switch

      log.info("Exception: Switch not founded.")


def launch():
  # Inicializando el modulo openflow_discovery
  pox.openflow.discovery.launch()

  # Registrando el Controller en pox.core para que sea ejecutado
  core.registerNew(Controller)
