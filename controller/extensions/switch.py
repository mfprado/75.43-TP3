from pox.core import core
import pox.openflow.libopenflow_01 as of
import pox.lib.packet.ethernet as ethernet

log = core.getLogger()

class SwitchController:
  def __init__(self, dpid, connection, controller):
    self.controller = controller
    self.dpid = dpid
    self.connection = connection

    # El SwitchController se agrega como handler de los eventos del switch
    self.connection.addListeners(self)

    #Esta tabla es un diccionario cuya clave es una tupla (mac_origen, mac_destino) y el valor es el
    #puerto de salida.
    self.flow_table = {}

  def _handle_PacketIn(self, event):
    """
    Esta funcion es llamada cada vez que el switch recibe un paquete
    y no encuentra en su tabla una regla para rutearlo
    """
    self.controller.host_tracker._handle_openflow_PacketIn(event)

    packet = event.parsed

    log.info("---------------------PACKET ARRIVED--------------------------")
    log.info("Packet arrived to switch %s from %s to %s", self.dpid, packet.src, packet.dst)
    log.info("Packet is from type %s", ethernet.getNameForType(packet.type))

    next_hop = self.get_next_hop(packet)


    if not next_hop:
      self.search_for_minimum_path(event)
      # En caso de que no haya next_hop, en search_for_minimum_path se escribe en la tabla del switch.
      next_hop = self.get_next_hop(packet)
      if not next_hop:
        #self.flood_packet(event)
        return

    log.info("Founded entry in switch table.")

    self.forward(next_hop, event)
    log.info("---------------------FINISHED --------------------------")

  def get_next_hop(self, packet):
    src = packet.src
    destination = packet.dst
    return self.flow_table.get((src, destination), None)

  def search_for_minimum_path(self, event):
    destination = event.parsed.dst
    destination_entry = self.controller.host_tracker.getMacEntry(destination)

    if destination_entry != None:
      log.info("port entry is: " + str(destination_entry.port))
      log.info("dpid entry is: " + str(destination_entry.dpid))
      log.info("maccadr is: " + str(destination_entry.macaddr))

      switch_origin = self.dpid
      switch_destination = destination_entry.dpid

      if switch_origin == switch_destination:
        self.forward(destination_entry.port, event)
        return

      path = self.controller.ecmp_path(switch_origin, switch_destination)

      self.controller.write_on_tables(path, event.parsed.src, event.parsed.dst)

  def flood_packet(self, event):
    msg = of.ofp_packet_out()
    msg.buffer_id = event.ofp.buffer_id
    msg.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD))
    msg.data = event.ofp
    msg.in_port = event.port
    log.info("FLOODING PACKET")
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

  def drop(self, event):
      """Tell the switch to drop the packet"""
      if event.ofp.buffer_id is not None:  # No se dropea porque el paquete no esta en el Switch Buffer
          msg = of.ofp_packet_out()
          msg.buffer_id = event.ofp.buffer_id
          event.ofp.buffer_id = None
          msg.in_port = event.port
          self.connection.send(msg)

  def write_on_table(self, tuple_macs, next_hop):
    self.flow_table[tuple_macs] = next_hop

  def get_dpid(self):
    return self.dpid

  def setTopology(self, topology):
    self.topology = topology