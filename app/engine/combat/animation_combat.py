from app.constants import TILEWIDTH, TILEHEIGHT, WINWIDTH, WINHEIGHT, TILEX, TILEY
from app.resources.resources import RESOURCES
from app.data.database import DB

from app.engine.sprites import SPRITES
from app.engine.fonts import FONT

from app.utilities import utils

from app.engine.combat.solver import CombatPhaseSolver

from app.engine.sound import SOUNDTHREAD
from app.engine import engine, combat_calcs, gui, action, battle_animation, \
    item_system, skill_system, icons, item_funcs
from app.engine.health_bar import CombatHealthBar
from app.engine.game_state import game

from app.engine.objects.item import ItemObject
from app.engine.objects.unit import UnitObject

from app.engine.combat.map_combat import MapCombat
from app.engine.combat.base_combat import BaseCombat
from app.engine.combat.mock_combat import MockCombat

class AnimationCombat(BaseCombat, MockCombat):
    alerts: bool = True

    def __init__(self, attacker: UnitObject, main_item: ItemObject, defender: UnitObject, def_item: ItemObject, script: list):
        self.attacker = attacker
        self.defender = defender
        self.main_item = main_item
        self.def_item = def_item

        if self.defender.team == 'player' and self.attacker.team != 'player':
            self.right = self.defender
            self.right_item = self.def_item
            self.left = self.attacker
            self.left_item = self.main_item
        elif self.attacker.team.startswith('enemy') and not self.defender.team.startswith('enemy'):
            self.right = self.defender
            self.right_item = self.def_item
            self.left = self.attacker
            self.left_item = self.main_item
        else:
            self.right = self.attacker
            self.right_item = self.main_item
            self.left = self.defender
            self.left_item = self.def_item

        if self.attacker.position and self.defender.position:
            self.distance = utils.calculate_distance(self.attacker.position, self.defender.position)
        else:
            self.distance = 1
        self.at_range = self.distance - 1

        if self.defender.position:
            self.view_pos = self.defender.position
        elif self.attacker.position:
            self.view_pos = self.attacker.position
        else:
            self.view_pos = (0, 0)

        self.state_machine = CombatPhaseSolver(
            self.attacker, self.main_item, [self.main_item],
            [self.defender], [[]], [self.defender.position],
            self.defender, self.def_item, script)

        self.last_update = engine.get_time()
        self.state = 'init'

        self.left_hp_bar = CombatHealthBar(self.left)
        self.right_hp_bar = CombatHealthBar(self.right)

        self._skip = False
        self.full_playback = []
        self.playback = []
        self.actions = []

        self.viewbox_time = 250
        self.viewbox = None

        self.setup_dark()

        self.setup_ui()

        # For pan
        self.focus_right: bool = self.attacker is self.right
        self.setup_pan()

        # For shake
        self.setup_shake()

        self.battle_music = None

        self.left_battle_anim = battle_animation.get_battle_anim(self.left, self.left_item, self.distance)
        self.right_battle_anim = battle_animation.get_battle_anim(self.right, self.right_item, self.distance)
        self.current_battle_anim = None

        self.initial_paint_setup()
        self._set_stats()

    def skip(self):
        self._skip = True
        battle_animation.battle_anim_speed = 0.25

    def end_skip(self):
        self._skip = False
        battle_animation.battle_anim_speed = 1

    def update(self) -> bool:
        current_time = engine.get_time() - self.last_update
        current_state = self.state

        if self.state == 'init':
            self.start_combat()
            self.attacker.sprite.change_state('combat_attacker')
            self.defender.sprite.change_state('combat_defender')
            self.state = 'red_cursor'
            game.cursor.combat_show()
            game.cursor.set_pos(self.view_pos)
            if not self._skip:
                game.state.change('move_camera')
            self._set_stats()  # For start combat changes

        elif self.state == 'red_cursor':
            if self._skip or current_time > 400:
                game.cursor.hide()
                game.highlight.remove_highlights()
                self.state = 'fade_in'

        elif self.state == 'fade_in':
            if current_time <= self.viewbox_time:
                self.build_viewbox(current_time)
            else:
                self.viewbox = (self.viewbox[0], self.viewbox[1], 0, 0)
                self.state = 'entrance'
                left_pos = (self.left.position[0] - game.camera.get_x()) * TILEWIDTH, \
                    (self.left.position[1] - game.camera.get_y()) * TILEHEIGHT
                right_pos = (self.right.position[0] - game.camera.get_x()) * TILEWIDTH, \
                    (self.right.position[1] - game.camera.get_y()) * TILEHEIGHT
                self.left_battle_anim.pair(self, self.right_battle_anim, False, self.at_range, 14, left_pos)
                self.right_battle_anim.pair(self, self.left_battle_anim, True, self.at_range, 14, right_pos)
                # Unit should be facing down
                self.attacker.sprite.change_state('selected')

        elif self.state == 'entrance':
            entrance_time = utils.frames2ms(10)
            self.bar_offset = current_time / entrance_time
            self.name_offset = current_time / entrance_time
            if self._skip or current_time > entrance_time:
                self.bar_offset = 1
                self.name_offset = 1
                self.state = 'init_pause'
                self.start_battle_music()

        elif self.state == 'init_pause':
            if self._skip or current_time > utils.frames2ms(25):
                self.state = 'pre_proc'

        elif self.state == 'pre_proc':
            if self.left_battle_anim.done() and self.right_battle_anim.done():
                # These would have happened from pre_combat and start_combat
                if self.get_from_full_playback('attack_pre_proc'):
                    self.set_up_pre_proc_animation('attack_pre_proc')
                elif self.get_from_full_playback('defense_pre_proc'):
                    self.set_up_pre_proc_animation('defense_pre_proc')
                else:
                    self.state = 'init_effects'

        elif self.state == 'init_effects':
            if not self.left_battle_anim.effect_playing() and not self.right_battle_anim.effect_playing():
                any_effect: bool = False
                if self.right_item:
                    mode = 'attack' if self.right is self.attacker else 'defense'
                    effect = item_system.combat_effect(self.right, self.right_item, self.left, mode)
                    if effect:
                        any_effect = True
                        self.right_battle_anim.add_effect(effect)
                elif self.left_item:
                    mode = 'attack' if self.left is self.attacker else 'defense'
                    effect = item_system.combat_effect(self.left, self.left_item, self.right, mode)
                    if effect:
                        any_effect = True
                        self.left_battle_anim.add_effect(effect)
                
                if any_effect:
                    pass # Stay on current state
                else:
                    self.state = 'begin_phase'

        elif self.state == 'begin_phase':
            # Get playback
            if not self.state_machine.get_state():
                self.state = 'end_combat'
                self.actions.clear()
                self.playback.clear()
                return False
            self.actions, self.playback = self.state_machine.do()
            self.full_playback += self.playback
            if not self.actions and not self.playback:
                self.state_machine.setup_next_state()
                return False
            self._set_stats()

            if self.get_from_playback('attack_proc'):
                self.set_up_proc_animation('attack_proc')
            elif self.get_from_playback('defense_proc'):
                self.set_up_proc_animation('defense_proc')
            else:
                self.set_up_combat_animation()

        elif self.state == 'attack_proc':
            if self.left_battle_anim.done() and self.right_battle_anim.done() and current_time > 400:
                if self.get_from_playback('defense_proc'):
                    self.set_up_proc_animation('defense_proc')
                else:
                    self.set_up_combat_animation()

        elif self.state == 'defense_proc':
            if self.left_battle_anim.done() and self.right_battle_anim.done() and current_time > 400:
                self.set_up_combat_animation()

        elif self.state == 'anim':
            if self.left_battle_anim.done() and self.right_battle_anim.done():
                self.state = 'end_phase'

        elif self.state == 'hp_change':
            proceed = self.current_battle_anim.can_proceed()
            if current_time > utils.frames2ms(27) and self.left_hp_bar.done() and self.right_hp_bar.done() and proceed:
                self.current_battle_anim.resume()
                if self.left.get_hp() <= 0:
                    self.left_battle_anim.start_dying_animation()
                if self.right.get_hp() <= 0:
                    self.right_battle_anim.start_dying_animation()
                if (self.left.get_hp() <= 0 or self.right.get_hp() <= 0) and self.current_battle_anim.state != 'dying':
                    self.current_battle_anim.wait_for_dying()
                self.state = 'anim'

        elif self.state == 'end_phase':
            self._end_phase()
            self.state_machine.setup_next_state()
            self.state = 'begin_phase'

        elif self.state == 'end_combat':
            if self.left_battle_anim.done() and self.right_battle_anim.done():
                self.state = 'exp_pause'
                self.focus_exp()
                self.move_camera()

        elif self.state == 'exp_pause':
            if self._skip or current_time > 450:
                self.clean_up1()
                self.state = 'exp_wait'

        elif self.state == 'exp_wait':
            # waits here for exp_gain state to finish
            self.state = 'fade_out_wait'

        elif self.state == 'fade_out_wait':
            if self._skip or current_time > 820:
                self.left_battle_anim.finish()
                self.right_battle_anim.finish()
                self.state = 'name_tags_out'

        elif self.state == 'name_tags_out':
            exit_time = utils.frames2ms(10)
            self.name_offset = 1 - current_time / exit_time
            if self._skip or current_time > exit_time:
                self.name_offset = 0
                self.state = 'all_out'

        elif self.state == 'all_out':
            exit_time = utils.frames2ms(10)
            self.bar_offset = 1 - current_time / exit_time
            if self._skip or current_time > exit_time:
                self.bar_offset = 0
                self.state = 'fade_out'

        elif self.state == 'fade_out':
            if current_time <= self.viewbox_time:
                self.build_viewbox(self.viewbox_time - current_time)
            else:
                self.finish()
                self.clean_up2()
                self.end_skip()
                return True

        if self.state != current_state:
            self.last_update = engine.get_time()

        # Update hp bars
        self.left_hp_bar.update()
        self.right_hp_bar.update()

        self.update_anims()

        return False

    def initial_paint_setup(self):
        crit_flag = DB.constants.value('crit')
        # Left
        left_color = utils.get_team_color(self.left.team)
        # Name tag
        self.left_name = SPRITES.get('combat_name_left_' + left_color).copy()
        if FONT['text-brown'].width(self.left.name) > 52:
            font = FONT['narrow-brown']
        else:
            font = FONT['text-brown']
        font.blit_center(self.left.name, self.left_name, (30, 8))
        # Bar
        if crit_flag:
            self.left_bar = SPRITES.get('combat_main_crit_left_' + left_color).copy()
        else:
            self.left_bar = SPRITES.get('combat_main_left_' + left_color).copy()
        if self.left_item:
            name = self.left_item.name
            if FONT['text-brown'].width(name) > 60:
                font = FONT['narrow-brown']
            else:
                font = FONT['text-brown']
            font.blit_center(name, self.left_bar, (91, 5 + (8 if crit_flag else 0)))

        # Right
        right_color = utils.get_team_color(self.right.team)
        # Name tag
        self.right_name = SPRITES.get('combat_name_right_' + right_color).copy()
        if FONT['text-brown'].width(self.right.name) > 52:
            font = FONT['narrow-brown']
        else:
            font = FONT['text-brown']
        font.blit_center(self.right.name, self.right_name, (36, 8))
        # Bar
        if crit_flag:
            self.right_bar = SPRITES.get('combat_main_crit_right_' + right_color).copy()
        else:
            self.right_bar = SPRITES.get('combat_main_right_' + right_color).copy()
        if self.right_item:
            name = self.right_item.name
            if FONT['text-brown'].width(name) > 60:
                font = FONT['narrow-brown']
            else:
                font = FONT['text-brown']
            font.blit_center(name, self.right_bar, (47, 5 + (8 if crit_flag else 0)))

        # Platforms
        if self.left.position:
            terrain_nid = game.tilemap.get_terrain(self.left.position)
            left_terrain = DB.terrain.get(terrain_nid)
            if not left_terrain:
                left_terrain = DB.terrain[0]
            left_platform_type = left_terrain.platform
        else:
            left_platform_type = 'Arena'

        if self.right.position:
            terrain_nid = game.tilemap.get_terrain(self.right.position)
            right_terrain = DB.terrain.get(terrain_nid)
            if not right_terrain:
                right_terrain = DB.terrain[0]
            right_platform_type = right_terrain.platform
        else:
            right_platform_type = 'Arena'

        if self.at_range:
            suffix = '-Ranged'
        else:
            suffix = '-Melee'

        left_platform_full_loc = RESOURCES.platforms.get(left_platform_type + suffix)
        self.left_platform = engine.image_load(left_platform_full_loc)
        right_platform_full_loc = RESOURCES.platforms.get(right_platform_type + suffix)
        self.right_platform = engine.flip_horiz(engine.image_load(right_platform_full_loc))

    def start_hit(self, sound=True, miss=False):
        self._apply_actions()
        self._handle_playback(sound)

        if miss:
            self.miss_anim()

    def spell_hit(self):
        self._apply_actions()
        self._handle_playback()

    def _handle_playback(self, sound=True):
        for brush in self.playback:
            if brush[0] in ('damage_hit', 'damage_crit', 'heal_hit'):
                self.last_update = engine.get_time()
                self.state = 'hp_change'
                self.handle_damage_numbers(brush)
            elif brush[0] == 'hit_sound' and sound:
                sound = brush[1]
                if sound == 'Attack Miss 2':
                    sound = 'Miss'  # Replace with miss sound
                SOUNDTHREAD.play_sfx(sound)

    def _apply_actions(self):
        """
        Actually commit the actions that we had stored!
        """
        for act in self.actions:
            action.do(act)

    def _end_phase(self):
        pass

    def finish(self):
        # Fade back music if and only if it was faded in
        if self.battle_music:
            SOUNDTHREAD.battle_fade_back(self.battle_music)

    def build_viewbox(self, current_time):
        vb_multiplier = utils.clamp(current_time / self.viewbox_time, 0, 1)
        true_x, true_y = self.view_pos[0] - game.camera.get_x() + 0.5, self.view_pos[1] - game.camera.get_y() + 0.5
        vb_x = int(vb_multiplier * true_x * TILEWIDTH)
        vb_y = int(vb_multiplier * true_y * TILEHEIGHT)
        vb_width = int(WINWIDTH - vb_x - (vb_multiplier * (TILEX - true_x)) * TILEWIDTH)
        vb_height = int(WINHEIGHT - vb_y - (vb_multiplier * (TILEY - true_y)) * TILEHEIGHT)
        self.viewbox = (vb_x, vb_y, vb_width, vb_height)

    def start_battle_music(self):
        attacker_battle = item_system.battle_music(self.attacker, self.main_item, self.defender, 'attack')
        if self.def_item:
            defender_battle = item_system.battle_music(self.defender, self.def_item, self.attacker, 'defense')
        else:
            defender_battle = None
        battle_music = game.level.music['%s_battle' % self.attacker.team]
        if attacker_battle:
            self.battle_music = SOUNDTHREAD.battle_fade_in(attacker_battle)
        elif defender_battle:
            self.battle_music = SOUNDTHREAD.battle_fade_in(defender_battle)
        elif battle_music:
            self.battle_music = SOUNDTHREAD.battle_fade_in(battle_music) 

    def left_team(self):
        return self.left.team

    def right_team(self):
        return self.right.team

    def _set_stats(self):
        a_hit = combat_calcs.compute_hit(self.attacker, self.defender, self.main_item, self.def_item, 'attack')
        a_mt = combat_calcs.compute_damage(self.attacker, self.defender, self.main_item, self.def_item, 'attack')
        if DB.constants.value('crit'):
            a_crit = combat_calcs.compute_crit(self.attacker, self.defender, self.main_item, self.def_item, 'attack')
        else:
            a_crit = 0
        a_stats = a_hit, a_mt, a_crit

        if self.def_item and combat_calcs.can_counterattack(self.attacker, self.main_item, self.defender, self.def_item):
            d_hit = combat_calcs.compute_hit(self.defender, self.attacker, self.def_item, self.main_item, 'defense')
            d_mt = combat_calcs.compute_damage(self.defender, self.attacker, self.def_item, self.main_item, 'defense')
            if DB.constants.value('crit'):
                d_crit = combat_calcs.compute_crit(self.defender, self.attacker, self.def_item, self.main_item, 'defense')
            else:
                d_crit = 0
            d_stats = d_hit, d_mt, d_crit
        else:
            d_stats = None

        if self.attacker is self.right:
            self.left_stats = d_stats
            self.right_stats = a_stats
        else:
            self.left_stats = a_stats
            self.right_stats = d_stats

    def set_up_pre_proc_animation(self, mark_type):
        marks = self.get_from_full_playback(mark_type)
        mark = marks.pop()
        self.full_playback.remove(mark)
        self.mark_proc(mark)

    def set_up_proc_animation(self, mark_type):
        self.state = mark_type
        marks = self.get_from_playback(mark_type)
        mark = marks.pop()
        # Remove the mark since we no longer want to consider it
        self.playback.remove(mark)
        self.mark_proc(mark)

    def mark_proc(self, mark):
        skill = mark[2]
        unit = mark[1]
        if unit == self.right:
            effect = self.right_battle_anim.get_effect(skill.nid, pose='Attack')
            if effect:
                self.right_battle_anim.add_effect(effect)
        else:
            effect = self.left_battle_anim.get_effect(skill.nid, pose='Attack')
            if effect:
                self.left_battle_anim.add_effect(effect)

        self.add_proc_icon(mark)
        if unit == self.right:
            self.focus_right = True
        else:
            self.focus_right = False
        self.move_camera()

    def set_up_combat_animation(self):
        self.state = 'anim'
        if self.get_from_playback('defender_phase'):
            if self.attacker is self.left:
                self.current_battle_anim = self.right_battle_anim
            else:
                self.current_battle_anim = self.left_battle_anim
        else:
            if self.attacker is self.left:
                self.current_battle_anim = self.left_battle_anim
            else:
                self.current_battle_anim = self.right_battle_anim
        alternate_pose = self.get_from_playback('alternate_battle_pose')
        if alternate_pose:
            alternate_pose = alternate_pose[0][1]
        if alternate_pose and self.current_battle_anim.has_pose(alternate_pose):
            self.current_battle_anim.start_anim(alternate_pose)
        elif self.get_from_playback('mark_crit'):
            self.current_battle_anim.start_anim('Critical')
        elif self.get_from_playback('mark_hit'):
            self.current_battle_anim.start_anim('Attack')
        elif self.get_from_playback('mark_miss'):
            self.current_battle_anim.start_anim('Miss')

        if self.right_battle_anim == self.current_battle_anim:
            self.focus_right = True
        else:
            self.focus_right = False
        self.move_camera()

    def handle_damage_numbers(self, brush):
        if brush[0] == 'damage_hit':
            damage = brush[4]
            if damage <= 0:
                return
            str_damage = str(damage)
            left = brush[3] == self.left
            for idx, num in enumerate(str_damage):
                d = gui.DamageNumber(int(num), idx, len(str_damage), left, 'red')
                self.damage_numbers.append(d)
        elif brush[0] == 'damage_crit':
            damage = brush[4]
            if damage <= 0:
                return
            str_damage = str(damage)
            left = brush[3] == self.left
            for idx, num in enumerate(str_damage):
                d = gui.DamageNumber(int(num), idx, len(str_damage), left, 'yellow')
                self.damage_numbers.append(d)
        elif brush[0] == 'heal_hit':
            damage = brush[4]
            if damage <= 0:
                return
            str_damage = str(damage)
            left = brush[3] == self.left
            for idx, num in enumerate(str_damage):
                d = gui.DamageNumber(int(num), idx, len(str_damage), left, 'cyan')
                self.damage_numbers.append(d)

    def add_proc_icon(self, mark):
        unit = mark[1]
        skill = mark[2]
        new_icon = gui.SkillIcon(skill, unit is self.right)
        self.proc_icons.append(new_icon)

    def get_damage(self) -> int:
        damage_hit_marks = self.get_from_playback('damage_hit')
        damage_crit_marks = self.get_from_playback('damage_crit')
        if damage_hit_marks:
            damage = damage_hit_marks[0][4]
        elif damage_crit_marks:
            damage = damage_crit_marks[0][4]
        else:
            damage = 0
        return damage

    def shake(self):
        for brush in self.playback:
            if brush[0] == 'damage_hit':
                damage = brush[4]
                unit = brush[1]
                item = brush[2]
                magic = item_funcs.is_magic(unit, item, self.distance)
                if damage > 0:
                    if magic:
                        self._shake(3)
                    else:
                        self._shake(1)
                else:
                    self._shake(2)  # No damage
            elif brush[0] == 'damage_crit':
                damage = brush[4]
                if damage > 0:
                    self._shake(4)  # Critical
                else:
                    self._shake(2)  # No damage

    def pan_back(self):
        next_state = self.state_machine.get_next_state()
        if next_state:
            if next_state == 'attacker':
                self.focus_right = (self.attacker is self.right)
            elif next_state == 'defender':
                self.focus_right = (self.defender is self.right)
        else:
            self.focus_exp()
        self.move_camera()

    def focus_exp(self):
        # Handle exp
        if self.attacker.team == 'player':
            self.focus_right = (self.attacker is self.right)
        elif self.defender.team == 'player':
            self.focus_right = (self.defender is self.right)

    def draw(self, surf):
        left_range_offset, right_range_offset, total_shake_x, total_shake_y = \
            self.draw_ui(surf)

        shake = (-total_shake_x, total_shake_y)
        if self.playback:
            if self.current_battle_anim is self.right_battle_anim:
                self.left_battle_anim.draw_under(surf, shake, left_range_offset, self.pan_offset)
                self.right_battle_anim.draw_under(surf, shake, right_range_offset, self.pan_offset)
                self.left_battle_anim.draw(surf, shake, left_range_offset, self.pan_offset)
                self.right_battle_anim.draw(surf, shake, right_range_offset, self.pan_offset)
                self.right_battle_anim.draw_over(surf, shake, right_range_offset, self.pan_offset)
                self.left_battle_anim.draw_over(surf, shake, left_range_offset, self.pan_offset)
            else:
                self.right_battle_anim.draw_under(surf, shake, right_range_offset, self.pan_offset)
                self.left_battle_anim.draw_under(surf, shake, left_range_offset, self.pan_offset)
                self.right_battle_anim.draw(surf, shake, right_range_offset, self.pan_offset)
                self.left_battle_anim.draw(surf, shake, left_range_offset, self.pan_offset)
                self.left_battle_anim.draw_over(surf, shake, left_range_offset, self.pan_offset)
                self.right_battle_anim.draw_over(surf, shake, right_range_offset, self.pan_offset)
        else:
            self.left_battle_anim.draw(surf, shake, left_range_offset, self.pan_offset)
            self.right_battle_anim.draw(surf, shake, right_range_offset, self.pan_offset)

        # Animations
        self.draw_anims(surf)

        # Proc Icons
        for proc_icon in self.proc_icons:
            proc_icon.update()
            proc_icon.draw(surf)
        self.proc_icons = [proc_icon for proc_icon in self.proc_icons if not proc_icon.done]

        # Damage Numbers
        self.draw_damage_numbers(surf, (left_range_offset, right_range_offset, total_shake_x, total_shake_y))

        # Combat surf
        combat_surf = engine.copy_surface(self.combat_surf)
        # bar
        left_bar = self.left_bar.copy()
        right_bar = self.right_bar.copy()
        crit = 7 if DB.constants.value('crit') else 0
        # HP bar
        self.left_hp_bar.draw(left_bar, 27, 30 + crit)
        self.right_hp_bar.draw(right_bar, 25, 30 + crit)
        # Item
        if self.left_item:
            self.draw_item(left_bar, self.left_item, self.right_item, self.left, self.right, (45, 2 + crit))
        if self.right_item:
            self.draw_item(right_bar, self.right_item, self.left_item, self.right, self.left, (1, 2 + crit))
        # Stats
        self.draw_stats(left_bar, self.left_stats, (42, 0))
        self.draw_stats(right_bar, self.right_stats, (WINWIDTH // 2 - 3, 0))

        bar_trans = 52
        left_pos_x = -3 + self.shake_offset[0]
        left_pos_y = WINHEIGHT - left_bar.get_height() + (bar_trans - self.bar_offset * bar_trans) + self.shake_offset[1]
        right_pos_x = WINWIDTH // 2 + self.shake_offset[0]
        right_pos_y = left_pos_y
        combat_surf.blit(left_bar, (left_pos_x, left_pos_y))
        combat_surf.blit(right_bar, (right_pos_x, right_pos_y))
        # Nametag
        top = -60 + self.name_offset * 60 + self.shake_offset[1]
        combat_surf.blit(self.left_name, (left_pos_x, top))
        combat_surf.blit(self.right_name, (WINWIDTH + 3 - self.right_name.get_width() + self.shake_offset[0], top))

        self.color_ui(combat_surf)

        surf.blit(combat_surf, (0, 0))

        self.foreground.draw(surf)

    def draw_item(self, surf, item, other_item, unit, other, topleft):
        icon = icons.get_icon(item)
        if icon:
            icon = item_system.item_icon_mod(unit, item, other, icon)
            surf.blit(icon, (topleft[0] + 2, topleft[1] + 3))

        if skill_system.check_enemy(unit, other):
            game.ui_view.draw_adv_arrows(surf, unit, other, item, other_item, (topleft[0] + 11, topleft[1] + 7))

    def draw_stats(self, surf, stats, topright):
        right, top = topright

        hit = '--'
        damage = '--'
        crit = '--'
        if stats is not None:
            if stats[0] is not None:
                hit = str(stats[0])
            if stats[1] is not None:
                damage = str(stats[1])
            if DB.constants.value('crit') and stats[2] is not None:
                crit = str(stats[2])
        FONT['number-small2'].blit_right(hit, surf, (right, top))
        FONT['number-small2'].blit_right(damage, surf, (right, top + 8))
        if DB.constants.value('crit'):
            FONT['number-small2'].blit_right(crit, surf, (right, top + 16))

    def clean_up1(self):
        """
        # This clean up function is called within the update loop (so while still showing combat)
        # Handles miracle, exp, & wexp
        """
        all_units = self._all_units()

        # Handle death
        for unit in all_units:
            if unit.get_hp() <= 0:
                game.death.should_die(unit)
            else:
                unit.sprite.change_state('normal')

        self.cleanup_combat()

        # handle wexp & skills
        if not self.attacker.is_dying:
            self.handle_wexp(self.attacker, self.main_item, self.defender)
        if self.defender and self.def_item and not self.defender.is_dying:
            self.handle_wexp(self.defender, self.def_item, self.attacker)

        self.handle_exp()

    def clean_up2(self):
        game.state.back()

        # attacker has attacked
        action.do(action.HasAttacked(self.attacker))

        self.handle_messages()
        all_units = self._all_units()
        self.turnwheel_death_messages(all_units)

        self.handle_state_stack()
        game.events.trigger('combat_end', self.attacker, self.defender, self.main_item, self.attacker.position)
        self.handle_item_gain(all_units)

        self.handle_supports(all_units)
        self.handle_records(self.full_playback, all_units)

        self.end_combat()

        self.handle_death(all_units)

        a_broke, d_broke = self.find_broken_items()
        self.handle_broken_items(a_broke, d_broke)

    def handle_state_stack(self):
        """
        Map combat has the implementation I want of this, so let's just use it
        """
        MapCombat.handle_state_stack(self)
