import math

from app.data.constants import WINWIDTH, WINHEIGHT, FRAMERATE
from app.data.database import DB

from app.engine import engine, image_mods, icons, unit_funcs, action
from app.engine.sprites import SPRITES
from app.engine.fonts import FONT
from app.engine.state import State
from app.engine.state_machine import SimpleStateMachine
from app.engine.game_state import game

class ExpState(State):
    name = 'exp'
    transparent = True

    def start(self):
        if 'exp' not in game.memory or game.memory['exp'] is None:
            # Generally can only happen if a player character attacks a player character.
            # Then two 'exp' command will be put on the stack
            # But of the course the second will overwrites the first's memory
            # So we'll just ignore the first
            game.state.back()
            return 'repeat'

        self.unit, self.exp_gain, self.combat_object, self.starting_state = \
            game.memory['exp']
        game.memory['exp'] = None

        self.old_exp = self.unit.exp
        self.old_level = self.unit.level

        self.state = SimpleStateMachine(self.starting_state)
        self.start_time = engine.get_time()

        self.exp_bar = None
        self.level_up_animation = None
        self.level_up_screen = None

        self.total_time_for_exp = self.exp_gain * FRAMERATE  # 1 frame per exp

        self.stat_changes = None

        self.unit_klass = DB.classes.get(self.unit.klass)
        if self.unit.level >= self.unit_klass.max_level and not self.unit_klass.turns_into:
            # We're done here
            game.state.back()
            return 'repeat'

    def begin(self):
        game.cursor.hide()

    def create_level_up_logo(self):
        pass
        # TODO Animation for Level Up logo

    def update(self):
        super().update()
        current_time = engine.get_time()

        # Initiating State
        if self.state.get_state() == 'init':
            self.exp_bar = ExpBar(self.old_exp, center=not self.combat_object)
            self.start_time = current_time
            self.state.change('exp_wait')

        # Wait before starting to increment exp
        elif self.state.get_state() == 'exp_wait':
            self.exp_bar.update(self.old_exp)
            if current_time - self.start_time > 400:
                self.state.change('exp0')
                self.start_time = current_time
                # GC.SOUNDDICT['Experience Gain'].play(-1)

        # Increment exp until done or 100 exp is reached
        elif self.state.get_state() == 'exp0':
            progress = (current_time - self.start_time)/float(self.total_time_for_exp)
            exp_set = self.old_exp + progress * self.exp_gain
            exp_set = int(min(self.old_exp + self.exp_gain, exp_set))
            self.exp_bar.update(exp_set)

            # transition
            # if exp_set >= self.old_exp + self.exp_gain:
            #     GC.SOUNDDICT['Experience Gain'].stop()

            if exp_set >= 100:
                max_level = self.unit_klass.max_level
                if self.unit.level >= max_level:  # Do I promote?
                    # GC.SOUNDDICT['Experience Gain'].stop()
                    if DB.constants.get('auto_promote').value and \
                            self.unit_klass.turns_into and \
                            'NoAutoPromote' not in self.unit.tags:
                        self.exp_bar.update(100)
                        # GC.SOUNDDICT['Level Up'].play()
                    else:
                        self.exp_bar.update(99)
                    self.state.clear()
                    self.state.change('prepare_promote')
                    self.state.change('exp_leave')
                    self.exp_bar.fade_out()
                    self.start_time = current_time
                else:
                    self.state.change('exp100')

            elif current_time - self.start_time >= self.total_time_for_exp + 500:
                self.state.clear()
                self.state.change('exp_leave')
                self.exp_bar.fade_out()
                self.start_time = current_time

        elif self.state.get_state() == 'exp_leave':
            done = self.exp_bar.update()
            if done:
                action.do(action.GainExp(self.unit, self.exp_gain))
                self.state.back()
                self.start_time = current_time
                # If we're ready to leave
                if len(self.state.state) <= 0:
                    game.state.back()
                # Otherwise, we're probably about to level up!

        elif self.state.get_state() == 'exp100':
            progress = (current_time - self.start_time)/float(self.total_time_for_exp)
            exp_set = self.old_exp + (self.exp_gain * progress) - 100
            exp_set = int(min(self.old_exp + self.exp_gain - 100, exp_set))
            self.exp_bar.update(exp_set)

            # if exp_set >= self.old_exp + self.exp_gain - 100:
            #     GC.SOUNDDICT['Experience Gain'].stop()

            # Extra time to account for pause at end
            if current_time - self.start_time >= self.total_time_for_exp + 500:
                self.stat_changes = unit_funcs.get_next_level_up(self.unit)
                action.do(action.IncLevel(self.unit))
                action.do(action.ApplyLevelUp(self.unit, self.stat_changes))
                self.create_level_up_logo()
                self.state.clear()
                self.state.change('level_up')
                self.state.change('exp_leave')
                self.exp_bar.fade_out()
                self.start_time = current_time

        elif self.state.get_state() == 'level_up':
            # if not self.level_up_sound_played:
            #     GC.SOUNDDICT['Level Up'].play()
            #     self.level_up_sound_played = True

            if self.level_up_animation.update():
                if self.combat_object:
                    self.combat_object.darken_ui()
                self.state.change('level_screen')
                self.start_time = current_time

        elif self.state.get_state() == 'level_screen':
            if not self.level_up_screen:
                self.level_up_screen = LevelUpScreen(
                    self.unit, self.start_changes, self.old_level, self.unit.level)
            if self.level_up_screen.update(current_time):
                game.state.back()
                if self.combat_object:
                    self.combat_object.lighten_ui()
                # check for weapon experience gain
                # if self.new_wexp:
                #     action.do(action.GainWexp(self.unit, self.new_wexp))

                # check for skill gain unless the unit is using a booster to
                # get to this screen
                # TODO Implement with skills
                """
                if self.starting_state != "booster":
                    self.unit_klass = DB.classes.get(self.unit.klass)
                    for level_needed, class_skill in self.unit_klass.learned_skills:
                        if self.unit.level == level_needed:
                            if class_skill == 'Feat':
                                game.cursor.cur_unit = self.unit
                                game.state.change('feat_choice')
                            else:
                                skill = StatusCatalog.statusparser(class_skill, gameStateObj)
                                # If we don't already have this skill
                                if skill.stack or skill.id not in (s.id for s in self.unit.status_effects):
                                    Action.do(Action.AddStatus(self.unit, skill), gameStateObj)
                                    gameStateObj.banners.append(Banner.gainedSkillBanner(self.unit, skill))
                                    gameStateObj.stateMachine.change('itemgain')
                """

        # Wait 100 ms before transferring to the promotion state
        elif self.state.get_state() == 'prepare_promote':
            self.exp_bar.update()
            if current_time - self.start_time > 100:
                class_options = self.unit_klass.turns_into
                if DB.constants.get('auto_promote').value and class_options and \
                        'NoAutoPromote' not in self.unit.tags:
                    self.exp_bar.update(0)
                    if len(class_options) > 1:
                        game.cursor.cur_unit = self.unit
                        game.state.change('promotion_choice')
                        game.state.change('transition_out')
                        # We are leaving
                        self.state.clear()
                        self.state.change('wait')
                        self.start_time = current_time
                    elif len(class_options) == 1:
                        game.cursor.cur_unit = self.unit
                        game.memory['next_class'] = class_options[0]
                        game.state.change('promotion')
                        game.state.change('transition_out')  # We are leaving
                        self.state.clear()
                        self.state.change('wait')
                        self.start_time = current_time
                    else:
                        action.do(action.SetExp(self.unit, 99))
                        game.state.back()
                else:
                    action.do(action.SetExp(self.unit, 99))
                    game.state.back()

        elif self.state.get_state() == 'promote':
            # TODO for Promotion

            old_anim = self.unit.battle_anim
            """
            promote_action = Action.Promote(self.unit, self.unit.new_klass)
            self.levelup_list, self.new_wexp = promote_action.get_data()
            Action.do(promote_action, gameStateObj)

            if self.combat_object:
                self.combat_object.darken_ui()
                if old_anim:
                    self.combat_object.update_battle_anim(old_anim)

            self.state.clear()
            self.state.change('level_screen')
            self.start_time = current_time
            """

        elif self.state.get_state() == 'item_promote':
            class_options = self.unit_klass.turns_into
            if len(class_options) > 1:
                game.cursor.cur_unit = self.unit
                game.state.change('promotion_choice')
                game.state.change('transition_out')  # We are leaving
                self.state.clear()
                self.state.change('wait')
                self.start_time = current_time
            elif len(class_options) == 1:
                game.cursor.cur_unit = self.unit
                game.memory['next_class'] = class_options[0]
                game.state.change('promotion')
                game.state.change('transition_out')  # We are leaving
                self.state.clear()
                self.state.change('wait')
                self.start_time = current_time

        elif self.state.get_state() == 'booster':
            self.stat_changes = game.memory['stat_changes']
            self.exp_gain = 0
            action.do(action.PermanentStatIncrease(self.unit, self.stat_changes))
            self.old_level = self.unit.level
            self.state.change('level_screen')
            self.start_time = current_time

        elif self.state.get_state() == 'wait':
            if current_time - self.start_time > 1000:  # Wait a while
                game.state.back()

    def draw(self, surf):
        # surf = engine.create_surface((WINWIDTH, WINHEIGHT), transparent=True)

        if self.state.get_state() in ('init', 'exp_wait', 'exp_leave', 'exp0', 'exp100', 'prepare_promote'):
            if self.exp_bar:
                self.exp_bar.draw(surf)

        elif self.state.get_state() == 'level_up':
            pass

        elif self.state.get_state() == 'level_screen':
            if self.level_screen:
                self.level_screen.draw(surf)

        return surf

class LevelUpScreen():
    bg = SPRITES.get('level_screen')
    width = bg.get_width()
    height = bg.get_height()

    spark_time = 320
    level_up_wait = 1960

    spark = SPRITES.get('stat_up_spark')
    underline = SPRITES.get('stat_underline')
    uparrow = SPRITES.get('level_up_arrow')
    numbers = SPRITES.get('level_up_numbers')

    def __init__(self, unit, stat_changes, old_level, new_level):
        self.unit = unit
        self.stat_list = [stat_changes.get(nid, 0) for nid in DB.stats.keys()]
        self.stat_list = self.stat_list[:8]  # Can only show first 8 stats on level up
        self.old_level = old_level
        self.new_level = new_level

        self.current_spark = -1

        self.unit_scroll_offset = 80
        self.screen_scroll_offset = self.width + 32
        self.underline_offset = 36

        self.animations = []
        self.arrow_animaitons = []

        self.state = 'scroll_in'
        self.start_time = 0

    def make_spark(self, topleft):
        return None
        # TODO
        # return CustomObjects.Animation(
        #     self.spark, topleft, (11, 1), animation_speed=32,
        #     ignore_map=True)

    def get_position(self, i):
        if i >= 4:
            position = (self.width//2 + 8, (i - 4) * 16 + 35)
        else:
            position = (10, i * 16 + 35)
        return position

    def inc_spark(self):
        self.current_spark += 1
        if self.current_spark >= len(self.stat_list):
            return True
        elif self.stat_list[self.current_spark] == 0:
            return self.inc_spark()
        return False

    def update(self, current_time):
        if self.state == 'scroll_in':
            self.unit_scroll_offset = max(0, self.unit_scroll_offset - 10)
            self.screen_scroll_offset = max(0, self.screen_scroll_offset - 20)
            if self.unit_scroll_offset == 0 and self.screen_scroll_offset == 0:
                self.state = 'init_wait'
                self.start_time = current_time

        elif self.state == 'init_wait':
            if current_time - self.start_time > 320:
                if self.old_level == self.new_level:  # No level up spark
                    self.state = 'get_next_spark'
                else:
                    self.state = 'first_spark'
                    topleft = (87, 27)
                    self.animations.append(self.make_spark(topleft))
                    # GC.SOUNDDICT['Level_Up_Level'].play()                
                self.start_time = current_time

        elif self.state == 'scroll_out':
            self.unit_scroll_offset += 10
            self.screen_scroll_offset += 20
            if current_time - self.start_time > 500:
                return True  # Done

        elif self.state == 'first_spark':
            if current_time - self.start_time > self.spark_time:
                self.state = 'get_next_spark'
                self.start_time = current_time

        elif self.state == 'get_next_spark':
            done = self.inc_spark()
            if done:
                self.state = 'level_up_wait'
                self.start_time = current_time
            else:
                pos = self.get_position(self.current_spark)
                # TODO Animations
                """
                arrow_animation = CustomObjects.Animation(
                    self.uparrow, (pos[0] + 45, pos[1] - 11), (10, 1), animation_speed=32,
                    ignore_map=True, hold=True)
                self.arrow_animations.append(arrow_animation)
                spark_pos = pos[0] + 14, pos[1] + 26
                self.animations.append(self.make_spark(spark_pos))
                increase = Utility.clamp(self.levelup_list[self.current_spark], 1, 7)
                row = Engine.subsurface(self.numbers, (0, (increase - 1)*24, 10*28, 24))
                number_animation = CustomObjects.Animation(
                    row, (pos[0] + 43, pos[1] + 49), (10, 1), animation_speed=32, 
                    ignore_map=True, hold=True)
                number_animation.frameCount = -5  # delay this animation for 5 frames
                self.animations.append(number_animation)
                GC.SOUNDDICT['Stat Up'].play()
                """
                self.underline_offset = 36 # for underline growing
                self.state = 'spark_wait'
                self.start_time = current_time

        elif self.state == 'spark_wait':
            if current_time - self.start_time > self.spark_time:
                self.state = 'get_next_spark'

        elif self.state == 'level_up_wait':
            if current_time - self.start_time > self.level_up_wait:
                self.animations.clear()
                self.state = 'scroll_out'
                self.start_time = current_time

    def draw(self, surf):
        sprite = self.bg.copy()
        # Changes through entire color wheel
        # from t = 0 to t = 1 in
        # 180 * 10 milliseconds
        t = math.sin(math.radians((engine.get_time()//10) % 180))
        new_color = image_mods.blend_colors((88, 16, -40), (-80, -32, 40), t)

        # Render top
        klass = DB.classes.get(self.unit.klass)
        long_name = klass.long_name
        FONT['text_white'].blit(long_name, sprite, (12, 3))
        FONT['text_yellow'].blit('Lv', sprite, (self.width//2 + 12, 3))
        if self.state in ('scroll_in', 'init_wait'):
            level = str(self.old_level)
        else:
            level = str(self.new_level)
        width = FONT['text_blue'].size(level)[0]
        FONT['text_blue'].blit(level, sprite, (self.width//2 + 50 - width, 3))

        # Render underlines
        new_underline_surf = image_mods.change_color(self.underline, new_color)
        for idx, num in enumerate(self.stat_list[:self.current_spark + 1]):
            if num != 0:  # Stat change
                if idx == self.current_spark:
                    rect = (self.underline_offset, 0, 
                            new_underline_surf.get_width() - self.underline_offset, 3)
                    new_underline_surf = engine.subsurface(new_underline_surf, rect)
                    # Change underline offset
                    self.underline_offset = max(0, self.underline_offset - 6)
                    pos = self.get_position(idx)
                    pos = (pos[0] + self.underline_offset//2 + 1, pos[1] + 10)
                else:
                    pos = self.get_position(idx)
                    pos = (pos[0] + 4, pos[1] + 11)
                sprite.blit(new_underline_surf, pos)

        # Update and draw arrow animations
        self.arrow_animations = [a for a in self.arrow_animations if not a.update()]
        for animation in self.arrow_animations:
            animation.draw(sprite, blend=new_color)

        # Draw stats
        for idx, stat in enumerate(DB.stats.keys()):
            pos = self.get_position(idx)
            FONT['text_yellow'].blit(stat, sprite, pos)
            text = self.unit.stats[stat] - (self.stat_list[idx] if self.current_spark < idx else 0)
            width = FONT['text_blue'].size(str(text))[0]
            FONT['text_blue'].blit(str(text), sprite, (pos[0] + 40 - width, pos[1]))

        pos = (6 - self.screen_scroll_offset, WINHEIGHT - 8 - self.height)
        surf.blit(sprite, pos)

        # Blit unit's pic
        right = WINWIDTH - 4
        bottom = WINHEIGHT + self.unit_scroll_offset
        icons.draw_portrait(surf, self.unit.nid, bottomright=(right, bottom))

        # Update and draw animations
        self.animations = [a for a in self.animations if not a.update()]
        for animation in self.animations:
            animation.draw(surf)

        return surf

class ExpBar():
    background = engine.subsurface(SPRITES.get('expbar'), (0, 0, 136, 24))
    begin = engine.subsurface(SPRITES.get('expbar'), (0, 24, 3, 7))
    middle = engine.subsurface(SPRITES.get('expbar'), (3, 24, 1, 7))
    end = engine.subsurface(SPRITES.get('expbar'), (4, 24, 2, 7))
    width = 136
    height = 24

    def __init__(self, old_exp, center=True):
        self.bg_surf = self.create_bg_surf()
        if center:
            self.pos = WINWIDTH//2 - self.width//2, WINHEIGHT//2 - self.height//2
        else:
            self.pos = WINWIDTH//2 - self.width//2, WINHEIGHT - self.height

        self.offset = self.height//2  # Start with fade in
        self.done = False

        self.num = old_exp

    def create_bg_surf(self):
        surf = engine.create_surface((self.width, self.height), transparent=True)
        surf.blit(self.background, (0, 0))
        surf.blit(self.begin, (7, 9))
        return surf

    def fade_out(self):
        self.done = True

    def update(self, exp=None):
        if self.done:
            self.offset += 1  # So fade in and out
            if self.offset >= self.height//2:
                return True
        elif self.offset > 0:
            self.offset -= 1

        if exp is not None:
            self.num = exp

    def draw(self, surf):
        new_surf = engine.copy_surface(self.bg_surf)

        # Blit correct number of sprites for middle of exp bar
        idx = int(max(0, self.num))
        for x in range(idx):
            new_surf.blit(self.middle, (10 + x, 9))

        # Blit end of exp bar
        new_surf.blit(self.end, (10 + idx, 9))

        # Blit current amount of exp
        FONT['number_small3'].blit_right(str(self.num), new_surf, (self.width - 4, 4))

        # Transition
        new_surf = engine.subsurface(new_surf, (0, self.offset, self.width, self.height - self.offset * 2))

        surf.blit(new_surf, (self.pos[0], self.pos[1] + self.offset))
        return surf