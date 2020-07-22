import functools
from enum import IntEnum

class Type(IntEnum):
    Int = 1
    Float = 2
    String = 3
    WeaponType = 4
    WeaponRank = 5
    Unit = 6
    Class = 7
    Tag = 8
    Color = 9
    Status = 10
    Set = 100
    Dict = 101

class ItemComponent():
    nid: str = None
    desc: str = None
    author: str = 'rainlash'

    @property
    def name(self):
        name = self.__class__.__name__
        return functools.reduce(lambda a, b: a + ((b.upper() == b and (a and a[-1].upper() != a[-1])) and (' ' + b) or b), name, '')

    def defines(self, function_name):
        return hasattr(self, function_name)

# Only for exclusive behaviours
class Defaults():
    @staticmethod
    def minimum_range(unit, item) -> int:
        return 0

    @staticmethod
    def maximum_range(unit, item) -> int:
        return 0

    @staticmethod
    def splash(unit, item, position) -> tuple:
        """
        Returns main target and splash
        """
        from app.engine.game_state import game
        return game.grid.get_unit(position), []

    @staticmethod
    def damage(unit, item) -> int:
        return None

    @staticmethod
    def splash_multiplier(unit, item) -> int:
        return 1

    @staticmethod
    def damage_formula(unit, item) -> str:
        return 'DAMAGE'

default_behaviours = ('is_weapon', 'is_spell', 'equippable', 'can_use', 'locked', 'can_counter', 'can_be_countered')
# These behaviours default to false

for behaviour in default_behaviours:
    func = """def %s(unit, item):
                  for component in item.components:
                      if component.defines('%s'):
                          return component.%s(unit, item)
                  return False""" \
        % (behaviour, behaviour, behaviour)
    exec(func)

exclusive_behaviours = ('minimum_range', 'maximum_range', 'splash', 'damage', 'splash_multiplier', 'damage_formula')

for behaviour in exclusive_behaviours:
    func = """def %s(unit, item):
                  for component in item.components:
                      if component.defines('%s'):
                          return component.%s(unit, item)
                  return Defaults.%s(unit, item)""" \
        % (behaviour, behaviour, behaviour, behaviour)
    exec(func)

event_behaviours = ('on_use', 'on_not_available', 'on_end_chapter')

for behaviour in event_behaviours:
    func = """def %s(unit, item):
                  for component in item.components:
                      if component.defines('%s'):
                          component.%s(unit, item)""" \
        % (behaviour, behaviour, behaviour)
    exec(func)

def get_range(unit, item) -> set:
    min_range, max_range = 0, 0
    for component in item.components:
        if component.defines('minimum_range'):
            min_range = component.minimum_range(unit, item)
            break
    for component in item.components:
        if component.defines('maximum_range'):
            max_range = component.maximum_range(unit, item)
            break
    return set(range(min_range, max_range + 1))

def valid_targets(unit, item) -> set:
    targets = set()
    for component in item.components:
        if component.defines('valid_targets'):
            targets |= component.valid_targets(unit, item)
    return targets

def available(unit, item) -> bool:
    for component in item.components:
        if component.defines('available'):
            if not component.available(unit, item):
                return False
    return True

def on_hit(unit, item, target, mode=None):
    for component in item.components:
        if component.defines('on_hit'):
            component.on_hit(unit, item, target, mode)

def on_crit(unit, item, target, mode=None):
    for component in item.components:
        if component.defines('on_crit'):
            component.on_crit(unit, item, target, mode)
        elif component.defines('on_hit'):
            component.on_hit(unit, item, target, mode)

def on_miss(unit, item, target, mode=None):
    for component in item.components:
        if component.defines('on_miss'):
            component.on_miss(unit, item, target, mode)
