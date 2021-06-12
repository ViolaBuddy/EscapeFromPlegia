from app.constants import TILEWIDTH, TILEHEIGHT, WINWIDTH, WINHEIGHT, TILEX, TILEY
from app.resources.resources import RESOURCES
from app.data.database import DB

from app.engine.sprites import SPRITES
from app.engine.fonts import FONT

from app.utilities import utils

from app.engine.combat.solver import CombatPhaseSolver

from app.engine.sound import SOUNDTHREAD
from app.engine import engine, combat_calcs, gui, action, battle_animation, \
    item_system, skill_system, icons, background, image_mods
from app.engine.animations import Animation
from app.engine.health_bar import CombatHealthBar
from app.engine.game_state import game

from app.engine.objects.item import ItemObject
from app.engine.objects.unit import UnitObject

from app.engine.combat.map_combat import MapCombat
from app.engine.combat.base_combat import BaseCombat

class AnimationCombat(BaseCombat):
    alerts: bool = True

    def __init__(self, attacker: UnitObject, main_item: ItemObject, main_target: tuple, script):
        self.attacker = attacker
        self.defender = game.board.get_unit(main_target)
        self.main_item = main_item
        self.def_item = self.defender.get_weapon()

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

        self.darken_background = 0
        self.target_dark = 0
        self.darken_ui_background = 0
        self.foreground = background.Foreground()
        self.combat_surf = engine.create_surface((WINWIDTH, WINHEIGHT), transparent=True)

        self.bar_offset = 0
        self.name_offset = 0
        self.damage_numbers = []
        self.proc_icons = []
        self.animations = []

        self.left_stats = None
        self.right_stats = None

        # For pan
        self.focus_right: bool = self.attacker is self.right
        self.pan_dir = 0
        if self.at_range == 1:
            self.pan_max = 16
            self.pan_move = 4
        elif self.at_range == 2:
            self.pan_max = 32
            self.pan_move = 8
        elif self.at_range >= 3:
            self.pan_max = 120
            self.pan_move = 25
        else:
            self.pan_max = 0
            self.pan_move = 0

        if self.focus_right:
            self.pan_offset = -self.pan_max
        else:
            self.pan_offset = self.pan_max

        # For shake
        self.shake_set = [(0, 0)]
        self.shake_offset = (0, 0)
        self.current_shake = 0
        self.platform_shake_set = [(0, 0)]
        self.platform_shake_offset = (0, 0)
        self.platform_current_shake = 0

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
        self.current_state = self.state

        if self.state == 'init':
            self.start_combat()
            self.attacker.sprite.change_state('combat_attacker')
            self.defender.sprite.change_state('combat_defender')
            self.state = 'red_cursor'
            game.cursor.combat_show()
            game.cursor.set_pos(self.view_pos)
            if not self._skip:
                game.state.change('move_camera')

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
                if self.get_from_playback('attack_pre_proc'):
                    self.set_up_proc_animation('attack_pre_proc')
                elif self.get_from_playback('defense_pre_proc'):
                    self.set_up_proc_animation('defense_pre_proc')
                else:
                    self.state = 'init_effects'

        elif self.state == 'init_effects':
            if not self.left_battle_anim.effect_playing() and not self.right_battle_anim.effect_playing():
                if self.right_item:
                    mode = 'attack' if self.right is self.attacker else 'defense'
                    effect = item_system.combat_effect(self.right, self.right_item, self.left, mode)
                    if effect:
                        self.right_battle_anim.add_effect(effect)
                elif self.left_item:
                    mode = 'attack' if self.left is self.attacker else 'defense'
                    effect = item_system.combat_effect(self.left, self.left_item, self.right, mode)
                    if effect:
                        self.left_battle_anim.add_effect(effect)
                else:
                    self.state = 'begin_phase'

        elif self.state == 'begin_phase':
            # Get playback
            if not self.state_machine.get_state():
                self.state = 'end_combat'
                self.actions = []
                self.playback = []
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
            if current_time > 450 and self.left_hp_bar.done() and self.right_hp_bar.done() and proceed:
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

        if self.state != self.current_state:
            self.last_update = engine.get_time()

        # Update hp bars
        self.left_hp_bar.update()
        self.right_hp_bar.update()

        # Update battle anims
        self.left_battle_anim.update()
        self.right_battle_anim.update()

        # Update shake
        if self.current_shake:
            self.shake_offset = self.shake_set[self.current_shake - 1]
            self.current_shake += 1
            if self.current_shake > len(self.shake_set):
                self.current_shake = 0
        if self.platform_current_shake:
            self.platform_shake_offset = self.platform_shake_set[self.platform_current_shake - 1]
            self.platform_current_shake += 1
            if self.platform_current_shake > len(self.platform_shake_set):
                self.platform_current_shake = 0

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

    def _handle_playback(self, sound=True):
        for brush in self.playback:
            if brush[0] in ('damage_hit', 'damage_crit', 'heal_hit'):
                self.last_update = engine.get_time()
                self.state = 'hp_change'
                self.damage_numbers(brush)
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
            SOUNDTHREAD.fade_back()

    def build_viewbox(self, current_time):
        vb_multiplier = utils.clamp(current_time / self.viewbox_time, 0, 1)
        true_x, true_y = self.view_pos[0] - game.camera.get_x(), self.view_pos[1] - game.camera.get_y()
        vb_x = int(vb_multiplier * true_x * TILEWIDTH)
        vb_y = int(vb_multiplier * true_y * TILEHEIGHT)
        vb_width = int(WINWIDTH - vb_x - (vb_multiplier * (TILEX - true_x)) * TILEWIDTH)
        vb_height = int(WINHEIGHT - vb_y - (vb_multiplier * (TILEY - true_y)) * TILEHEIGHT)
        self.viewbox = (vb_x, vb_y, vb_width, vb_height)

    def start_battle_music(self):
        attacker_battle = item_system.battle_music(self.attacker, self.main_item, self.defender, 'attack')
        defender_battle = item_system.battle_music(self.defender, self.def_item, self.attacker, 'defense')
        battle_music = game.level.music['%s_battle' % self.attacker.team]
        if attacker_battle:
            self.battle_music = SOUNDTHREAD.fade_in(attacker_battle)
        elif defender_battle:
            self.battle_music = SOUNDTHREAD.fade_in(defender_battle)
        elif battle_music:
            self.battle_music = SOUNDTHREAD.fade_in(battle_music) 

    def _set_stats(self):
        a_hit = combat_calcs.compute_hit(self.attacker, self.defender, self.main_item, self.def_item, 'attack')
        a_mt = combat_calcs.compute_damage(self.attacker, self.defender, self.main_item, self.def_item, 'attack')
        if DB.constants.value('crit'):
            a_crit = combat_calcs.compute_crit(self.attacker, self.defender, self.main_item, self.def_item, 'attack')
        else:
            a_crit = 0
        a_stats = a_hit, a_mt, a_crit

        if self.def_item:
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

    def set_up_proc_animation(self, mark_type):
        self.state = mark_type
        marks = self.get_from_playback(mark_type)
        mark = marks.pop()
        # Remove the mark since we no longer want to consider it
        self.playback.remove(mark)

        self.add_proc_icon(mark)
        if mark[1] == self.right:
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
        if self.get_from_playback('mark_crit'):
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

    def damage_numbers(self, brush):
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

    def hit_spark(self):
        if self.get_from_playback('damage_hit') or self.get_from_playback('damage_crit'):
            if self.current_battle_anim is self.right_battle_anim:
                position = (-110, -30)
            else:
                position = (-40, -30)
            anim_nid = 'HitSpark'
            animation = RESOURCES.animations.get(anim_nid)
            if animation:
                anim = Animation(animation, position)
                self.animations.append(anim)
        else:
            self.no_damage()

    def crit_spark(self):
        if self.get_from_playback('damage_hit') or self.get_from_playback('damage_crit'):
            anim_nid = 'HitSpark'
            animation = RESOURCES.animations.get(anim_nid)
            if animation:
                if self.current_battle_anim is self.right_battle_anim:
                    pass
                else:
                    animation.image = engine.flip_horiz(animation.image)
                position = (-40, -30)
                anim = Animation(animation, position)
                self.animations.append(anim)
        else:
            self.no_damage()

    def no_damage(self):
        if self.current_battle_anim is self.right_battle_anim:
            position = (52, 21)
            team = self.right.team
        else:
            position = (110, 21)
            team = self.left.team
        color = utils.get_team_color(team)
        anim_nid = 'NoDamage%s' % color.capitalize()
        animation = RESOURCES.animations.get(anim_nid)
        if animation:
            anim = Animation(animation, position)
            self.animations.append(anim)
        # Also offset battle animation by lr_offset
        self.current_battle_anim.lr_offset = [-1, -2, -3, -2, -1]

    def miss_anim(self):
        if self.current_battle_anim is self.right_battle_anim:
            position = (72, 21)
            team = self.right.team
        else:
            position = (128, 21)  # Enemy's position
            team = self.left.team
        color = utils.get_team_color(team)
        anim_nid = 'Miss%s' % color.capitalize()
        animation = RESOURCES.animations.get(anim_nid)
        if animation:
            anim = Animation(animation, position)
            self.animations.append(anim)

    def shake(self):
        for brush in self.playback:
            if brush[0] == 'damage_hit':
                damage = brush[4]
                if damage > 0:
                    self._shake(1)
                else:
                    self._shake(2)  # No damage
            elif brush[0] == 'damage_crit':
                damage = brush[4]
                if damage > 0:
                    self._shake(4)  # Critical
                else:
                    self._shake(2)  # No damage

    def _shake(self, num):
        self.current_shake = 1
        if num == 1: # Normal Hit
            self.shake_set = [(3, 3), (0, 0), (0, 0), (-3, -3), (0, 0), (0, 0), (3, 3), (0, 0), (-3, -3), (0, 0), 
                              (3, 3), (0, 0), (-3, -3), (3, 3), (0, 0)]
        elif num == 2: # No Damage
            self.shake_set = [(1, 1), (1, 1), (1, 1), (-1, -1), (-1, -1), (-1, -1), (0, 0)]
        elif num == 3: # Spell Hit
            self.shake_set = [(0, 0), (-3, -3), (0, 0), (0, 0), (0, 0), (3, 3), (0, 0), (0, 0), (-3, -3), (0, 0),
                              (0, 0), (3, 3), (0, 0), (-3, -3), (0, 0), (3, 3), (0, 0), (-3, -3), (3, 3), (3, 3), 
                              (0, 0)]
        elif num == 4: # Critical Hit
            self.shake_set = [(-6, -6), (0, 0), (0, 0), (0, 0), (6, 6), (0, 0), (0, 0), (-6, -6), (0, 0), (0, 0),
                              (6, 6), (0, 0), (-6, -6), (0, 0), (6, 6), (0, 0), (4, 4), (0, 0), (-4, -4), (0, 0),
                              (4, 4), (0, 0), (-4, -4), (0, 0), (4, 4), (0, 0), (-2, -2), (0, 0), (2, 2), (0, 0),
                              (-2, -2), (0, 0), (2, 2), (0, 0), (-1, -1), (0, 0), (1, 1), (0, 0)]

    def platform_shake(self):
        self.platform_current_shake = 1
        self.platform_shake_set = [(0, 1), (0, 0), (0, -1), (0, 0), (0, 1), (0, 0), (-1, -1), (0, 1), (0, 0)]

    def screen_flash(self, num_frames, color, fade_out=0):
        self.foreground.flash(num_frames, fade_out, color)

    def darken(self):
        self.target_dark += 0.5

    def lighten(self):
        self.target_dark -= 0.5

    def darken_ui(self):
        self.darken_ui_background = 1

    def lighten_ui(self):
        self.darken_ui_background = -3

    def pan_away(self):
        self.focus_right = not self.focus_right
        self.move_camera()

    def pan_back(self):
        self.focus_exp()
        self.move_camera()

    def focus_exp(self):
        # Handle exp
        if self.attacker.team == 'player':
            self.focus_right = (self.attacker is self.right)
        elif self.defender.team == 'player':
            self.focus_right = (self.defender is self.right)

    def move_camera(self):
        if self.focus_right and self.pan_offset != -self.pan_max:
            self.pan_dir = -self.pan_move
        elif not self.focus_right and self.pan_offset != self.pan_max:
            self.pan_dir = self.pan_move

    def draw(self, surf):
        platform_trans = 88
        platform_top = 88
        if self.darken_background or self.target_dark:
            bg = image_mods.make_translucent(SPRITES.get('bg_black'), 1 - self.darken_background)
            surf.blit(bg, (0, 0))
            if self.target_dark > self.darken_background:
                self.darken_background += 0.125
            elif self.target_dark < self.darken_background:
                self.darken_background -= 0.125
        # Pan
        if self.pan_dir != 0:
            self.pan_offset += self.pan_dir
            if self.pan_offset > self.pan_max:
                self.pan_offset = self.pan_max
                self.pan_dir = 0
            elif self.pan_offset < -self.pan_max:
                self.pan_offset = -self.pan_max
                self.pan_dir = 0

        total_shake_x = self.shake_offset[0] + self.platform_shake_offset[0]
        total_shake_y = self.shake_offset[1] + self.platform_shake_offset[1]
        # Platform
        top = platform_top + (platform_trans - self.bar_offset * platform_trans) + total_shake_y
        if self.at_range:
            surf.blit(self.left_platform, (9 - self.pan_max + total_shake_x + self.pan_offset, top))
            surf.blit(self.right_platform, (131 + self.pan_max + total_shake_x + self.pan_offset, top))
        else:
            surf.blit(self.left_platform, (WINWIDTH // 2 - self.left_platform.get_width() + total_shake_x, top))
            surf.blit(self.right_platform, (WINWIDTH // 2 + total_shake_x, top))
        # Animation
        if self.at_range:
            right_range_offset = 24 + self.pan_max
            left_range_offset = -24 - self.pan_max
        else:
            right_range_offset, left_range_offset = 0, 0

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
        self.animations = [anim for anim in self.animations if not anim.update()]
        for anim in self.animations:
            anim.draw(surf)

        # Proc Icons
        for proc_icon in self.proc_icons:
            proc_icon.update()
            proc_icon.draw(surf)
        self.proc_icons = [proc_icon for proc_icon in self.proc_icons if not proc_icon.done]

        # Damage Numbers
        for damage_num in self.damage_numbers:
            damage_num.update()
            if damage_num.left:
                x_pos = 94 + left_range_offset - total_shake_x + self.pan_offset
            else:
                x_pos = 194 + right_range_offset - total_shake_x + self.pan_offset
            damage_num.draw(surf, (x_pos, 40))
        self.damage_numbers = [d for d in self.damage_numbers if not d.done]

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
        self.draw_stats(left_bar, self.left_stats, (42, 1))
        self.draw_stats(right_bar, self.right_stats, (WINWIDTH // 2 - 3, 1))

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

        if self.darken_ui_background:
            self.darken_ui_background = min(self.darken_ui_background, 4)
            color = 255 - abs(self.darken_ui_background * 24)
            engine.fill(combat_surf, (color, color, color), None, engine.BLEND_RGB_MULT)
            self.darken_ui_background += 1

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
        MapCombat.handle_state_stack()
