from __future__ import annotations
from typing import List

from app.engine.objects.overworld import OverworldEntityObject, OverworldNodeObject, RoadObject
from .overworld_manager import OverworldManager
from app.engine.overworld.overworld_movement_manager import \
    OverworldMovementManager
from app.utilities.typing import NID


class OverworldMove():
    """
    A user-issued move to a party on the overworld between two nodes.
    """
    def __init__(self, entity: OverworldEntityObject | NID, target_node: OverworldNodeObject | NID, overworld: OverworldManager, event=False, follow=True, speed_adj=1, remove_last=False):
        if isinstance(entity, OverworldEntityObject):
            entity = entity.nid
        if isinstance(target_node, NID):
            target_node = overworld.nodes[target_node]
        self.entity = overworld.entities[entity]
        self.old_node = overworld.nodes[self.entity.on_node]
        self.new_node = target_node
        self.speed_adj = speed_adj

        roads: List[RoadObject] = overworld.shortest_path(self.old_node, self.new_node)
        if remove_last:
            roads.pop()
        self.path = [self.old_node.position]

        for road in roads:
            # fetch the actual coordinate paths from the roads and orient them properly
            tpath = road.prefab
            if tpath[0] == self.path[-1]:
                self.path = self.path + tpath
            else:
                self.path = self.path + tpath[::-1]
        # finally, since movement is queued LIFO, we reverse the path
        # so the first step is last in the list
        self.path.reverse()
        self.event = event
        self.follow = follow

    def queue(self, movement_manager: OverworldMovementManager):
        if self.path:
            movement_manager.begin_move(self.entity, self.path, self.event, self.follow, self.speed_adj)

    def execute(self):
        self.entity.on_node = self.new_node.nid

    def reverse(self):
        self.entity.on_node = self.old_node.nid
