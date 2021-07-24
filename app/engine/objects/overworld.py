from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

from app.constants import TILEHEIGHT, TILEWIDTH
from app.data.database import DB
from app.engine.unit_sprite import MapSprite
from app.utilities.utils import magnitude, tuple_sub

if TYPE_CHECKING:
    from app.data.overworld import OverworldPrefab
    from app.data.units import UnitPrefab
    from app.data.overworld_node import OverworldNodePrefab
    from app.engine.game_state import GameState
    from app.engine.objects.party import PartyObject
    from app.engine.objects.unit import UnitObject

from app.engine.objects.tilemap import TileMapObject
from app.engine.overworld.overworld_map_sprites import (OverworldNodeSprite,
                                                        OverworldRoadSprite,
                                                        OverworldUnitSprite)
from app.engine.unit_sound import UnitSound
from app.resources.sounds import Song
from app.utilities.typing import NID, Point

import logging

class OverworldNodeProperty():
    IS_NEXT_LEVEL = "IS_NEXT_LEVEL"

class OverworldNodeObject():
    def __init__(self):
        self.prefab: OverworldNodePrefab = None # prefab info
        self.sprite: OverworldNodeSprite = None # sprite

    @property
    def position(self) -> Point:
        return self.prefab.pos

    @property
    def nid(self) -> NID:
        return self.prefab.nid

    @classmethod
    def from_prefab(cls, prefab: OverworldNodePrefab):
        node = cls()
        node.prefab = prefab
        node.sprite = OverworldNodeSprite(prefab)
        return node

class OverworldEntityObject():
    def __init__(self):
        # an OverworldEntityObject is just a wrapper around a unit that represents a party on the overworld.
        self.on_node: NID = None                 # NID of node on which the unit is standing
        self.prefab: PartyObject = None          # party object which this entity represents
        self.team: NID = 'player'                # team of party. @TODO: Implement non-player entities.
        self.sprite: OverworldUnitSprite = None    # sprite for the entity

        # private data
        self.unit: UnitObject | UnitPrefab = None   # Unit data for this entity
        self._sound: UnitSound = None               # sound associated
        self.temporary_position: Point = None       # NOTE: because the 'official' position of the entity (see below)
                                                    # is always on top of a node, this temporary position attribute
                                                    # is chiefly used in service of animation - when walking along
                                                    # roads, etc.
        self._display_position: Point = None        # ditto as above

    @classmethod
    def from_prefab(cls, initial_node: NID, prefab: PartyObject, unit_registry: Dict[NID, UnitObject]):
        entity = cls()
        entity.prefab = prefab
        entity.on_node = initial_node

        # create unit
        if prefab.leader_nid in unit_registry:
            entity.unit = unit_registry.get(prefab.leader_nid)
        else:
            entity.unit = DB.units.get(prefab.leader_nid)
        if entity.unit:
            entity.sprite = OverworldUnitSprite(entity.unit, entity)
        else:
            logging.error("OverworldEntityObject cannot find unit %s", prefab.leader_nid)
            entity.sprite = None
        return entity

    def save(self):
        s_dict = {'prefab_nid': self.prefab.nid,
                  'on_node_nid': self.on_node,
                  'team': self.team}
        return s_dict

    @classmethod
    def restore(cls, s_dict, game: GameState) -> OverworldEntityObject:
        prefab_nid = s_dict['prefab_nid']
        party_prefab = game.parties.get(prefab_nid)
        on_node_nid = s_dict['on_node_nid']
        entity_object = OverworldEntityObject.from_prefab(on_node_nid, party_prefab, game.unit_registry)
        entity_object.team = s_dict['team']
        return entity_object

    @property
    def position(self) -> Point:
        if self.on_node:
            for overworld in DB.overworlds.values():
                node = overworld.overworld_nodes.get(self.on_node, None)
                if node is not None:
                    return node.pos
        return None

    @property
    def display_position(self) -> Point:
        if self._display_position:
            return self._display_position
        elif self.temporary_position:
            return self.temporary_position
        else:
            return self.position

    @display_position.setter
    def display_position(self, pos: Point):
        self._display_position = pos

    @property
    def nid(self) -> NID:
        return self.prefab.nid

    @property
    def sound(self):
        if not self._sound:
            from app.engine import unit_sound
            self._sound = unit_sound.UnitSound(self.unit)
        return self._sound

class RoadObject():
    def __init__(self):
        self.nid: NID = None
        self.prefab: List[Point] = None # "prefab", lol, really this is just the list of points
        self.sprite: OverworldRoadSprite = None # sprite

    def get_segments(self, road: List[Point]) -> List[Tuple[Point, Point]]:
        """turns road ( a list of points in sequence) into a list of road
        segments ( a list of two endpoints describing a line) for ease of use.

        Returns:
            List[Tuple[Point, Point]]: a list of road segments (two points) in sequence.
        """
        segments = []
        for i in range(len(road) - 1):
            segment = (road[i], road[i+1])
            segments.append(segment)
        return segments

    def road_in_pixel_coords(self) -> List[Point]:
        """Returns the same list of points that make up the road,
        but converted to pixel coordinates instead of tile coordinates
        for ease of drawing

        Returns:
            List[Point]: list of road point coordinates in pixels
        """
        pix_list = []
        for point in self.prefab:
            pix_x = point[0] * TILEWIDTH + TILEWIDTH / 2
            pix_y = point[1] * TILEHEIGHT + TILEHEIGHT / 2
            pix_list.append((pix_x, pix_y))
        return pix_list

    @property
    def pixel_length(self) -> float:
        """Property, returns total pixel length of the road.
        Useful for transitions.

        Returns:
            float: the pixel length of the road
        """
        length = 0
        pixel_road = self.road_in_pixel_coords()
        for segment in self.get_segments(pixel_road):
            length += (segment[1] - segment[0]).length()
        return length

    @property
    def tile_length(self) -> float:
        """Returns the "length" of the road in tiles.

        Returns:
            float: road length in tiles
        """
        length = 0
        for segment in self.get_segments(self.prefab):
            length += magnitude(tuple_sub(segment[1], segment[0]))
        return length

    @classmethod
    def from_prefab(cls, prefab: List[Point], nid: NID):
        # as above, this isn't actually a prefab, but follows the convention for ease of use
        road = cls()
        road.nid = nid
        road.prefab = [tuple(point) for point in prefab]
        road.sprite = OverworldRoadSprite(road)
        return road

# Main Overworld Object used by engine
class OverworldObject():
    def __init__(self):
        self.prefab: OverworldPrefab = None # the prefab information itself
        self.tilemap: TileMapObject = None  # tilemap
        self.enabled_nodes: Set[NID] = set() # set of ids of nodes that are accessible right now
        self.enabled_roads: Set[NID] = set() # set of ids of roads that are accessible right now
        self.overworld_entities: Dict[NID, OverworldEntityObject] = {} # list of entities on the map (e.g. player party, wandering encounters)

        self.selected_party_nid: NID = None

        self.node_properties: Dict[NID, Set[str]] = {}                     # allows us to assign arbitrary properties to nodes. Currently, only one property is supported:
                                                                            # "is_objective", indicating whether or not this node is the next objective (and whether or not to fly the little flag
                                                                            # on top of it) Could be useful for other properties in the future.
        # not saved since it's just a property
        self._music: Song = None # filename of overworld music file

    @property
    def nid(self) -> NID:
        return self.prefab.nid

    @property
    def name(self) -> str:
        return self.prefab.name

    @property
    def music(self) -> Song:
        if not self._music:
            self._music = self.prefab.get_music_resource()
        return self._music

    @classmethod
    def from_prefab(cls, prefab: OverworldPrefab, party_registry: Dict[NID, PartyObject], unit_registry: Dict[NID, UnitObject]):
        overworld = cls()
        tilemap_prefab = prefab.get_tilemap_resource()
        if tilemap_prefab:
            overworld.tilemap = TileMapObject.from_prefab(tilemap_prefab)
        overworld.prefab = prefab
        for pnid, party in party_registry.items():
            overworld_party = OverworldEntityObject.from_prefab(None, party, unit_registry)
            overworld.overworld_entities[pnid] = overworld_party
        return overworld

    def save(self):
        s_dict = {'tilemap': self.tilemap.save(),
                  'enabled_nodes': list(self.enabled_nodes),
                  'enabled_roads': list(self.enabled_roads),
                  'prefab_nid': self.nid,
                  'overworld_entities': [entity.save() for entity in self.overworld_entities.values()],
                  'selected_party_nid': self.selected_party_nid,
                  'node_properties': self.node_properties
                  }
        return s_dict

    @classmethod
    def restore(cls, s_dict: Dict, game: GameState) -> OverworldObject:
        overworld = OverworldObject.from_prefab(DB.overworlds.get(s_dict['prefab_nid']), game.parties, game.unit_registry)
        overworld.tilemap = TileMapObject.restore(s_dict['tilemap'])
        overworld.enabled_nodes = set(s_dict['enabled_nodes'])
        overworld.enabled_roads = set(s_dict['enabled_roads'])
        overworld.node_properties = s_dict.get('node_properties', {})

        for entity in s_dict['overworld_entities']:
            entity_obj = OverworldEntityObject.restore(entity, game)
            overworld.overworld_entities[entity_obj.nid] = entity_obj

        overworld.selected_party_nid = s_dict['selected_party_nid']
        return overworld
