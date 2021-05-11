import os
from app.utilities.data import Prefab
from app.resources.base_catalog import ManifestCatalog

class Palette(Prefab):
    def __init__(self, nid):
        self.nid = nid
        # Mapping of color indices to true colors
        # Color indices are generally (0, 1) -> (240, 160, 240), etc.
        self.colors = {}

    def save(self):
        return (self.nid, self.colors.copy())

    @classmethod
    def restore(cls, s):
        self = cls(s[0])
        self.colors = s[1].copy()
        return self

class PaletteCatalog(ManifestCatalog):
    manifest = 'palettes.json'
    title = 'palettes'

    def load(self, loc):
        true_loc = os.path.join(loc, self.manifest)
        if not os.path.exists(true_loc):
            return
        palette_dict = self.read_manifest(true_loc)
        for s_dict in palette_dict:
            new_palette = Palette.restore(s_dict)
            self.append(new_palette)

    def save(self, loc):
        # No need to finagle with full paths
        # Because Palettes don't have any connection to any actual file.
        import time
        start = time.time_ns()/1e6
        self.dump(loc)
        end = time.time_ns()/1e6
        print("Time Taken: %s ms" % (end - start))
