
class Defaults():
    @staticmethod
    def can_select(unit) -> bool:
        return unit.team == 'player'

    @staticmethod
    def check_ally(unit1, unit2) -> bool:
        if unit1.team == 'player' or unit1.team == 'other':
            return unit2.team == 'player' or unit2.team == 'other'
        else:
            return unit2.team == unit1.team
        return False

    @staticmethod
    def check_enemy(unit1, unit2) -> bool:
        if unit1.team == 'player' or unit1.team == 'other':
            return not (unit2.team == 'player' or unit2.team == 'other')
        else:
            return not unit2.team == unit1.team
        return True

    @staticmethod
    def can_trade(unit1, unit2) -> bool:
        return unit2.position and unit1.team == unit2.team and check_ally(unit1, unit2)

    @staticmethod
    def sight_range(unit) -> int:
        return 0

default_behaviours = ('has_canto', 'pass_through')

for behaviour in default_behaviours:
    func = """def %s(unit):
                  for component in item.components:
                      if component.defines('%s'):
                          return component.%s(unit)
                  return False""" \
        % (behaviour, behaviour, behaviour)
    exec(func)

exclusive_behaviours = ('can_select', 'check_ally', 'check_enemy', 'can_trade', 'sight_range')

for behaviour in default_behaviours:
    func = """def %s(unit):
                  for component in item.components:
                      if component.defines('%s'):
                          return component.%s(unit)
                  return Defaults.%s(unit)""" \
        % (behaviour, behaviour, behaviour, behaviour)
    exec(func)