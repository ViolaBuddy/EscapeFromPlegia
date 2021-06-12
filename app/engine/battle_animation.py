from app.constants import WINWIDTH, COLORKEY
from app.utilities import utils
from app.resources.resources import RESOURCES
from app.data.database import DB

from app.engine.sprites import SPRITES
from app.engine.sound import SOUNDTHREAD
from app.engine import engine, image_mods, item_system, item_funcs

from app.resources.combat_anims import CombatAnimation, WeaponAnimation, EffectAnimation
from app.resources.combat_palettes import Palette

import logging

battle_anim_speed = 1

class BattleAnimation():
    idle_poses = {'Stand', 'RangedStand', 'TransformStand'}

    def __init__(self, anim_prefab: WeaponAnimation, palette: Palette, unit, item):
        self.anim_prefab = anim_prefab
        self.current_palette = palette
        self.unit = unit
        self.item = item

        self.poses = {pose.nid: pose for pose in anim_prefab.poses}
        self._generate_missing_poses()
        self.current_pose = None

        # Load frames as images
        if not anim_prefab.image:
            # Only do load stuff if image does not exist already
            image_full_path = anim_prefab.full_path
            anim_prefab.image = engine.image_load(image_full_path, convert=True)
            engine.set_colorkey(anim_prefab.image, COLORKEY, rleaccel=True)
            for frame in anim_prefab.frames:
                frame.image = engine.subsurface(anim_prefab.image, frame.rect)

        # Apply palette to frames
        self.apply_palette()

        self.state = 'inert'
        self.in_basic_state: bool = False  # Is animation in a basic state?
        self.processing = False

        self.wait_for_hit: bool = False
        self.script_idx = 0
        self.current_frame = None
        self.under_frame = None
        self.over_frame = None
        self.frame_count = 0
        self.num_frames = 0

        self.loop = None
        self.skip_next_loop = 0  # A counter that keeps track of how many loops in the future to skip

        # Pairing stuff
        self.owner = None
        self.partner_anim = None
        self.parent = self
        self.right = True
        self.at_range = 0
        self.init_position = None
        self.init_speed = 0
        self.entrance = 0

        # Effect stuff
        self.child_effects = []
        self.under_child_effects = []
        self.loop = False

        # For drawing
        self.blend = 0
        # Flash Frames
        self.foreground = None
        self.foreground_counter = 0
        self.background = None
        self.background_counter = 0
        self.flash_color = []  # It's a list so you could have it flash through several colors
        self.flash_counter = 0
        self.flash_image = None
        self.screen_dodge_color = None
        self.screen_dodge_counter = 0
        self.screen_dodge_image = None
        # Opacity
        self.opacity = 255
        self.death_opacity = []
        # Offset
        self.static = False # Animation will always be in the same place on the screen
        self.ignore_pan = False  # Animation will ignore any panning
        self.pan_away = False

        self.lr_offset = []
        self.effect_offset = (0, 0)
        self.personal_offset = (0, 0)

    def _generate_missing_poses(self):
        # Copy Stand -> RangedStand and Dodge -> RangedDodge if missing
        # Copy Attack -> Miss and Attack -> Critical if missing
        if 'RangedStand' not in self.poses and 'Stand' in self.poses:
            self.poses['RangedStand'] = self.poses['Stand']
        if 'RangedDodge' not in self.poses and 'Dodge' in self.poses:
            self.poses['RangedDodge'] = self.poses['Dodge']
        if 'Miss' not in self.poses and 'Attack' in self.poses:
            self.poses['Miss'] = self.poses['Attack']
        if 'Critical' not in self.poses and 'Attack' in self.poses:
            self.poses['Critical'] = self.poses['Attack']

    def apply_palette(self):
        self.image_directory = {}
        colors = self.current_palette.colors
        conversion_dict = {(0, coord[0], coord[1]): (color[0], color[1], color[2]) for coord, color in colors.items()}
        for frame in self.anim_prefab.frames:
            converted_image = image_mods.color_convert(engine.copy_surface(frame.image), conversion_dict)
            self.image_directory[frame.nid] = converted_image

    def pair(self, owner, partner_anim, right, at_range, entrance_frames=0, position=None, parent=None):
        print(self.unit.nid, "pair")
        self.owner = owner
        self.partner_anim = partner_anim
        self.parent = parent if parent else self
        self.right = right
        self.at_range = at_range
        self.entrance_frames = entrance_frames
        self.entrance_counter = entrance_frames
        self.init_position = position
        self.get_stand()
        self.script_idx = 0
        self.current_frame = None
        self.under_frame = None
        self.over_frame = None
        self.reset_frames()

    def get_stand(self):
        if self.at_range:
            self.current_pose = 'RangedStand'
        else:
            self.current_pose = 'Stand'

    def get_frame(self, frame_nid: str):
        return self.anim_prefab.frames.get(frame_nid)

    def start_anim(self, pose):
        print(self.unit.nid, "start anim", pose)
        self.change_pose(pose)
        self.script_idx = 0
        self.wait_for_hit = True
        self.reset_frames()

    def change_pose(self, pose):
        self.current_pose = pose

    def has_pose(self, pose) -> bool:
        return pose in self.poses

    def end_current_pose(self):
        if 'Stand' in self.poses:
            self.get_stand()
            self.state = 'run'
        else:
            self.state = 'inert'
        # Make sure to return to correct pan if we somehow didn't
        if self.pan_away:
            self.pan_away = False
            self.owner.pan_back()
        self.script_idx = 0

    def resume(self):
        if self.state == 'wait':
            self.reset_frames()
        for effect in self.child_effects:
            effect.resume()
        for effect in self.under_child_effects:
            effect.resume()
        self.wait_for_hit = False

    def finish(self):
        self.get_stand()
        self.state = 'leaving'
        self.script_idx = 0

    def reset_frames(self):
        self.state = 'run'
        self.frame_count = 0
        self.num_frames = 0

    def can_proceed(self):
        return self.loop or self.state == 'wait'

    def done(self) -> bool:
        return self.state == 'inert' or (self.state == 'run' and self.current_pose in self.idle_poses)

    def dodge(self):
        if self.at_range:
            self.start_anim('RangedDodge')
        else:
            self.start_anim('Dodge')

    def get_num_frames(self, num) -> int:
        return max(1, int(int(num) * battle_anim_speed))

    def start_dying_animation(self):
        self.state = 'dying'
        self.death_opacity = [0, 20, 20, 20, 20, 44, 44, 44, 44, 64,
                              64, 64, 64, 84, 84, 84, 108, 108, 108, 108, 
                              128, 128, 128, 128, 148, 148, 148, 148, 172, 172, 
                              172, 192, 192, 192, 192, 212, 212, 212, 212, 236,
                              236, 236, 236, 255, 255, 255, 0, 0, 0, 0,
                              0, 0, -1, 0, 0, 0, 0, 0, 0, 255, 
                              0, 0, 0, 0, 0, 0, 255, 0, 0, 0,
                              0, 0, 0, 255, 0, 0, 0, 0, 0, 0,
                              255, 0, 0, 0, 0, 0, 0]

    def wait_for_dying(self):
        if self.in_basic_state:
            self.num_frames = int(42 * battle_anim_speed)

    def flash(self, num_frames: int, color: tuple):
        self.flash_counter = num_frames
        self.flash_color = [color]

    def screen_dodge(self, num_frames, color):
        self.screen_dodge_counter = num_frames
        self.screen_dodge_color = color

    def get_effect(self, effect_nid: str, enemy: bool = False) -> EffectAnimation:
        effect = RESOURCES.combat_effects.get(effect_nid)
        if effect:
            effect_palette_nids = [palette[1] for palette in effect.palettes]
            if self.current_palette.nid in effect_palette_nids:
                palette = self.current_palette
            else:
                first_palette_nid = effect.palettes[0][1]
                palette = RESOURCES.combat_palettes.get(first_palette_nid)
            child_effect = BattleAnimation(effect, palette, self.unit, self.item)
            right = not self.right if enemy else self.right
            parent = self.parent.partner_anim if enemy else self.parent
            child_effect.pair(self.owner, self.partner_anim, right, self.at_range, parent=parent)
            child_effect.start_anim(self.current_pose)
            return child_effect
        return None

    def add_effect(self, effect, pose=None):
        if pose and pose in effect.poses:
            effect.change_pose(pose)
        self.child_effects.append(effect)

    def remmove_effects(self, effects: list):
        for effect in effects:
            if effect in self.child_effects:
                self.child_effects.remove(effect)
            if effect in self.under_child_effects:
                self.under_child_effects.remove(effect)

    def clear_all_effects(self):
        for child in self.child_effects:
            child.clear_all_effects()
        for child in self.under_child_effects:
            child.clear_all_effects()
        self.child_effects.clear()
        self.under_child_effects.clear()

    def effect_playing(self):
        return bool(self.child_effects) or bool(self.under_child_effects)

    def end_loop(self):
        if self.loop:
            if self.loop[1] >= 0:
                self.script_idx = self.loop[1]  # Move to end of loop
            self.loop = None
        else:
            self.skip_next_loop += 1

    def update(self):
        print("Update", self.unit.nid, self.state)
        if self.state == 'run':
            print("Current Pose", self.current_pose)
            # Read script
            if self.frame_count >= self.num_frames:
                self.processing = True
                self.read_script()
            if self.current_pose in self.poses:
                script = self.poses[self.current_pose].timeline
                if self.script_idx >= len(script):
                    # Check whether we should loop or end
                    if self.current_pose in self.idle_poses:
                        self.script_idx = 0  # Loop
                    else:
                        self.end_current_pose()
            else:
                self.end_current_pose()

            self.frame_count += 1
            if self.entrance_counter:
                self.entrance_counter -= 1

        elif self.state == 'dying':
            if self.death_opacity:
                opacity = self.death_opacity.pop()
                if opacity == -1:
                    opacity = 255
                    self.flash_color = [(248, 248, 248)]
                    self.flash_counter = 100
                    SOUNDTHREAD.play_sfx('CombatDeath')
                self.opacity = opacity
            else:
                self.state = 'inert'

        elif self.state == 'leaving':
            self.entrance_counter += 1
            if self.entrance_counter > self.entrance_frames:
                self.entrance_counter = self.entrance_frames
                self.state = 'inert'  # done

        elif self.state == 'wait':
            pass

        # Handle effects
        for child in self.child_effects:
            child.update()
        for child in self.under_child_effects:
            child.update()

        # Remove completed child effects
        self.child_effects = [child for child in self.child_effects if child.state != 'inert']
        self.under_child_effects = [child for child in self.under_child_effects if child.state != 'inert']

    def read_script(self):
        if not self.has_pose(self.current_pose):
            return
        script = self.poses[self.current_pose].timeline
        while self.script_idx < len(script) and self.processing:
            command = script[self.script_idx]
            self.run_command(command)
            self.script_idx += 1

    def run_command(self, command):
        print("Command", command.nid, command.value)
        self.in_basic_state = False

        values = command.value
        if command.nid == 'frame':
            self.frame_count = 0
            self.num_frames = self.get_num_frames(values[0])
            self.current_frame = self.get_frame(values[1])
            self.under_frame = self.over_frame = None
            self.processing = False  # No more processing -- need to wait at least a frame
        elif command.nid == 'over_frame':
            self.frame_count = 0
            self.num_frames = self.get_num_frames(values[0])
            self.over_frame = self.get_frame(values[1])
            self.under_frame = self.current_frame = None
            self.processing = False
        elif command.nid == 'under_frame':
            self.frame_count = 0
            self.num_frames = self.get_num_frames(values[0])
            self.under_frame = self.get_frame(values[1])
            self.over_frame = self.current_frame = None
            self.processing = False
        elif command.nid == 'frame_with_offset':
            self.frame_count = 0
            self.num_frames = self.get_num_frames(values[0])
            self.current_frame = self.get_frame(values[1])
            self.under_frame = self.over_frame = None
            self.processing = False
            self.personal_offset = (int(values[2]), int(values[3]))
        elif command.nid == 'dual_frame':
            self.frame_count = 0
            self.num_frames = self.get_num_frames(values[0])
            self.current_frame = self.get_frame(values[1])
            self.under_frame = self.get_frame(values[1])
            self.over_frame = None
            self.processing = False
        elif command.nid == 'wait':
            self.frame_count = 0
            self.num_frames = self.get_num_frames(values[0])
            self.current_frame = self.over_frame = self.under_frame = None
            self.processing = False  # No more processing -- need to wait at least a frame

        elif command.nid == 'sound':
            SOUNDTHREAD.play_sfx(values[0])
        elif command.nid == 'stop_sound':
            SOUNDTHREAD.stop_sfx(values[0])

        elif command.nid == 'start_hit':
            self.owner.shake()
            self.owner.start_hit()
            if self.partner_anim:  # Also offset partner, since they got hit
                self.partner_anim.lr_offset = [-1, -2, -3, -2, -1]
        elif command.nid == 'wait_for_hit':
            if self.wait_for_hit:
                self.current_frame = self.get_frame(values[0])
                self.under_frame = self.get_frame(values[1])
                self.over_frame = None
                self.processing = False
                self.state = 'wait'
                self.in_basic_state = True
        elif command.nid == 'miss':
            self.owner.start_hit(miss=True)
            if self.partner_anim:
                self.partner_anim.dodge()
        elif command.nid == 'spell_hit':
            self.owner.spell_hit(values[0])
            self.state = 'wait'
            self.processing = False

        elif command.nid == 'effect':
            effect = values[0]
            child_effect = self.get_effect(effect)
            if child_effect:
                self.child_effects.append(child_effect)
        elif command.nid == 'under_effect':
            effect = values[0]
            child_effect = self.get_effect(effect)
            if child_effect:
                self.parent.under_child_effects.append(child_effect)
        elif command.nid == 'enemy_effect':
            effect = values[0]
            child_effect = self.get_effect(effect, enemy=True)
            if child_effect and self.partner_anim:
                self.partner_anim.child_effects.append(child_effect)
        elif command.nid == 'enemy_under_effect':
            effect = values[0]
            child_effect = self.get_effect(effect, enemy=True)
            if child_effect and self.partner_anim:
                self.partner_anim.under_child_effects.append(child_effect)
        elif command.nid == 'clear_all_effects':
            self.clear_all_effects()

        elif command.nid == 'spell':
            if values[0]:
                effect = values[0]
            else:
                effect = self.item.nid
            child_effect = self.get_effect(effect)
            if child_effect:
                self.child_effects.append(child_effect)

        elif command.nid == 'blend':
            if bool(values[0]):
                self.blend = engine.BLEND_RGB_ADD
            else:
                self.blend = 0
        elif command.nid == 'static':
            self.static = bool(values[0])
        elif command.nid == 'ignore_pan':
            self.ignore_pan = bool(values[0])
        elif command.nid == 'opacity':
            self.opacity = int(values[0])
        elif command.nid == 'parent_opacity':
            self.parent.opacity = int(values[0])

        elif command.nid == 'pan':
            self.pan_away = not self.pan_away
            if self.pan_away:
                self.owner.pan_away()
            else:
                self.owner.pan_back()

        elif command.nid == 'self_tint':
            num_frames = self.get_num_frames(values[0])
            color = values[1]
            self.flash(num_frames, color)
        elif command.nid == 'enemy_tint':
            num_frames = self.get_num_frames(values[0])
            color = values[1]
            if self.partner_anim:
                self.partner_anim.flash(num_frames, color)
        elif command.nid == 'self_screen_dodge':
            num_frames = self.get_num_frames(values[0])
            color = values[1]
            self.screen_dodge(num_frames, color)
        elif command.nid == 'enemy_screen_dodge':
            num_frames = self.get_num_frames(values[0])
            color = values[1]
            if self.partner_anim:
                self.partner_anim.screen_dodge(num_frames, color)
        elif command.nid == 'background_blend':
            num_frames = self.get_num_frames(values[0])
            color = values[1]
            self.background_counter = num_frames
            self.background = SPRITES.get('bg_black').copy()
            self.background.fill(color)
        elif command.nid == 'foreground_blend':
            num_frames = self.get_num_frames(values[0])
            color = values[1]
            self.foreground_counter = num_frames
            self.foreground = SPRITES.get('bg_black').copy()
            self.foreground.fill(color)
        elif command.nid == 'screen_blend':
            num_frames = self.get_num_frames(values[0])
            color = values[1]
            self.owner.screen_flash(num_frames, color)

        elif command.nid == 'platform_shake':
            self.owner.platform_shake()
        elif command.nid == 'screen_shake':
            self.owner._shake(1)
        elif command.nid == 'darken':
            self.owner.darken()
        elif command.nid == 'lighten':
            self.owner.lighten()
        elif command.nid == 'hit_spark':
            self.owner.hit_spark()
        elif command.nid == 'crit_spark':
            self.owner.crit_spark()

        elif command.nid == 'start_loop':
            if self.skip_next_loop:
                self.skip_next_loop -= 1
            else:
                self.loop = (self.script_idx, -1)
        elif command.nid == 'end_loop':
            if self.loop:
                self.loop = (self.loop[0], self.script_idx)
                self.script_idx = self.loop[0]  # Re-loop
        elif command.nid == 'end_parent_loop':
            self.parent.end_loop()
        elif command.nid == 'end_child_loop':
            for child in self.child_effects:
                child.end_loop()
            for child in self.under_children:
                child.end_loop()

    def draw(self, surf, shake=(0, 0), range_offset=0, pan_offset=0):
        if self.state == 'inert':
            return

        # Screen flash
        if self.background and not self.blend:
            engine.blit(surf, self.background, (0, 0), None, engine.BLEND_RGB_ADD)

        for child in self.under_child_effects:
            child.draw(surf, (0, 0), range_offset, pan_offset)

        if self.current_frame is not None:
            image, offset = self.get_image(self.current_frame, shake, range_offset, pan_offset, self.static)

            # Move the animations in at the beginnign and out at the end
            if self.entrance_counter:
                progress = (self.entrance_frames - self.entrance_counter) / self.entrance_frames
                new_size = int(progress * image.get_width()), int(progress * image.get_height())
                image = engine.transform_scale(image, new_size)
                if self.flash_color and self.flash_image:
                    self.flash_image = image
                diff_x = offset[0] - self.init_position[0]
                diff_y = offset[1] - self.init_position[1]
                offset = int(self.init_position[0] + progress * diff_x), int(self.init_position[1] + progress * diff_y)

            # Self flash
            image = self.handle_flash(image)

            # Self screen dodge
            image = self.handle_screen_dodge(image)

            if self.opacity != 255:
                if self.blend:
                    image = image_mods.make_translucent_blend(image, 255 - self.opacity)
                else:
                    image = image_mods.make_translucent(image.convert_alpha(), (255 - self.opacity)/255.)

            # Actually blit
            if self.background and self.blend:
                old_bg = self.background.copy()
                engine.blit(old_bg, image, offset)
                engine.blit(surf, old_bg, (0, 0), None, self.blend)
            else:
                engine.blit(surf, image, offset, None, self.blend)

        # Handle children
        for child in self.child_effects:
            child.draw(surf, (0, 0), range_offset, pan_offset)

        # Screen flash
        if self.foreground:
            engine.blit(surf, self.foreground, (0, 0), None, engine.BLEND_RGB_ADD)
            self.foreground_counter -= 1
            if self.foreground_counter <= 0:
                self.foreground = None
                self.foreground_counter = 0

        if self.background:
            # Draw above
            self.background_counter -= 1
            if self.background_counter <= 0:
                self.background = None
                self.background_counter = 0

    def draw_under(self, surf, shake=(0, 0), range_offset=0, pan_offset=0):
        if self.state != 'inert' and self.under_frame is not None:
            image, offset = self.get_image(self.under_frame, shake, range_offset, pan_offset, False)
            engine.blit(surf, image, offset, None, self.blend)

    def draw_over(self, surf, shake=(0, 0), range_offset=0, pan_offset=0):
        if self.state != 'inert' and self.over_frame is not None:
            image, offset = self.get_image(self.over_frame, shake, range_offset, pan_offset, False)
            engine.blit(surf, image, offset, None, self.blend)

    def get_image(self, frame, shake, range_offset, pan_offset, static) -> tuple:
        image = self.image_directory[frame.nid].copy()
        if not self.right:
            image = engine.flip_horiz(image)
        offset = frame.offset
        # Handle offset (placement of the object on the screen)
        if self.lr_offset:
            offset = offset[0] + self.lr_offset.pop(), offset[1]
        if self.effect_offset:
            offset = offset[0] + self.effect_offset[0], offset[1] + self.effect_offset[1]
        if self.personal_offset:
            offset = offset[0] + self.personal_offset[0], offset[1] + self.personal_offset[1]

        left = 0
        if not static:
            left += shake[0] + range_offset
        if self.at_range and not static:
            if self.ignore_pan:
                if self.right:
                    pan_max = range_offset - 24
                else:
                    pan_max = range_offset + 24
                left -= pan_max
            else:
                left += pan_offset

        if self.right:
            offset = offset[0] + shake[0] + left, offset[1] + shake[1]
        else:
            offset = WINWIDTH - offset[0] - image.get_width() + left, offset[1] + shake[1]
        return image, offset

    def handle_flash(self, image):
        if self.flash_color:
            if not self.flash_image:
                flash_color = self.flash_color[self.flash_counter % len(self.flash_color)]
                self.flash_image = image_mods.change_color(image.convert_alpha(), flash_color)
            self.flash_counter -= 1
            image = self.flash_image
            # done
            if self.flash_counter <= 0:
                self.flash_color.clear()
                self.flash_counter = 0
                self.flash_image = None
        return image

    def handle_screen_dodge(self, image):
        if self.screen_dodge_color:
            if not self.screen_dodge_image:
                self.screen_dodge_image = image_mods.screen_dodge(image.convert_alpha(), self.screen_dodge_color)
            self.screen_dodge_counter -= 1
            image = self.screen_dodge_image
            # done
            if self.screen_dodge_color <= 0:
                self.screen_dodge_color = None
                self.screen_dodge_counter = 0
                self.screen_dodge_image = None
        return image

def get_palette(anim_prefab: CombatAnimation, unit) -> Palette:
    palettes = anim_prefab.palettes
    palette_names = [palette[0] for palette in palettes]
    palette_nids = [palette[1] for palette in palettes]
    team_palette = 'Generic%s' % utils.get_team_color(unit.team).capitalize()
    if unit.name in palette_names:
        idx = palette_names.index(unit.name)
        palette_nid = palette_nids[idx]
    elif unit.nid in palette_names:
        idx = palette_names.index(unit.nid)
        palette_nid = palette_nids[idx]
    elif team_palette in palette_names:
        idx = palette_names.index(team_palette)
        palette_nid = palette_nids[idx]
    else:
        palette_nid = palette_nids[0]
    current_palette = RESOURCES.combat_palettes.get(palette_nid)
    return current_palette

def get_battle_anim(unit, item, distance=1) -> BattleAnimation:
    # Find the right combat animation
    class_obj = DB.classes.get(unit.klass)
    combat_anim_nid = class_obj.combat_anim_nid
    if unit.variant:
        combat_anim_nid += unit.variant
    res = RESOURCES.combat_anims.get(combat_anim_nid)
    if not res:  # Try without unit variant
        res = RESOURCES.combat_anims.get(class_obj.combat_anim_nid)
    if not res:
        return None

    # Get the palette
    palette = get_palette(res, unit)
    if not palette:
        logging.warning("Could not find valid palette for %s", unit)
        return None

    # Get the correct weapon anim
    if not item:
        weapon_anim_nid = "Unarmed"
    else:
        weapon_type = item_system.weapon_type(unit, item)
        if not weapon_type:
            weapon_type = "Neutral"
        magic = item_funcs.is_magic(unit, item)
        ranged = item_funcs.is_ranged(unit, item)
        if item.nid in res.weapon_anims.keys():
            weapon_anim_nid = item.nid
            if magic:
                weapon_anim_nid = "Magic" + weapon_anim_nid
            elif ranged and distance > 1:
                weapon_anim_nid = "Ranged" + weapon_anim_nid
        elif magic:
            weapon_anim_nid = "Magic" + weapon_type
        elif ranged and distance > 1:
            weapon_anim_nid = "Ranged" + weapon_type
        else:
            weapon_anim_nid = weapon_type
        if magic and weapon_anim_nid not in res.weapon_anims.keys():
            weapon_anim_nid = 'MagicGeneric'
    weapon_anim = res.weapon_anims.get(weapon_anim_nid)
    if not weapon_anim:
        logging.warning("Could not find valid weapon animation. Trying: %s", weapon_anim_nid)
        return None

    # Check spell effects
    for pose in weapon_anim.poses:
        script = pose.timeline
        for command in script:
            if command.nid == 'spell':
                if command.value[0]:
                    effect = command.value[0]
                else:
                    effect = item.nid
                if effect not in RESOURCES.combat_effects.keys():
                    logging.warning("Could not find spell animation for effect %s in weapon anim %s", effect, weapon_anim_nid)
                    return None

    battle_anim = BattleAnimation(weapon_anim, palette, unit, item)
    return battle_anim
