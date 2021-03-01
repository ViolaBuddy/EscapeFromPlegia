from app.data.database import DB
from app.engine import target_system, skill_system, action, equations
from app.engine.game_state import game

class Ability():
    @staticmethod
    def targets(unit) -> set:
        return set()

    @staticmethod        
    def highlights(unit):
        pass
    
    @staticmethod
    def do(unit):
        pass

class AttackAbility(Ability):
    name = 'Attack'

    @staticmethod
    def targets(unit) -> set:
        if unit.has_attacked:
            return set()
        return target_system.get_all_weapon_targets(unit)
    
    @staticmethod
    def highlights(unit):
        valid_attacks = target_system.get_possible_attacks(unit, {unit.position})
        game.highlight.display_possible_attacks(valid_attacks)

class SpellAbility(Ability):
    name = 'Spells'

    @staticmethod
    def targets(unit) -> set:
        if unit.has_attacked:
            return set()
        return target_system.get_all_spell_targets(unit)

    @staticmethod
    def highlights(unit):
        valid_attacks = target_system.get_possible_spell_attacks(unit, {unit.position})
        game.highlight.display_possible_spell_attacks(valid_attacks)

class TalkAbility(Ability):
    name = 'Talk'

    @staticmethod
    def targets(unit) -> set:
        adj_units = target_system.get_adj_units(unit)
        return set([u.position for u in adj_units if (unit.nid, u.nid) in game.talk_options])

    @staticmethod
    def do(unit):
        u = game.board.get_unit(game.cursor.position)
        game.state.back()
        action.do(action.HasTraded(unit))
        did_trigger = game.events.trigger('on_talk', unit, u, unit.position)
        if did_trigger:
            action.do(action.RemoveTalk(unit.nid, u.nid))
        
class DropAbility(Ability):
    name = "Drop"

    @staticmethod
    def targets(unit) -> set:
        if unit.traveler and not unit.has_attacked and not unit.has_rescued:
            good_pos = set()
            adj_positions = target_system.get_adjacent_positions(unit.position)
            u = game.get_unit(unit.traveler)
            for adj_pos in adj_positions:
                if not game.board.get_unit(adj_pos) and game.movement.check_traversable(u, adj_pos):
                    good_pos.add(adj_pos)
            return good_pos
        return set()

    @staticmethod
    def do(unit):
        game.state.change('menu')
        u = game.get_unit(unit.traveler)
        action.do(action.Drop(unit, u, game.cursor.position))
        if skill_system.has_canto(unit):
            action.do(action.HasTraded(unit))
            game.state.change('menu')
        else:
            game.state.change('free')
            game.cursor.set_pos(unit.position)
            unit.wait()

class RescueAbility(Ability):
    name = "Rescue"

    @staticmethod
    def targets(unit) -> set:
        if not unit.traveler and not unit.has_attacked and not unit.has_given and not unit.has_dropped:
            adj_allies = target_system.get_adj_allies(unit)
            return set([u.position for u in adj_allies if not u.traveler and
                        equations.parser.rescue_aid(unit) >= equations.parser.rescue_weight(u)])

    @staticmethod
    def do(unit):
        u = game.board.get_unit(game.cursor.position)
        action.do(action.Rescue(unit, u))
        if skill_system.has_canto(unit):
            action.do(action.HasTraded(unit))
            game.state.change('menu')
        else:
            game.state.change('free')
            game.cursor.set_pos(unit.position)
            unit.wait()

class TakeAbility(Ability):
    name = 'Take'

    @staticmethod
    def targets(unit) -> set:
        if not unit.traveler and not unit.has_attacked and not unit.has_given and not unit.has_dropped:
            adj_allies = target_system.get_adj_allies(unit)
            return set([u.position for u in adj_allies if u.traveler and
                        equations.parser.rescue_aid(unit) > equations.parser.rescue_weight(game.get_unit(u.traveler))])

    @staticmethod
    def do(unit):
        u = game.board.get_unit(game.cursor.position)
        action.do(action.HasTraded(unit))
        action.do(action.Take(unit, u))
        # Taking does not count as major action
        game.state.change('menu')

class GiveAbility(Ability):
    name = 'Give'

    @staticmethod
    def targets(unit) -> set:
        if unit.traveler and not unit.has_attacked and (not unit.has_taken or DB.constants.value('give_and_take')) and not unit.has_rescued:
            adj_allies = target_system.get_adj_allies(unit)
            return set([u.position for u in adj_allies if not u.traveler and
                        equations.parser.rescue_aid(u) > equations.parser.rescue_weight(game.get_unit(unit.traveler))])

    @staticmethod
    def do(unit):
        u = game.board.get_unit(game.cursor.position)
        action.do(action.HasTraded(unit))
        action.do(action.Give(unit, u))
        # Giving does not count as a major action
        game.state.change('menu')

class ItemAbility(Ability):
    name = 'Item'

    @staticmethod
    def targets(unit) -> set:
        if unit.items:
            return {unit.position}
        return set()

class TradeAbility(Ability):
    name = 'Trade'

    @staticmethod
    def targets(unit) -> set:
        adj_allies = target_system.get_adj_allies(unit)
        return set([u.position for u in adj_allies if unit.team == u.team])

    @staticmethod
    def do(unit):
        game.state.change('trade')

ABILITIES = Ability.__subclasses__()
