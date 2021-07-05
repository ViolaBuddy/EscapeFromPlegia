from app.data.item_components import ItemComponent
from app.data.components import Type

from app.utilities import utils
from app.engine import target_system, skill_system
from app.engine.game_state import game 

class MementoEnemyCleaveAOE(ItemComponent):
    nid = 'memento_enemy_cleave_aoe'
    desc = "Gives Enemy Memento Cleave AOE"
    tag = 'memento'

    def splash(self, unit, item, position) -> tuple:
        pos = unit.position
        x_diff = position[0] - pos[0]
        y_diff = position[1] - pos[1]
        if x_diff in (1, -1):
            splash_positions = {(position[0], position[1] - 1), (position[0], position[1] + 1)}
        elif y_diff in (1, -1):
            splash_positions = {(position[0] - 1, position[1]), (position[0] + 1, position[1])}
        else:
            splash_positions = set()
        
        splash_positions = {pos for pos in splash_positions if game.tilemap.check_bounds(pos)}
        splash = [game.board.get_unit(pos) for pos in splash_positions]
        splash = [s.position for s in splash if s and skill_system.check_enemy(unit, s)]
        main_target = position if game.board.get_unit(position) else None
        return main_target, splash

    def splash_positions(self, unit, item, position) -> set:
        pos = unit.position
        x_diff = position[0] - pos[0]
        y_diff = position[1] - pos[1]
        if x_diff in (1, -1):
            splash_positions = {(position[0], position[1] - 1), (position[0], position[1] + 1)}
        elif y_diff in (1, -1):
            splash_positions = {(position[0] - 1, position[1]), (position[0] + 1, position[1])}
        else:
            splash_positions = set()
        
        splash_positions = {pos for pos in splash_positions if game.tilemap.check_bounds(pos)}
        # Doesn't highlight allies positions
        splash = {pos for pos in splash_positions if not game.board.get_unit(pos) or skill_system.check_enemy(unit, game.board.get_unit(pos))}
        return splash

class MementoEnemyPierceAOE(ItemComponent):
    nid = 'memento_enemy_pierce_aoe'
    desc = "Gives Enemy Memento Pierce AOE"
    tag = 'memento'

    def splash(self, unit, item, position) -> tuple:
        pos = unit.position
        x_diff = position[0] - pos[0]
        y_diff = position[1] - pos[1]
        x_diff *= 2
        y_diff *= 2
        splash_positions = {(position[0] + x_diff, position[1] + y_diff)}
        
        splash_positions = {pos for pos in splash_positions if game.tilemap.check_bounds(pos)}
        splash = [game.board.get_unit(pos) for pos in splash_positions]
        splash = [s.position for s in splash if s and skill_system.check_enemy(unit, s)]
        main_target = position if game.board.get_unit(position) else None
        return main_target, splash

    def splash_positions(self, unit, item, position) -> set:
        pos = unit.position
        x_diff = position[0] - pos[0]
        y_diff = position[1] - pos[1]
        x_diff *= 2
        y_diff *= 2
        splash_positions = {(position[0] + x_diff, position[1] + y_diff)}

        splash_positions = {pos for pos in splash_positions if game.tilemap.check_bounds(pos)}
        # Doesn't highlight allies positions
        splash = {pos for pos in splash_positions if not game.board.get_unit(pos) or skill_system.check_enemy(unit, game.board.get_unit(pos))}
        return splash