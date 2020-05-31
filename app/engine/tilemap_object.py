from app.data.constants import TILEWIDTH, TILEHEIGHT
from app.data.data import Data, Prefab

from app.data.resources import RESOURCES

from app.engine import engine

class LayerObject():
    def __init__(self, nid: str, parent):
        self.nid: str = nid
        self.parent = parent
        self.visible = True
        self.terrain = {}
        self.image = None

    def set_image(self, image):
        self.image = image

    def serialize(self):
        s_dict = {}
        s_dict['nid'] = self.nid
        s_dict['visible'] = self.visible
        # s_dict['terrain'] = {}
        # for coord, terrain_nid in self.terrain.items():
        #     str_coord = "%d,%d" % (coord[0], coord[1])
        #     s_dict['terrain'][str_coord] = terrain_nid
        return s_dict

    # Not even needed -- handled in TileMapObjects deserialize function
    # @classmethod
    # def deserialize(cls, s_dict, parent):
    #     self = cls(s_dict['nid'], parent)
    #     self.visible = bool(s_dict['visible'])
    #     # for str_coord, terrain_nid in s_dict['terrain'].items():
    #     #     coord = tuple(int(_) for _ in str_coord.split(','))
    #     #     self.terrain[coord] = terrain_nid
    #     return self

class TileMapObject(Prefab):
    @classmethod
    def from_prefab(cls, prefab):
        self = cls()
        self.nid = prefab.nid
        self.width = prefab.width
        self.height = prefab.height
        self.layers = Data()
        self.full_image = None

        # Stitch together image layers
        for layer in prefab.layers:
            new_layer = LayerObject(layer.nid, self)
            # Terrain
            for coord, terrain_nid in layer.terrain_grid.items():
                new_layer.terrain[coord] = terrain_nid
            # Image
            image = engine.create_surface((self.width * TILEWIDTH, self.height * TILEHEIGHT), transparent=True)
            for coord, tile_sprite in layer.sprite_grid.items():
                tileset = RESOURCES.tilesets.get(tile_sprite.tileset_nid)
                if not tileset.image:
                    tileset.image = engine.image_load(tileset.full_path)
                rect = (tile_sprite.tileset_position[0] * TILEWIDTH, 
                        tile_sprite.tileset_position[1] * TILEHEIGHT,
                        TILEWIDTH, TILEHEIGHT)
                sub_image = engine.subsurface(tileset.image, rect)
                image.blit(sub_image, (coord[0] * TILEWIDTH, coord[1] * TILEHEIGHT))
            new_layer.image = image
            self.layers.append(new_layer)

        # Base layer should be visible, rest invisible
        for layer in self.layers:
            layer.visible = False
        self.layers.get('base').visible = True

        return self

    def get_terrain(self, pos):
        for layer in reversed(self.layers):
            if layer.visible and pos in layer.terrain:
                return layer.terrain[pos]
        return '0'

    def get_full_image(self):
        if not self.full_image:
            image = engine.create_surface((self.width * TILEWIDTH, self.height * TILEHEIGHT), transparent=True)
            for layer in self.layers:
                if layer.visible:
                    image.blit(layer.image, (0, 0))
            self.full_image = image
        return self.full_image

    def reset(self):
        self.full_image = None

    def serialize(self):
        s_dict = {}
        s_dict['nid'] = self.nid
        s_dict['layers'] = [layer.serialize() for layer in self.layers]
        return s_dict

    @classmethod
    def deserialize(cls, s_dict):
        print(s_dict)
        prefab = RESOURCES.tilemaps.get(s_dict['nid'])
        print(prefab)
        self = cls.from_prefab(prefab)
        self.deserialize_layers(s_dict['layers'])
        return self

    def deserialize_layers(self, layer_list):
        for layer_dict in layer_list:
            nid = layer_dict['nid']
            visible = layer_dict['visible']
            self.layers.get(nid).visible = visible
