import math

from app.data.constants import WINWIDTH, WINHEIGHT
from app.data.database import DB
from app.engine.sprites import SPRITES

from app import utilities

from app.engine import config as cf
from app.engine import engine, image_mods
from app.engine.game_state import game

import logging
logger = logging.getLogger(__name__)

class PhaseController():
    def __init__(self):
        self.phase_in = []
        for team in DB.teams:
            self.phase_in.append(PhaseIn(team))

        self.current = 3 if game.turncount == 0 else 0
        self.previous = 0

    def get_current(self):
        return DB.teams[self.current]

    def get_previous(self):
        return DB.teams[self.previous]

    def _next(self):
        self.current = (self.current + 1) % len(DB.teams)

    def next(self):
        self.previous = self.current
        # If there are units
        if game.level.units:
            self._next()
            # Skip over any phases that no one is part of
            # but never skip player phase
            while not any(self.get_current() == unit.team for unit in game.level.units) and self.current != 0:
                self._next()
        else:   
            self.current = 0

    def slide_in(self):
        self.phase_in[self.current].begin()

    def update(self):
        return self.phase_in[self.current].update()

    def draw(self, surf):
        surf = self.phase_in[self.current].draw(surf)
        return surf

class PhaseIn():
    t_begin = 128
    t_main = 1000
    t_end = 240
    t_display = t_begin + t_main + t_end
    black_squares = SPRITES.get('phase_transition')
    transition_space = engine.create_surface((WINWIDTH, WINHEIGHT//2 - 16), transparent=True)

    def __init__(self, name):
        self.name = name
        self.sprite_name = 'turnbanner_' + name
        self.image = SPRITES.get(self.sprite_name)

        self.starting_time = None

    def begin(self):
        self.starting_time = engine.get_time()
        if self.name == 'player':
            if cf.SETTINGS['autocursor']:
                game.cursor.autocursor()
            else:
                game.cursor.set_position(game.memory['previous_cursor_position'])

    def update(self):
        return engine.get_time() - self.starting_time >= self.t_display

    def draw(self, surf):
        current_time = engine.get_time()
        time_passed = min(current_time - self.starting_time, self.t_display)
        
        max_opacity = 118

        # Blit the banner
        # Determine position
        if time_passed < self.t_begin:
            diff = time_passed / self.t_begin
            offset_x = self.t_begin * (1 - diff)
            trans = (1 - diff) ** 2
        elif time_passed < self.t_begin + self.t_main:
            offset_x = 0
            trans = 0
        else:
            diff = (time_passed - self.t_begin - self.t_main) / self.t_end
            offset_x = -self.t_end * diff
            trans = diff**2

        image = image_mods.make_translucent(self.image, trans)
        surf.blit(image, (offset_x + WINWIDTH//2 - self.image.get_width()//2, WINHEIGHT//2 - self.image.get_height()//2))

        transition_space1 = engine.copy_surface(self.transition_space)
        transition_space2 = engine.copy_surface(self.transition_space)

        # Black square transition
        t_half = self.t_display//2
        if time_passed < t_half:
            diff = time_passed / t_half
            height = 64 * diff
            alpha = int(max_opacity * math.sqrt(time_passed / t_half))
            t = int(2 + diff * 16)  # Starts a little ways along at the beginning
        else:
            diff = -(t_half - time_passed) / t_half
            height = 64 * (1 - diff)
            alpha = int(max_opacity - max_opacity * ((time_passed - t_half)/t_half) ** 2)
            t = int(diff * 16)

        for x in range(0, WINWIDTH, 16):
            for y in range(0, 64, 16):
                i, j = x//16, y//16
                k1 = int(t * 1.5 - (i - j%2)/2 + j/2 - 4)
                k2 = int(t * 1.5 - (i - j%2)/2 + j/2 - 1)
                if time_passed < t_half:
                    frame1 = utilities.clamp(8 - abs(max(k1, 8) - 8), 0, 8)
                    frame2 = utilities.clamp(8 - abs(max(k2, 8) - 8), 0, 8)
                else:
                    frame1 = utilities.clamp(k1, 0, 8)
                    frame2 = utilities.clamp(k2, 0, 8)
                square_surf = engine.subsurface(self.black_squares, (frame1*16, 0, 16, 16)).copy()
                transition_space1.blit(square_surf, (x, y))
                square_surf = engine.subsurface(self.black_squares, (frame2*16, 0, 16, 16)).copy()
                transition_space2.blit(square_surf, (x, y))

        transition_space1 = engine.subsurface(transition_space1, (0, 0, WINWIDTH, height))
        transition_space2 = engine.subsurface(transition_space2, (0, self.transition_space.get_height() - height, WINWIDTH, height))

        engine.fill(transition_space1, (255, 255, 255, alpha), None, engine.BLEND_RGBA_MULT)
        engine.fill(transition_space2, (255, 255, 255, alpha), None, engine.BLEND_RGBA_MULT)

        surf.blit(transition_space1, (0, 0))
        surf.blit(transition_space2, (0, WINHEIGHT - transition_space2.get_height()))

        return surf