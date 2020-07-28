from app import utilities

from app.engine.item_system.item_component import ItemComponent, Type

from app.engine import status_system, targets
from app.engine.item_system import item_system
from app.engine.game_state import game 

class Spell(ItemComponent):
    nid = 'spell'
    desc = "Item will be treated as a spell (cannot counterattack or double)"

    def is_spell(self, unit, item):
        return True

    def is_weapon(self, unit, item):
        return False

    def equippable(self, unit, item):
        return False

    def can_be_countered(self, unit, item):
        return False

    def can_counter(self, unit, item):
        return False

class Weapon(ItemComponent):
    nid = 'weapon'
    desc = "Item will be treated as a normal weapon (can double, counterattack, be equipped, etc.)" 

    def is_weapon(self, unit, item):
        return True

    def is_spell(self, unit, item):
        return False

    def equippable(self, unit, item):
        return True

    def can_be_countered(self, unit, item):
        return True

    def can_counter(self, unit, item):
        return True

class SiegeWeapon(ItemComponent):
    nid = 'siege_weapon'
    desc = "Item will be treated as a siege weapon (can not double or counterattack, but can still be equipped)"

    def is_weapon(self, unit, item):
        return True

    def is_spell(self, unit, item):
        return False

    def equippable(self, unit, item):
        return True

    def can_be_countered(self, unit, item):
        return False

    def can_counter(self, unit, item):
        return False

class TargetsAnything(ItemComponent):
    nid = 'target_tile'
    desc = "Item targets any tile"

    def valid_targets(self, unit, item) -> set:
        rng = item_system.get_range(unit, item)
        return targets.find_manhattan_spheres(rng, *unit.position)

class TargetsUnits(ItemComponent):
    nid = 'target_unit'
    desc = "Item targets any unit"

    def valid_targets(self, unit, item) -> set:
        return {other.position for other in game.level.units if other.position and 
                utilities.calculate_distance(unit.position, other.position) in item_system.get_range(unit, item)}

class TargetsEnemies(ItemComponent):
    nid = 'target_enemy'
    desc = "Item targets any enemy"

    def valid_targets(self, unit, item) -> set:
        return {other.position for other in game.level.units if other.position and 
                status_system.check_enemy(unit, other) and 
                utilities.calculate_distance(unit.position, other.position) in item_system.get_range(unit, item)}

class TargetsAllies(ItemComponent):
    nid = 'target_ally'
    desc = "Item targets any ally"

    def valid_targets(self, unit, item) -> set:
        return {other.position for other in game.level.units if other.position and 
                status_system.check_ally(unit, other) and 
                utilities.calculate_distance(unit.position, other.position) in item_system.get_range(unit, item)}

class MinimumRange(ItemComponent):
    nid = 'min_range'
    desc = "Set the minimum_range of the item to an integer"

    expose = Type.Int

    def minimum_range(self, unit, item) -> int:
        return self.value

class MaximumRange(ItemComponent):
    nid = 'max_range'
    desc = "Set the maximum_range of the item to an integer"
    expose = Type.Int

    def maximum_range(self, unit, item) -> int:
        return self.value

class Usable(ItemComponent):
    nid = 'usable'
    desc = "Item is usable"

    def can_use(self, unit, item):
        return True

class Value(ItemComponent):
    nid = 'value'
    desc = "Item has a value and can be bought and sold. Items sell for half their value."
    expose = Type.Int

    def buy_price(self, unit, item):
        if item.uses:
            frac = item.data['uses'] / item.uses.starting_uses
            return self.value * frac
        return self.value

    def sell_price(self, unit, item):
        if item.uses:
            frac = item.data['uses'] / item.uses.starting_uses
            return self.value * frac // 2
        return self.value // 2
