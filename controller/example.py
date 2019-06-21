from pox.core import core
import pox.openflow.discovery
import pox.openflow.spanning_tree
import pox.forwarding.l2_learning
from pox.lib.util import dpid_to_str
from extensions.switch import SwitchController

log = core.getLogger()

class Controller:
  def __init__ (self):
    self.connections = set()
    self.switches = []
    self.topology = {}
    self.links_counter = 0

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
      sw = SwitchController(event.dpid, event.connection)
      self.switches.append(sw)
      self.topology[event.dpid] = set()

  def _handle_LinkEvent(self, event):
      """
      Esta funcion es llamada cada vez que openflow_discovery descubre un nuevo enlace
      """
      link = event.link
      self.links_counter += 1
      log.info("Link has been discovered from %s,%s to %s,%s", dpid_to_str(link.dpid1), link.port1, dpid_to_str(link.dpid2), link.port2)
      log.info("The discovered link is the %dth link"%self.links_counter)

      self.topology[link.dpid1].add(link.dpid2)
      self.log_topology()

  def log_topology(self):
    log.info("The resultant topology after the discovery is: ")
    for switch, adjacents in self.topology.items():
        log.info('switch: ' + str(switch) + ' have this adjacents: ' + str(list(adjacents)))

def launch():
  # Inicializando el modulo openflow_discovery
  pox.openflow.discovery.launch()

  # Registrando el Controller en pox.core para que sea ejecutado
  core.registerNew(Controller)

  """
  Corriendo Spanning Tree Protocol y el modulo l2_learning.
  No queremos correrlos para la resolucion del TP.
  Aqui lo hacemos a modo de ejemplo
  """
