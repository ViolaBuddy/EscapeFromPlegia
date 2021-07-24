from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

if TYPE_CHECKING:
    from .overworld_cursor import OverworldCursor

from app.engine.objects.overworld import (OverworldEntityObject,
                                          OverworldNodeObject, OverworldObject,
                                          RoadObject)
from app.engine.objects.tilemap import TileMapObject
from app.utilities.typing import NID, Point
from app.utilities.algorithms.ltgraph import LTGraph

class OverworldManager():
    """A wrapper class that contains various functionality for manipulating
    and accessing the overworld data.
    """
    def __init__(self, overworld: OverworldObject, cursor: OverworldCursor = None):
        self._overworld = overworld
        if cursor:
            self.cursor = cursor
            self.cursor.set_overworld_manager(self)
        else:
            self.cursor = None
        # generate useful structs
        self.nodes: Dict[NID, OverworldNodeObject] = {}
        self.roads: Dict[NID, RoadObject] = {}

        self.overworld_full_graph: LTGraph[NID, OverworldNodeObject, RoadObject]  = None
        self.overworld_explored_graph: LTGraph[NID, OverworldNodeObject, RoadObject] = None

        self._initialize_objects()
        self._initialize_graphs()

    @property
    def entities(self) -> Dict[NID, OverworldEntityObject]:
        return self._overworld.overworld_entities

    @property
    def revealed_nodes(self) -> List[OverworldNodeObject]:
        return [self.nodes[nid] for nid in self._overworld.enabled_nodes]

    @property
    def revealed_node_nids(self) -> List[NID]:
        return self._overworld.enabled_nodes

    def enable_node(self, node: OverworldNodeObject | NID):
        if isinstance(node, OverworldNodeObject):
            node = node.nid
        self._overworld.enabled_nodes.add(node)
        self.regenerate_explored_graph()

    @property
    def revealed_roads(self) -> List[RoadObject]:
        return [self.roads[nid] for nid in self._overworld.enabled_roads]

    def enable_road(self, road: RoadObject | NID):
        if isinstance(road, RoadObject):
            road = road.nid
        self._overworld.enabled_roads.add(road)
        self.regenerate_explored_graph()

    @property
    def tilemap(self) -> TileMapObject:
        return self._overworld.tilemap

    @property
    def selected_entity(self) -> OverworldEntityObject:
        if not self._overworld.selected_party_nid:
            # select the first player party on the map
            for entity in self._overworld.overworld_entities.values():
                if entity.team == 'player':
                    if entity.on_node is not None and entity.position:
                        self._overworld.selected_party_nid = entity.nid
                        break
        return self.entities[self._overworld.selected_party_nid]

    def select_entity(self, party: OverworldEntityObject | NID):
        if isinstance(party, OverworldEntityObject):
            party = party.nid
        self._overworld.selected_party_nid = party

    def set_node_property(self, node: OverworldNodeObject | NID, prop: str, unique=False):
        """Add property to a node. If unique is True, it will remove this property
        from all other nodes.

        Args:
            node_nid (OverworldNodeObject | NID): node
            property (str): arbitrary property to add
            unique (bool, optional): whether only one node can have this property at a time. Defaults to False.
        """
        if isinstance(node, OverworldNodeObject):
            node = node.nid
        if unique:
            for nid, nprops in self._overworld.node_properties.items():
                if nid != node and prop in nprops:
                    nprops.remove(prop)
        if node in self._overworld.node_properties:
            self._overworld.node_properties[node].add(prop)
        else:
            self._overworld.node_properties[node] = set([prop])

    def remove_node_property(self, node: OverworldNodeObject | NID, prop:str):
        """Remove property from node.
        """

        if isinstance(node, OverworldNodeObject):
            node = node.nid
        try:
            self._overworld.node_properties[node].remove(prop)
        except:
            # node doesn't exist, prop doesn't exist, who cares?
            pass

    def shortest_path(self, n1: OverworldNodeObject | NID,
                      n2: OverworldNodeObject | NID, neighbor_priority=True,
                      force=False) -> List[RoadObject]:
        """Returns a list of roads indicating the shortest paths between two nodes.

        If neighbor_priority is true (true by default), then it will always return the direct path between two neighboring nodes.
        This is because in certain use cases - if the player selects a neighboring node to go to - it should be
        assumed that direct path control is preferable to optimization.

        Args:
            n1 (OverworldNodeObject | NID): the start node which the path starts from.
            n2 (OverworldNodeObject | NID): the end node which the path goes to.
            neighbor_priority (bool): Optional. Indicates whether or not to override shortest path in favor
                of direct path in the case of neighboring n1 and n2. Default true
            force (bool): Optional. Indicates whether to use the full overworld graph, or just the graph of
                what's visible. Defaults to False, i.e., use only the visible graph.

        Returns:
            List[RoadObject]: list of road objects that constitutes a path between n1
                and n2. Can be a list of length 1, if the two nodes are neighbors, or 0,
                if no such path exists.

        """
        if not self.any_path(n1, n2, force):
            return []

        if isinstance(n1, OverworldNodeObject):
            n1 = n1.nid
        if isinstance(n2, OverworldNodeObject):
            n2 = n2.nid
        if force:
            graph = self.overworld_full_graph
        else:
            graph = self.overworld_explored_graph

        if neighbor_priority:
            if n1 in self.connected_nodes(n2, force):
                return [self.get_road(n1, n2, force)]
        node_path: List[NID] = graph.shortest_path(n1, n2)
        return [graph[node_path[i]][node_path[i+1]].data for i in range(len(node_path) - 1)]

    def entity_at(self, pos: Point | OverworldNodeObject) -> Optional[OverworldEntityObject]:
        if isinstance(pos, OverworldNodeObject):
            pos = pos.position
        for entity in self._overworld.overworld_entities.values():
            if entity.position == pos:
                return entity
        return None

    def node_props(self, node: OverworldNodeObject | NID) -> Set[str]:
        if isinstance(node, OverworldNodeObject):
            node = node.nid
        return self._overworld.node_properties.get(node, set())

    def node_at(self, pos: Point, force=False) -> OverworldNodeObject:
        for node in self.nodes.values():
            if node.position == pos:
                if force:
                    return node
                else:
                    if node.nid in self._overworld.enabled_nodes:
                        return node
                    else:
                        break
        return None

    def node_by_level(self, level_nid: NID) -> OverworldNodeObject:
        for node in self.nodes.values():
            if node.prefab.level == level_nid:
                return node
        return None

    def selected_party_node(self) -> OverworldNodeObject:
        return self.nodes[self.selected_entity.on_node]

    def any_path(self, n1: OverworldNodeObject | NID,
                 n2: OverworldNodeObject | NID, force: bool = False) -> bool:
        """If there exists a valid method of traveling between the two nodes on the world map,
        this will return true, else false.

        Args:
            n1 (OverworldNodeObject | NID): One node of interest
            n2 (OverworldNodeObject | NID): The other node of interest
            force (bool): Optional. Indicates whether to use the full overworld graph, or just the graph of
                what's visible. Defaults to False, i.e., use only the visible graph.

        Returns:
            bool: Whether or not a path exists between the two nodes
        """
        if isinstance(n1, OverworldNodeObject):
            n1 = n1.nid
        if isinstance(n2, OverworldNodeObject):
            n2 = n2.nid

        if force:
            graph = self.overworld_full_graph
        else:
            graph = self.overworld_explored_graph

        try:
            return graph.has_path(n1, n2)
        except:
            return False

    def get_road(self, n1: OverworldNodeObject | NID,
                 n2: OverworldNodeObject | NID, force: bool = False) -> Optional[RoadObject]:
        """gets the road between two nodes. If no such road exists, will return None

        Args:
            n1 (OverworldNodeObject | NID): first node
            n2 (OverworldNodeObject | NID): second node
            force (bool): Optional. Indicates whether to use the full overworld graph, or just the graph of
                what's visible. Defaults to False, i.e., use only the visible graph.

        Returns:
            Optional[RoadObject]: road object between the two
        """
        if isinstance(n1, OverworldNodeObject):
            n1 = n1.nid
        if isinstance(n2, OverworldNodeObject):
            n2 = n2.nid
        if force:
            graph = self.overworld_full_graph
        else:
            graph = self.overworld_explored_graph
        try:
            return graph[n1][n2].data
        except Exception:
            # node probably doesn't exist in graph
            return None

    def connected_nodes(self, n1: OverworldNodeObject | NID, force=False) -> List[NID]:
        if isinstance(n1, OverworldNodeObject):
            n1 = n1.nid
        if force:
            graph = self.overworld_full_graph
        else:
            graph = self.overworld_explored_graph
        try:
            neighbor_nids: List[NID] = list(graph.adj[n1])
            return neighbor_nids
        except:
            # something went wrong, node doesn't exist?
            return []

    def _initialize_objects(self):
        for nid, node in self._overworld.prefab.overworld_nodes.items():
            self.nodes[nid] = OverworldNodeObject.from_prefab(node)
        for rid, road in self._overworld.prefab.map_paths.items():
            self.roads[rid] = RoadObject.from_prefab(road, rid)

    def _initialize_graphs(self):
        self.overworld_full_graph = LTGraph()
        for node in self.nodes.values():
            self.overworld_full_graph.add_vertex(node.nid, node)
        for road in self.roads.values():
            path = road.prefab
            start_node = self.node_at(path[0], True)
            end_node = self.node_at(path[-1], True)
            if start_node.nid and end_node.nid:
                self.overworld_full_graph.add_edge(start_node.nid, end_node.nid, data=road, weight=road.tile_length)
        self.regenerate_explored_graph()

    def regenerate_explored_graph(self):
        """Forcibly regenerates the graph representation of the visible overworld graph.
        """
        self.overworld_explored_graph = LTGraph()
        for vis_node_nid in self._overworld.enabled_nodes:
            self.overworld_explored_graph.add_vertex(vis_node_nid, self.nodes[vis_node_nid])
        for vis_road_nid in self._overworld.enabled_roads:
            road = self.roads[vis_road_nid]
            path = road.prefab
            start_node = self.node_at(path[0])
            end_node = self.node_at(path[-1])
            if start_node and end_node:
                self.overworld_explored_graph.add_edge(start_node.nid, end_node.nid, data=road, weight=road.tile_length)

    def map_size(self) -> Tuple[int, int]:
        return (self._overworld.tilemap.width, self._overworld.tilemap.height)

    def map_bounds(self) -> Tuple[int, int, int, int]:
        """Get boundary of map. Returns as (left, top, right, bottom).

        Returns:
            Tuple[int, int, int, int]: Map boundary limits.
        """
        return (self._overworld.prefab.border_tile_width,
                self._overworld.prefab.border_tile_width,
                self._overworld.tilemap.width - self._overworld.prefab.border_tile_width - 1,
                self._overworld.tilemap.height - self._overworld.prefab.border_tile_width - 1)
