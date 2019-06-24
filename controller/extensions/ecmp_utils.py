

class ECMPUtil():
    """
    links: a dictionary of sets with the links
    use_counts: a dictionary of edges and it use count
    paths: a dictionary of paths
    ports: a dictionary with a port for each edge
    """
    def __init__(self):
        self.links = None
        self.use_counts = None
        self.paths = None
        self.ports = None

    @staticmethod
    def bfs_path_recursive(start, end, links, use_counts, previous, parents, visited):
        """
        Its our recursive strategy for BFS with a greedy optimization for each step

        :param start: the start vertice of this recursive iteration
        :param end: the target end
        :param links: the links dictionary
        :param use_counts: the use counts dictionary for each edge tuple
        :param previous: the vertice from the previous iteration
        :param parents: the parents dictionary that tracks the path
        :param visited: a visited set
        :return: a parents dictionary
        """
        parents[start] = previous
        visited.update([previous])
        # We have found our target:
        if start == end:
            return parents
        # Our target is not reacheable:
        if start not in links:
            return None
        # We now use a greedy strategy to iterate the neighbors using the least used first
        # Is not our goal to minimize the total used cost,
        # just the local on each step because we want the optimal length also,
        # and dijkstra (global cost) cant guarantee us that
        neighbors = [(link, use_counts[(start, link)]) for link in links[start]]
        neighbors = [n[0] for n in sorted(neighbors, key=lambda x: x[1])]
        for neigh in neighbors:
            # Tipical if for BFS to avoid loops
            if neigh in visited:
                continue
            # We get the parents of this step, could be None
            _parents = ECMPUtil.bfs_path_recursive(neigh, end, links, use_counts, start, parents.copy(), visited.copy())
            if _parents:
                return _parents

    @staticmethod
    def bfs_path(start, end, links, use_counts):
        """
        Recursive BFS with a greedy strategy while prioritizing the next hop

        :param start: the start vertice
        :param end: the target vertice
        :param links: the dictionary of sets containing the edges
        :param use_counts: the use counts dictionary for each edge tuple
        :return: a list as a path, containing the start and end
        """
        parents = {}
        visited = set()
        neighbors = [(link, use_counts[(start, link)]) for link in links[start]]
        neighbors = [n[0] for n in sorted(neighbors, key=lambda x: x[1])]
        visited.update([start])
        for neigh in neighbors:
            _parents = ECMPUtil.bfs_path_recursive(neigh, end, links, use_counts, start, parents.copy(), visited.copy())
            if _parents:
                path = []
                actual = end
                while True:
                    path.append(_parents[actual])
                    actual = _parents[actual]
                    if actual not in _parents:
                        return list(reversed(path)) + [end]

    def get_path(self, start, end):
        assert self.paths
        path = self.paths[(start, end)]
        new_path = []
        for i in range(len(path)-1):
            new_path.append((path[i],self.ports[(path[i], path[i+1])]))
        return new_path+[end]

    def update(self, topology):
        """
        Updates the topology

        :param topology: a dictionary of sets with tuple (switch, port)
        """
        vertices = ([sw for sw in topology.keys()] +
                    [edge[0] for edges in topology.values() for edge in edges])
        vertices = list(set(vertices))
        self.ports = {(sw, edge[0]): edge[1] for sw, edges in topology.items() for edge in edges}
        self.links = {sw: set(map(lambda x: x[0], edges)) for sw, edges in topology.items()}
        links_reversed = {}
        for k, vertices in self.links.items():
            for v in vertices:
                if v in links_reversed:
                    links_reversed[v] = {k}
                else:
                    links_reversed[v].update([k])
        for k in links_reversed.keys():
            if k in self.links:
                self.links[k].update(links_reversed[k])
            else:
                self.links[k] = links_reversed[k]
        self.use_counts = {(origin, end): 0 for origin in self.links.keys() for end in self.links[origin]}
        self.paths = {}
        for v1 in vertices:
            for v2 in vertices:
                path = ECMPUtil.bfs_path(v1, v2, self.links, self.use_counts)
                if path:
                    self.paths[(v1, v2)] = path
                    # We update the use counts
                    for i in range(len(path)-1):
                        self.use_counts[(path[i], path[i+1])] += 1
                        self.use_counts[(path[i+1], path[i])] += 1
