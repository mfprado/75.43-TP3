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
import datetime as dt


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
    self.has_updated_ecmp = False

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
      if (event.dpid not in self.connections):
          log.info("Switch %s has come up.", dpid_to_str(event.dpid))
          self.connections.add(event.dpid)
          self.topology[event.dpid] = set()
          sw = SwitchController(event.dpid, event.connection, self)
          self.switches.append(sw)
          self.has_updated_ecmp = False
          self.clean_switches_table()


  def _handle_LinkEvent(self, event):
      """
      Esta funcion es llamada cada vez que openflow_discovery descubre un nuevo enlace
      """
      link = event.link
      log.info("Link has been discovered from %s,%s to %s,%s", dpid_to_str(link.dpid1), link.port1, dpid_to_str(link.dpid2), link.port2)
      log.info("The discovered link is the %dth link"%self.links_counter)

      if event.added:
          if (link.dpid2, link.port1) in self.topology[link.dpid1]:
              log.info("Ignoring added link because is already in the topology")
              return
          else:
              self.links_counter += 1
              self.topology[link.dpid1].add((link.dpid2, link.port1))

      if event.removed:
          if (link.dpid2, link.port1) not in self.topology[link.dpid1]:
              log.info("Ignoring removed link because it doesnt belong to the topology")
              return
          else:
              self.links_counter -= 1
              self.topology[link.dpid1].remove((link.dpid2, link.port1))

      self.clean_switches_table()
      self.log_topology()
      self.has_updated_ecmp = False

  def delete_switch(self, switch_dpid):
      self.connections.remove(switch_dpid)
      adjacencys = [edge[0] for edge in self.topology[switch_dpid]]
      for adjacency in adjacencys:
          edges_to_clean = self.topology[adjacency]
          cleaned_egdes = set([edge for edge in edges_to_clean if switch_dpid not in edge])
          self.topology[adjacency] = cleaned_egdes
      del self.topology[switch_dpid]
      self.has_updated_ecmp = False
      self.clean_switches_table()

  def ecmp_path(self, switch_origin, switch_destination):
    if not self.has_updated_ecmp:
        log.info("Updating topology")
        log.info(dt.datetime.now())
        self.has_updated_ecmp = True
        self.ecmp_util.update(self.topology)
        log.info(dt.datetime.now())
    log.info("Asking path to go from %s to %s"%(switch_origin, switch_destination))
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

  def clean_switches_table(self):
      for swicht in self.switches:
          swicht.clean_table()

def launch():
  # Inicializando el modulo openflow_discovery
  pox.openflow.discovery.launch()

  # Registrando el Controller en pox.core para que sea ejecutado
  core.registerNew(Controller)
