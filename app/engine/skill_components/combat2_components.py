from app.data.skill_components import SkillComponent
from app.data.components import Type

from app.utilities import utils
from app.engine import action
from app.engine.game_state import game

class Miracle(SkillComponent):
    nid = 'miracle'
    desc = "Unit cannot be reduced below 1 HP"
    tag = 'combat2'

    def cleanup_combat(self, playback, unit, item, target, mode):
        if unit.get_hp() <= 0:
            action.do(action.SetHP(unit, 1))
            game.death.miracle(unit)
            action.do(action.TriggerCharge(unit, self.skill))

class IgnoreDamage(SkillComponent):
    nid = 'ignore_damage'
    desc = "Unit will ignore all damage"
    tag = 'combat2'

    def after_hit(self, actions, playback, unit, item, target, mode):
        # Remove any acts that reduce my HP!
        did_something = False
        for act in reversed(actions):
            if isinstance(act, action.ChangeHP) and act.num < 0:
                actions.remove(act)
                did_something = True

        if did_something:
            actions.append(action.TriggerCharge(unit, self.skill))

class LiveToServe(SkillComponent):
    nid = 'live_to_serve'
    desc = r"Unit will be healed X% of amount healed"
    tag = 'combat2'

    expose = Type.Float
    value = 1.0

    def after_hit(self, actions, playback, unit, item, target, mode):
        total_amount_healed = 0
        playbacks = [p for p in playback if p[0] == 'heal_hit' and p[1] is unit and p[3] is not unit]
        for p in playbacks:
            total_amount_healed += p[4]

        amount = int(total_amount_healed * self.value)
        if amount > 0:
            true_heal = min(amount, unit.get_max_hp() - unit.get_hp())
            playback.append(('heal_hit', unit, item, unit, true_heal, true_heal))
            actions.append(action.ChangeHP(unit, amount))
            actions.append(action.TriggerCharge(unit, self.skill))

class Lifelink(SkillComponent):
    nid = 'lifelink'
    desc = "Heals user %% of damage dealt"
    tag = 'combat2'

    expose = Type.Float
    value = 0.5

    def after_hit(self, actions, playback, unit, item, target, mode):
        total_damage_dealt = 0
        playbacks = [p for p in playback if p[0] in ('damage_hit', 'damage_crit') and p[1] == unit]
        for p in playbacks:
            total_damage_dealt += p[5]

        damage = utils.clamp(total_damage_dealt, 0, target.get_hp())
        true_damage = int(damage * self.value)
        actions.append(action.ChangeHP(unit, true_damage))

        playback.append(('heal_hit', unit, item, unit, true_damage, true_damage))

        actions.append(action.TriggerCharge(unit, self.skill))

class LimitMaximumRange(SkillComponent):
    nid = 'limit_maximum_range'
    desc = "limits unit's maximum allowed range"
    tag = 'combat2'

    expose = Type.Int
    value = 1

    def limit_maximum_range(self, unit, item):
        return self.value

class ModifyMaximumRange(SkillComponent):
    nid = 'modify_maximum_range'
    desc = "modifies unit's maximum allowed range"
    tag = 'combat2'

    expose = Type.Int
    value = 1

    def modify_maximum_range(self, unit, item):
        return self.value

class CannotDouble(SkillComponent):
    nid = 'cannot_double'
    desc = "Unit cannot double"
    tag = 'combat2'

    def no_double(self, unit):
        return True

class CanDoubleOnDefense(SkillComponent):
    nid = 'can_double_on_defense'
    desc = "Unit can double while defending (extraneous if set to True in constants)"
    tag = 'combat2'

    def def_double(self, unit):
        return True

class Vantage(SkillComponent):
    nid = 'vantage'
    desc = "Unit will attack first even while defending"
    tag = 'combat2'

    def vantage(self, unit):
        return True

class GuaranteedCrit(SkillComponent):
    nid = 'guaranteed_crit'
    desc = "Unit will have chance to crit even if crit constant is turned off"
    tag = 'combat2'

    def crit_anyway(self, unit):
        return True

class DistantCounter(SkillComponent):
    nid = 'distant_counter'
    desc = "Unit has infinite range when defending"
    tag = 'combat2'

    def distant_counter(self, unit):
        return True

class Oversplash(SkillComponent):
    nid = 'oversplash'
    desc = "Grants unit +X area of effect for regular and blast items"
    tag = 'combat2'

    expose = Type.Int
    value = 1

    def empower_splash(self, unit):
        return self.value

    def alternate_splash(self, unit):
        from app.engine.item_components.aoe_components import BlastAOE
        return BlastAOE(0)

class Cleave(SkillComponent):
    nid = 'Cleave'
    desc = "Grants unit the ability to cleave with all their non-splash attacks"
    tag = 'combat2'

    def alternate_splash(self, unit):
        from app.engine.item_components.aoe_components import EnemyCleaveAOE
        return EnemyCleaveAOE()

class GiveStatusAfterCombat(SkillComponent):
    nid = 'give_status_after_combat'
    desc = "Gives a status to target after combat"
    tag = 'combat2'

    expose = Type.Skill

    def end_combat(self, playback, unit, item, target, mode):
        from app.engine import skill_system
        if target and skill_system.check_enemy(unit, target):
            action.do(action.AddSkill(target, self.value, unit))
            action.do(action.TriggerCharge(unit, self.skill))

class GiveStatusAfterAttack(SkillComponent):
    nid = 'give_status_after_attack'
    desc = "Gives a status to target after attacking the target"
    tag = 'combat2'

    expose = Type.Skill

    def end_combat(self, playback, unit, item, target, mode):
        mark_playbacks = [p for p in playback if p[0] in ('mark_miss', 'mark_hit', 'mark_crit')]
        if target and any(p[3] == unit for p in mark_playbacks):  # Unit is overall attacker
            action.do(action.AddSkill(target, self.value, unit))
            action.do(action.TriggerCharge(unit, self.skill))

class GiveStatusAfterHit(SkillComponent):
    nid = 'give_status_after_hit'
    desc = "Gives a status to target after hitting them"
    tag = 'combat2'

    expose = Type.Skill

    def after_hit(self, actions, playback, unit, item, target, mode):
        mark_playbacks = [p for p in playback if p[0] in ('mark_miss', 'mark_hit', 'mark_crit')]
        if target and any(p[3] == unit for p in mark_playbacks):  # Unit is overall attacker
            actions.append(action.AddSkill(target, self.value, unit))
            actions.append(action.TriggerCharge(unit, self.skill))

class GainSkillAfterKill(SkillComponent):
    nid = 'gain_skill_after_kill'
    desc = "Gives a skill to user after a kill"
    tag = 'combat2'

    expose = Type.Skill

    def end_combat(self, playback, unit, item, target, mode):
        if target and target.get_hp() <= 0:
            action.do(action.AddSkill(unit, self.value))
            action.do(action.TriggerCharge(unit, self.skill))

class GainSkillAfterAttacking(SkillComponent):
    nid = 'gain_skill_after_attack'
    desc = "Gives a skill to user after an attack"
    tag = 'combat2'

    expose = Type.Skill

    def end_combat(self, playback, unit, item, target, mode):
        mark_playbacks = [p for p in playback if p[0] in ('mark_miss', 'mark_hit', 'mark_crit')]
        if any(p[3] == unit for p in mark_playbacks):  # Unit is overall attacker
            action.do(action.AddSkill(unit, self.value))
            action.do(action.TriggerCharge(unit, self.skill))

class GainSkillAfterActiveKill(SkillComponent):
    nid = 'gain_skill_after_active_kill'
    desc = "Gives a skill after a kill on personal phase"
    tag = 'combat2'

    expose = Type.Skill

    def end_combat(self, playback, unit, item, target, mode):
        mark_playbacks = [p for p in playback if p[0] in ('mark_miss', 'mark_hit', 'mark_crit')]
        if target and target.get_hp() <= 0 and any(p[3] == unit for p in mark_playbacks):  # Unit is overall attacker
            action.do(action.AddSkill(unit, self.value))
            action.do(action.TriggerCharge(unit, self.skill))

class DelayInitiativeOrder(SkillComponent):
    nid = 'delay_initiative_order'
    desc = "Delays the target's next turn by X after hit. Cannot activate when unit is defending."
    tag = 'combat2'

    expose = Type.Int
    value = 1
    author = "KD"

    def after_hit(self, actions, playback, unit, item, target, mode):
        mark_playbacks = [p for p in playback if p[0] in ('mark_miss', 'mark_hit', 'mark_crit')]
        if target and target.get_hp() <= 0 and any(p[3] == unit for p in mark_playbacks):  # Unit is overall attacker
            actions.append(action.MoveInInitiative(target, self.value))
            actions.append(action.TriggerCharge(unit, self.skill))
