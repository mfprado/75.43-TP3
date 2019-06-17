"""
Este archivo ejemplifica la creacion de una topologia de mininet
En este caso estamos creando una topologia muy simple con la siguiente forma

   host --- switch --- switch --- host
"""

from mininet.topo import Topo

class Datacenter( Topo ):

  def create_switches(self, levels):
    print("Initializing Switches")
    switches_by_level = {} 
    for level in range(levels):
       level_switches = []
       for switch in range(2**level):
         level_switches.append(self.addSwitch('sw1%d_%d'%(level,switch)))
       switches_by_level[level] = level_switches
    return switches_by_level

  def add_links_to_switches(self, switches_by_level):
    print("Initializing Links")
    for level, switches in switches_by_level.items():
      if level > 0:
        for switch1 in switches_by_level[level-1]:
          for switch2 in switches:
            self.addLink(switch1, switch2)
  
  def add_hosts_to_network(self, switches_by_level):
    root_switch = switches_by_level[0][0]
    print("Initializing Clients")
    for i in range(3):
      client = self.addHost('client%s'%i)
      self.addLink(root_switch, client)

    print("Initializing Providers")
    last_level = len(switches_by_level)-1
    for i, switch in enumerate(switches_by_level[last_level]):
      host = self.addHost('h%s'%i)
      self.addLink(switch, host)



  def __init__( self, levels = 1, half_ports = 2, **opts ):
    Topo.__init__(self, **opts)
    print("Initializing DataCenter Topology\nLevels: %s"%levels)

    switches_by_level = self.create_switches(levels)

    self.add_links_to_switches(switches_by_level)

    self.add_hosts_to_network(switches_by_level)

topos = { 'datacenter': Datacenter }
