from pox.core import core
import pox.openflow.libopenflow_01 as of

log = core.getLogger()

class SwitchController:
  def __init__(self, dpid, connection, controller):
    self.dpid = dpid
    self.connection = connection
    # El SwitchController se agrega como handler de los eventos del switch
    self.connection.addListeners(self)
    self.controller = controller
    #Esta tabla es un diccionario cuya clave es una tupla (mac_origen, mac_destino) y el valor es el
    #puerto de salida.
    self.flow_table = {}

  def _handle_PacketIn(self, event):
    """
    Esta funcion es llamada cada vez que el switch recibe un paquete
    y no encuentra en su tabla una regla para rutearlo
    """
    self.controller.host_tracker._handle_openflow_PacketIn(event)

    packet = event.parse

    log.info("---------------------PACKET ARRIVED--------------------------")
    log.info("Packet arrived to switch %s from %s to %s", self.dpid, packet.src, packet.dst)
    log.info("Packet is from type %s", packet.type)

    next_hop = self.get_next_hop(packet)

    if not next_hop:
      self.search_for_minimum_path(event)
      # En caso de que no haya next_hop, en search_for_minimum_path se escribe en la tabla del switch.
      next_hop = self.get_next_hop(packet, event)
      if not next_hop:
        self.flood_packet(event)
        return

    self.forward(next_hop, event)
    log.info("---------------------FINISHED --------------------------")

  def get_next_hop(self, packet):
    src = packet.src
    destination = packet.dst
    return self.flow_table.get((src, destination), default = None)

  def search_for_minimum_path(self, event):
    destination = event.parse.dst
    destination_entry = self.controller.host_tracker.getMacEntry(destination)

    if destination_entry != None:
      log.info("port entry is: " + str(destination_entry.inport))
      log.info("dpid entry is: " + str(destination_entry.dpid))
      log.info("maccadr is: " + str(destination_entry.macaddr))

      switch_origin = self.dpid
      switch_destination = destination_entry.dpid

      path = self.controller.ecmp_path(switch_origin, switch_destination)

      self.controller.write_on_tables(path, event.parse.src, event.parse.dst)

    else:
      self.flood_packet(event)

  def flood_packet(self, event):
    msg = of.ofp_packet_out()
    msg.buffer_id = event.ofp.buffer_id
    msg.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD))
    msg.data = event.ofp
    msg.in_port = event.port
    self.connection.send(msg)

  def forward(self, port, event):
    msg = of.ofp_packet_out()
    msg.actions.append(of.ofp_action_output(port=port))
    if event.ofp.buffer_id is not None:
      msg.buffer_id = event.ofp.buffer_id
    else:
      msg.data = event.ofp.data
    msg.in_port = event.port
    self.connection.send(msg)

  def write_on_table(self, tuple_macs, next_hop):
    pass
  def get_dpid(self):
    return self.dpid

  def setTopology(self, topology):
    self.topology = topology