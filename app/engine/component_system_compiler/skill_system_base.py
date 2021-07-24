class Defaults():
    @staticmethod
    def can_select(unit) -> bool:
        return unit.team == 'player'

    @staticmethod
    def check_ally(unit1, unit2) -> bool:
        if unit1 is unit2:
            return True
        elif unit1.team == 'player' or unit1.team == 'other':
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
    def num_items_offset(unit) -> int:
        return 0

    @staticmethod
    def num_accessories_offset(unit) -> int:
        return 0

    @staticmethod
    def exp_multiplier(unit1, unit2) -> float:
        return 1.0

    @staticmethod
    def enemy_exp_multiplier(unit1, unit2) -> float:
        return 1.0

    @staticmethod
    def wexp_multiplier(unit1, unit2) -> float:
        return 1.0

    @staticmethod
    def enemy_wexp_multiplier(unit1, unit2) -> float:
        return 1.0

    @staticmethod
    def steal_icon(unit1, unit2) -> bool:
        return False

    @staticmethod
    def has_canto(unit1, unit2) -> bool:
        return False

    @staticmethod
    def empower_heal(unit1, unit2) -> int:
        return 0

    @staticmethod
    def limit_maximum_range(unit, item) -> int:
        return 1000

    @staticmethod
    def modify_maximum_range(unit, item) -> int:
        return 0

    @staticmethod
    def movement_type(unit):
        return None

    @staticmethod
    def sight_range(unit):
        return 0

    @staticmethod
    def empower_splash(unit):
        return 0

    @staticmethod
    def modify_buy_price(unit, item) -> float:
        return 1.0

    @staticmethod
    def modify_sell_price(unit, item) -> float:
        return 1.0

    @staticmethod
    def damage_formula(unit) -> str:
        return 'DAMAGE'

    @staticmethod
    def resist_formula(unit) -> str:
        return 'DEFENSE'

    @staticmethod
    def accuracy_formula(unit) -> str:
        return 'HIT'

    @staticmethod
    def avoid_formula(unit) -> str:
        return 'AVOID'

    @staticmethod
    def crit_accuracy_formula(unit) -> str:
        return 'CRIT_HIT'

    @staticmethod
    def crit_avoid_formula(unit) -> str:
        return 'CRIT_AVOID'

    @staticmethod
    def attack_speed_formula(unit) -> str:
        return 'ATTACK_SPEED'

    @staticmethod
    def defense_speed_formula(unit) -> str:
        return 'DEFENSE_SPEED'

def condition(skill, unit) -> bool:
    for component in skill.components:
        if component.defines('condition'):
            if not component.condition(unit):
                return False
    return True

def available(unit, item) -> bool:
    """
    If any hook reports false, then it is false
    """
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('available'):
                if component.ignore_conditional or condition(skill, unit):
                    if not component.available(unit, item):
                        return False
    return True

def stat_change(unit, stat_nid) -> int:
    bonus = 0
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('stat_change'):
                if component.ignore_conditional or condition(skill, unit):
                    d = component.stat_change(unit)
                    bonus += d.get(stat_nid, 0)
    return bonus

def growth_change(unit, stat_nid) -> int:
    bonus = 0
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('growth_change'):
                if component.ignore_conditional or condition(skill, unit):
                    d = component.growth_change(unit)
                    bonus += d.get(stat_nid, 0)
    return bonus

def mana(playback, unit, item, target) -> int:
    mana = 0
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('mana'):
                if component.ignore_conditional or condition(skill, unit):
                    d = component.mana(playback, unit, item, target)
                    mana += d
    return mana

def can_unlock(unit, region) -> bool:
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('can_unlock'):
                if component.ignore_conditional or condition(skill, unit):
                    if component.can_unlock(unit, region):
                        return True
    return False

def on_upkeep(actions, playback, unit) -> tuple:  # actions, playback
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('on_upkeep'):
                if component.ignore_conditional or condition(skill, unit):
                    component.on_upkeep(actions, playback, unit)
    return actions, playback

def on_endstep(actions, playback, unit) -> tuple:  # actions, playback
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('on_endstep'):
                if component.ignore_conditional or condition(skill, unit):
                    component.on_endstep(actions, playback, unit)
    return actions, playback

def on_end_chapter(unit, skill):
    for component in skill.components:
        if component.defines('on_end_chapter'):
            if component.ignore_conditional or condition(skill, unit):
                component.on_end_chapter(unit, skill)

def init(skill):
    """
    Initializes any data on the parent skill if necessary
    """
    for component in skill.components:
        if component.defines('init'):
            component.init(skill)

def on_add(unit, skill):
    for component in skill.components:
        if component.defines('on_add'):
            component.on_add(unit, skill)
    for other_skill in unit.skills:
        for component in other_skill.components:
            if component.defines('on_gain_skill'):
                component.on_gain_skill(unit, skill)

def on_remove(unit, skill):
    for component in skill.components:
        if component.defines('on_remove'):
            component.on_remove(unit, skill)

def re_add(unit, skill):
    for component in skill.components:
        if component.defines('re_add'):
            component.re_add(unit, skill)

def on_true_remove(unit, skill):
    """
    This one does not intrinsically interact with the turnwheel
    It only fires when the skill is actually removed for the first time
    Not on execute or reverse
    """
    for component in skill.components:
        if component.defines('on_true_remove'):
            component.on_true_remove(unit, skill)

def get_text(skill) -> str:
    for component in skill.components:
        if component.defines('text'):
            return component.text()
    return None

def get_cooldown(skill) -> float:
    for component in skill.components:
        if component.defines('cooldown'):
            return component.cooldown()
    return None

def trigger_charge(unit, skill):
    for component in skill.components:
        if component.defines('trigger_charge'):
            component.trigger_charge(unit, skill)
    return None

def get_extra_abilities(unit):
    abilities = {}
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('extra_ability'):
                if component.ignore_conditional or condition(skill, unit):
                    new_item = component.extra_ability(unit)
                    ability_name = new_item.name
                    abilities[ability_name] = new_item
    return abilities

def get_combat_arts(unit):
    from app.engine import item_funcs, target_system
    combat_arts = {}
    for skill in unit.skills:
        if not condition(skill, unit):
            continue
        combat_art = None
        combat_art_weapons = [item for item in item_funcs.get_all_items(unit) if item_funcs.available(unit, item)]
        combat_art_set_max_range = None
        combat_art_modify_max_range = None
        for component in skill.components:
            if component.defines('combat_art'):
                combat_art = component.combat_art(unit)
            if component.defines('weapon_filter'):
                combat_art_weapons = \
                    [item for item in combat_art_weapons if component.weapon_filter(unit, item)]
            if component.defines('combat_art_set_max_range'):
                combat_art_set_max_range = component.combat_art_set_max_range(unit)
            if component.defines('combat_art_modify_max_range'):
                combat_art_modify_max_range = component.combat_art_modify_max_range(unit)

        if combat_art and combat_art_weapons:
            good_weapons = []
            # Check which of the good weapons meet the range requirements
            for weapon in combat_art_weapons:
                # Just for testing range
                if combat_art_set_max_range:
                    weapon._force_max_range = max(0, combat_art_set_max_range)
                elif combat_art_modify_max_range:
                    max_range = max(item_funcs.get_range(unit, weapon))
                    weapon._force_max_range = max(0, max_range + combat_art_modify_max_range)
                targets = target_system.get_valid_targets(unit, weapon)
                weapon._force_max_range = None
                if targets:
                    good_weapons.append(weapon)

            if good_weapons:
                combat_arts[skill.name] = (skill, good_weapons)

    return combat_arts

def activate_combat_art(unit, skill):
    for component in skill.components:
        if component.defines('on_activation'):
            component.on_activation(unit)

def deactivate_all_combat_arts(unit):
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('on_deactivation'):
                component.on_deactivation(unit)
