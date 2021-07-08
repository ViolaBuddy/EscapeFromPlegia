from enum import Enum
from typing import List
from app.utilities.data import Prefab

class Tags(Enum):
    FLOW_CONTROL = 'Flow Control'
    MUSIC_SOUND = 'Music/Sound'
    PORTRAIT = 'Portrait'
    BG_FG = 'Background/Foreground'
    DIALOGUE_TEXT = 'Dialogue/Text'
    CURSOR_CAMERA = 'Cursor/Camera'
    LEVEL_VARS = 'Level-wide Unlocks and Variables'
    GAME_VARS = 'Game-wide Unlocks and Variables'
    TILEMAP = 'Tilemap'
    REGION = 'Region'
    ADD_REMOVE_INTERACT_WITH_UNITS = 'Add/Remove/Interact with Units'
    MODIFY_UNIT_PROPERTIES = 'Modify Unit Properties'
    MODIFY_ITEM_PROPERTIES = 'Modify Item Properties'
    UNIT_GROUPS = 'Unit Groups'
    MISCELLANEOUS = 'Miscellaneous'
    HIDDEN = 'Hidden'

class EventCommand(Prefab):
    nid: str = None
    nickname: str = None
    tag: Tags = Tags.HIDDEN
    desc: str = ''

    keywords: list = []
    optional_keywords: list = []
    flags: list = []

    values: list = []
    display_values: list = []

    def __init__(self, values: List[str] = None, disp_values: List[str] = None):
        self.values: List[str] = values or []
        self.display_values: List[str] = disp_values or values or []

    def save(self):
        # Don't bother saving display values if they are identical
        if self.display_values == self.values:
            return self.nid, self.values
        else:
            return self.nid, self.values, self.display_values

    def to_plain_text(self) -> str:
        if self.display_values:
            return ';'.join([self.nid] + self.display_values)
        else:
            return ';'.join([self.nid] + self.values)

    def __repr__(self):
        return self.to_plain_text()

class Comment(EventCommand):
    nid = "comment"
    nickname = '#'
    tag = Tags.FLOW_CONTROL
    desc = \
        """
**Lines** starting with '#' will be ignored.
        """
    def to_plain_text(self) -> str:
        if self.values and not self.values[0].startswith('#'):
            self.values[0] = '#' + self.values[0]
        return self.values[0]

class If(EventCommand):
    nid = "if"
    tag = Tags.FLOW_CONTROL
    desc = \
        """
If the _Condition_ returns true, the block under this command will be executed. If it returns false, the script will search for the next **elif**, **else**, or **end** command before proceeding. If it is not a valid Python expression, the result will be treated as false.

Remember to end your **if** blocks with **end**.

The indentation is not required, but is recommended for organization of the conditional blocks.

Example:

```
if;game.check_dead('Eirika')
    lose_game
elif;game.check_dead('Lyon')
    win_game
else
    u;Eirika
    s;Eirika;Nice!
    r;Eirika
end
```
        """

    keywords = ['Condition']

class Elif(EventCommand):
    nid = "elif"
    tag = Tags.FLOW_CONTROL
    desc = \
        """
Works exactly like the **if** statement, but is called only if the previous **if** or **elif** returned false.

In the following example, the **elif** will only be processed if `if;game.check_dead('Eirika')` return false.

Example:

```
if;game.check_dead('Eirika')
    lose_game
elif;game.check_dead('Lyon')
    win_game
else
    u;Eirika
    s;Eirika;Nice!
    r;Eirika
end
```
        """

    keywords = ['Condition']

class Else(EventCommand):
    nid = "else"
    tag = Tags.FLOW_CONTROL
    desc = \
        """
Defines a block to be executed only if the previous **if** or **elif** returned false.

Example:

```
if;game.check_dead('Eirika')
    lose_game
elif;game.check_dead('Lyon')
    win_game
else
    u;Eirika
    s;Eirika;Nice!
    r;Eirika
end
```
        """

class End(EventCommand):
    nid = "end"
    tag = Tags.FLOW_CONTROL
    desc = \
        """
Ends a conditional block. Refer to the **if** command for more information.
        """

class Break(EventCommand):
    nid = "break"
    tag = Tags.FLOW_CONTROL
    desc = \
        """
Immediately ends the current event.
        """


class Wait(EventCommand):
    nid = "wait"
    tag = Tags.FLOW_CONTROL
    desc = \
        """
Pauses the execution of the script for _Time_ milliseconds.

Often used after a scene transition, cursor movement, or reinforcements to give the player a chance to take in the scene.
        """

    keywords = ['Time']

class EndSkip(EventCommand):
    nid = "end_skip"
    tag = Tags.FLOW_CONTROL
    desc = \
        """
If the player was skipping through the event script, stop the skip here. Used to prevent a single skip from skipping through an entire event.
        """

class Music(EventCommand):
    nid = "music"
    nickname = "m"
    tag = Tags.MUSIC_SOUND
    desc = \
        """
Fades in _Music_ over the course of _Time_ milliseconds. Fade in defaults to 400 milliseconds.
        """

    keywords = ['Music']
    optional_keywords = ['Time']  # How long to fade in (default 400)

class MusicClear(EventCommand):
    nid = "music_clear"
    tag = Tags.MUSIC_SOUND

    desc = \
        """
Fades out the currently playing song over the course of _Time_ milliseconds. Also clears the entire song stack. Fade out defaults to 400 milliseconds.
        """

    optional_keywords = ['Time']  # How long to fade out

class Sound(EventCommand):
    nid = "sound"
    tag = Tags.MUSIC_SOUND

    desc = \
        """
Plays the _Sound_ once.
        """

    keywords = ['Sound']

class ChangeMusic(EventCommand):
    nid = 'change_music'
    tag = Tags.MUSIC_SOUND

    desc = \
        """
Changes the phase theme music. For instance, you could use this command to change the player phase theme halfway through the chapter.
        """

    keywords = ['PhaseMusic', 'Music']

class AddPortrait(EventCommand):
    nid = "add_portrait"
    nickname = "u"
    tag = Tags.PORTRAIT

    desc = \
        """
Adds a portrait to the screen.

Extra flags:

1. _mirror_: Portrait will face opposite expected direction.
2. _low_priority_: Portrait will appear behind all other portraits on the screen.
3. _immediate_: Portrait will not fade in.
4. _no_block_: Portrait will fade in, but will not pause execution of event script while doing so.
        """

    keywords = ['Portrait', 'ScreenPosition']
    optional_keywords = ['Slide', 'ExpressionList']
    flags = ["mirror", "low_priority", "immediate", "no_block"]

class MultiAddPortrait(EventCommand):
    nid = "multi_add_portrait"
    nickname = "uu"
    tag = Tags.PORTRAIT

    desc = \
        """
Adds more than one portrait to the screen at the same time. Accepts 2-4 portraits and their associated _ScreenPosition_ as input.
        """

    keywords = ['Portrait', 'ScreenPosition', 'Portrait', 'ScreenPosition']
    optional_keywords = ['Portrait', 'ScreenPosition', 'Portrait', 'ScreenPosition']

class RemovePortrait(EventCommand):
    nid = "remove_portrait"
    nickname = "r"
    tag = Tags.PORTRAIT

    keywords = ['Portrait']
    flags = ["immediate", "no_block"]

class MultiRemovePortrait(EventCommand):
    nid = "multi_remove_portrait"
    nickname = "rr"
    tag = Tags.PORTRAIT

    keywords = ['Portrait', 'Portrait']
    optional_keywords = ['Portrait', 'Portrait']

class MovePortrait(EventCommand):
    nid = "move_portrait"
    tag = Tags.PORTRAIT

    keywords = ['Portrait', 'ScreenPosition']
    flags = ["immediate", "no_block"]

class BopPortrait(EventCommand):
    nid = "bop_portrait"
    nickname = "bop"
    tag = Tags.PORTRAIT

    keywords = ['Portrait']
    flags = ["no_block"]

class Expression(EventCommand):
    nid = "expression"
    nickname = "e"
    tag = Tags.PORTRAIT

    keywords = ['Portrait', 'ExpressionList']

class Speak(EventCommand):
    nid = "speak"
    nickname = "s"
    tag = Tags.DIALOGUE_TEXT

    keywords = ['Speaker', 'Text']
    optional_keywords = ['ScreenPosition', 'Width', 'DialogVariant']
    flags = ['low_priority']

class Transition(EventCommand):
    nid = "transition"
    nickname = "t"
    tag = Tags.BG_FG

    optional_keywords = ['Direction', 'Speed', 'Color3']

class Background(EventCommand):
    # Also does remove background
    nid = "change_background"
    nickname = "b"
    tag = Tags.BG_FG

    optional_keywords = ['Panorama']
    flags = ["keep_portraits"]

class DispCursor(EventCommand):
    nid = "disp_cursor"
    tag = Tags.CURSOR_CAMERA

    keywords = ["Bool"]

class MoveCursor(EventCommand):
    nid = "move_cursor"
    nickname = "set_cursor"
    tag = Tags.CURSOR_CAMERA

    keywords = ["Position"]
    flags = ["immediate"]

class CenterCursor(EventCommand):
    nid = "center_cursor"
    tag = Tags.CURSOR_CAMERA

    keywords = ["Position"]
    flags = ["immediate"]

class FlickerCursor(EventCommand):
    nid = 'flicker_cursor'
    nickname = 'highlight'
    tag = Tags.CURSOR_CAMERA

    keywords = ["Position"]
    flags = ["immediate"]

class GameVar(EventCommand):
    nid = 'game_var'
    tag = Tags.GAME_VARS

    keywords = ["Nid", "Condition"]

class IncGameVar(EventCommand):
    nid = 'inc_game_var'
    tag = Tags.GAME_VARS

    keywords = ["Nid"]
    optional_keywords = ["Condition"]

class LevelVar(EventCommand):
    nid = 'level_var'
    tag = Tags.LEVEL_VARS

    keywords = ["Nid", "Condition"]

class IncLevelVar(EventCommand):
    nid = 'inc_level_var'
    tag = Tags.LEVEL_VARS

    keywords = ["Nid"]
    optional_keywords = ["Condition"]

class WinGame(EventCommand):
    nid = 'win_game'
    tag = Tags.LEVEL_VARS

class LoseGame(EventCommand):
    nid = 'lose_game'
    tag = Tags.LEVEL_VARS

class ActivateTurnwheel(EventCommand):
    nid = 'activate_turnwheel'
    tag = Tags.MISCELLANEOUS

    # Whether to force the player to move the turnwheel back
    # defaults to true
    optional_keywords = ['Bool']

class BattleSave(EventCommand):
    nid = 'battle_save'
    tag = Tags.MISCELLANEOUS

class ChangeTilemap(EventCommand):
    nid = 'change_tilemap'
    tag = Tags.TILEMAP

    keywords = ["Tilemap"]
    # How much to offset placed units by
    # Which tilemap to load the unit positions from
    optional_keywords = ["PositionOffset", "Tilemap"]
    flags = ["reload"]  # Should place units in previously recorded positions

class LoadUnit(EventCommand):
    nid = 'load_unit'
    tag = Tags.ADD_REMOVE_INTERACT_WITH_UNITS

    keywords = ["UniqueUnit"]
    optional_keywords = ["Team", "AI"]

class MakeGeneric(EventCommand):
    nid = 'make_generic'
    tag = Tags.ADD_REMOVE_INTERACT_WITH_UNITS

    # Nid, class, level, team, ai, faction, anim variant
    keywords = ["String", "Klass", "String", "Team"]
    optional_keywords = ["AI", "Faction", "String", "ItemList"]

class CreateUnit(EventCommand):
    nid = 'create_unit'
    tag = Tags.ADD_REMOVE_INTERACT_WITH_UNITS
    # Unit template and new unit nid (can be '')
    keywords = ["Unit", "String"]
    # Unit level, position, entrytype, placement
    optional_keywords = ["String", "Position", "EntryType", "Placement"]

class AddUnit(EventCommand):
    nid = 'add_unit'
    nickname = 'add'
    tag = Tags.ADD_REMOVE_INTERACT_WITH_UNITS

    keywords = ["Unit"]
    optional_keywords = ["Position", "EntryType", "Placement"]

class MoveUnit(EventCommand):
    nid = 'move_unit'
    nickname = 'move'
    tag = Tags.ADD_REMOVE_INTERACT_WITH_UNITS

    keywords = ["Unit"]
    optional_keywords = ["Position", "MovementType", "Placement"]
    flags = ['no_block', 'no_follow']

class RemoveUnit(EventCommand):
    nid = 'remove_unit'
    nickname = 'remove'
    tag = Tags.ADD_REMOVE_INTERACT_WITH_UNITS

    keywords = ["Unit"]
    optional_keywords = ["RemoveType"]

class KillUnit(EventCommand):
    nid = 'kill_unit'
    nickname = 'kill'
    tag = Tags.ADD_REMOVE_INTERACT_WITH_UNITS

    keywords = ["Unit"]
    flags = ['immediate']

class RemoveAllUnits(EventCommand):
    nid = 'remove_all_units'
    tag = Tags.ADD_REMOVE_INTERACT_WITH_UNITS

class RemoveAllEnemies(EventCommand):
    nid = 'remove_all_enemies'
    tag = Tags.ADD_REMOVE_INTERACT_WITH_UNITS

class InteractUnit(EventCommand):
    nid = 'interact_unit'
    nickname = 'interact'
    tag = Tags.ADD_REMOVE_INTERACT_WITH_UNITS

    keywords = ["Unit", "Unit"]
    optional_keywords = ["CombatScript", "Ability"]

class SetCurrentHP(EventCommand):
    nid = 'set_current_hp'
    tag = Tags.MODIFY_UNIT_PROPERTIES
    keywords = ["Unit", "PositiveInteger"]

class SetCurrentMana(EventCommand):
    nid = 'set_current_mana'
    tag = Tags.MODIFY_UNIT_PROPERTIES
    keywords = ["Unit", "PositiveInteger"]

class Resurrect(EventCommand):
    nid = 'resurrect'
    tag = Tags.ADD_REMOVE_INTERACT_WITH_UNITS
    keywords = ["GlobalUnit"]

class Reset(EventCommand):
    nid = 'reset'
    tag = Tags.MODIFY_UNIT_PROPERTIES
    keywords = ["Unit"]

class HasAttacked(EventCommand):
    nid = 'has_attacked'
    tag = Tags.MODIFY_UNIT_PROPERTIES
    keywords = ["Unit"]

class HasTraded(EventCommand):
    nid = 'has_traded'
    tag = Tags.MODIFY_UNIT_PROPERTIES
    keywords = ['Unit']

class AddGroup(EventCommand):
    nid = 'add_group'
    tag = Tags.UNIT_GROUPS

    keywords = ["Group"]
    optional_keywords = ["StartingGroup", "EntryType", "Placement"]
    flags = ["create"]

class SpawnGroup(EventCommand):
    nid = 'spawn_group'
    tag = Tags.UNIT_GROUPS

    keywords = ["Group", "CardinalDirection", "StartingGroup"]
    optional_keywords = ["EntryType", "Placement"]
    flags = ["create", "no_block", 'no_follow']

class MoveGroup(EventCommand):
    nid = 'move_group'
    nickname = 'morph_group'
    tag = Tags.UNIT_GROUPS

    keywords = ["Group", "StartingGroup"]
    optional_keywords = ["MovementType", "Placement"]
    flags = ['no_block', 'no_follow']

class RemoveGroup(EventCommand):
    nid = 'remove_group'
    tag = Tags.UNIT_GROUPS

    keywords = ["Group"]
    optional_keywords = ["RemoveType"]

class GiveItem(EventCommand):
    nid = 'give_item'
    tag = Tags.MODIFY_UNIT_PROPERTIES

    keywords = ["GlobalUnit", "Item"]
    flags = ['no_banner', 'no_choice', 'droppable']

class RemoveItem(EventCommand):
    nid = 'remove_item'
    tag = Tags.MODIFY_UNIT_PROPERTIES

    keywords = ["GlobalUnit", "Item"]
    flags = ['no_banner']

class ChangeItemName(EventCommand):
    nid = 'change_item_name'
    tag = Tags.MODIFY_ITEM_PROPERTIES

    keywords = ["GlobalUnit", "Item", "String"]

class ChangeItemDesc(EventCommand):
    nid = 'change_item_desc'
    tag = Tags.MODIFY_ITEM_PROPERTIES

    keywords = ["GlobalUnit", "Item", "String"]

class AddItemToMultiItem(EventCommand):
    nid = 'add_item_to_multiitem'
    tag = Tags.MODIFY_ITEM_PROPERTIES

    keywords = ["GlobalUnit", "Item", "Item"]

class RemoveItemFromMultiItem(EventCommand):
    nid = 'remove_item_from_multiitem'
    tag = Tags.MODIFY_ITEM_PROPERTIES

    keywords = ["GlobalUnit", "Item", "Item"]

class GiveMoney(EventCommand):
    nid = 'give_money'
    tag = Tags.GAME_VARS

    keywords = ["Integer"]
    optional_keywords = ["Party"]
    flags = ['no_banner']

class GiveBexp(EventCommand):
    nid = 'give_bexp'
    tag = Tags.GAME_VARS

    keywords = ["Condition"]
    optional_keywords = ["Party", "String"]
    flags = ['no_banner']

class GiveExp(EventCommand):
    nid = 'give_exp'
    tag = Tags.MODIFY_UNIT_PROPERTIES

    keywords = ["GlobalUnit", "PositiveInteger"]

class SetExp(EventCommand):
    nid = 'set_exp'
    tag = Tags.MODIFY_UNIT_PROPERTIES

    keywords = ["GlobalUnit", "PositiveInteger"]

class GiveWexp(EventCommand):
    nid = 'give_wexp'
    tag = Tags.MODIFY_UNIT_PROPERTIES

    keywords = ["GlobalUnit", "WeaponType", "Integer"]
    flags = ['no_banner']

class GiveSkill(EventCommand):
    nid = 'give_skill'
    tag = Tags.MODIFY_UNIT_PROPERTIES

    keywords = ["GlobalUnit", "Skill"]
    flags = ['no_banner']

class RemoveSkill(EventCommand):
    nid = 'remove_skill'
    tag = Tags.MODIFY_UNIT_PROPERTIES

    keywords = ["GlobalUnit", "Skill"]
    flags = ['no_banner']

class ChangeAI(EventCommand):
    nid = 'change_ai'
    tag = Tags.MODIFY_UNIT_PROPERTIES

    keywords = ["GlobalUnit", "AI"]

class ChangeParty(EventCommand):
    nid = 'change_party'
    tag = Tags.MODIFY_UNIT_PROPERTIES

    keywords = ["GlobalUnit", "Party"]

class ChangeTeam(EventCommand):
    nid = 'change_team'
    tag = Tags.MODIFY_UNIT_PROPERTIES
    keywords = ["GlobalUnit", "Team"]

class ChangePortrait(EventCommand):
    nid = 'change_portrait'
    tag = Tags.MODIFY_UNIT_PROPERTIES
    keywords = ["GlobalUnit", "PortraitNid"]

class ChangeStats(EventCommand):
    nid = 'change_stats'
    tag = Tags.MODIFY_UNIT_PROPERTIES
    keywords = ["GlobalUnit", "StatList"]
    flags = ['immediate']

class SetStats(EventCommand):
    nid = 'set_stats'
    tag = Tags.MODIFY_UNIT_PROPERTIES
    keywords = ["GlobalUnit", "StatList"]
    flags = ['immediate']

class AutolevelTo(EventCommand):
    nid = 'autolevel_to'
    tag = Tags.MODIFY_UNIT_PROPERTIES
    # Second argument is level that is eval'd
    keywords = ["GlobalUnit", "String"]
    # Whether to actually change the unit's level
    flags = ["hidden"]

class SetModeAutolevels(EventCommand):
    nid = 'set_mode_autolevels'
    tag = Tags.GAME_VARS
    keywords = ["String"]
    # Whether to actually change the unit's level
    flags = ["hidden"]

class Promote(EventCommand):
    nid = 'promote'
    tag = Tags.MODIFY_UNIT_PROPERTIES
    keywords = ["GlobalUnit"]
    optional_keywords = ["Klass"]

class ChangeClass(EventCommand):
    nid = 'change_class'
    tag = Tags.MODIFY_UNIT_PROPERTIES
    keywords = ["GlobalUnit"]
    optional_keywords = ["Klass"]

class AddTag(EventCommand):
    nid = 'add_tag'
    tag = Tags.MODIFY_UNIT_PROPERTIES

    keywords = ["GlobalUnit", "Tag"]

class RemoveTag(EventCommand):
    nid = 'remove_tag'
    tag = Tags.MODIFY_UNIT_PROPERTIES

    keywords = ["GlobalUnit", "Tag"]

class AddTalk(EventCommand):
    nid = 'add_talk'
    tag = Tags.LEVEL_VARS

    keywords = ["Unit", "Unit"]

class RemoveTalk(EventCommand):
    nid = 'remove_talk'
    tag = Tags.LEVEL_VARS

    keywords = ["Unit", "Unit"]

class AddLore(EventCommand):
    nid = 'add_lore'
    nickname = 'unlock_lore'
    tag = Tags.GAME_VARS

    keywords = ["Lore"]

class RemoveLore(EventCommand):
    nid = 'remove_lore'
    tag = Tags.GAME_VARS

    keywords = ["Lore"]

class AddBaseConvo(EventCommand):
    nid = 'add_base_convo'
    tag = Tags.LEVEL_VARS

    keywords = ["String"]

class IgnoreBaseConvo(EventCommand):
    nid = 'ignore_base_convo'
    tag = Tags.LEVEL_VARS

    keywords = ["String"]

class RemoveBaseConvo(EventCommand):
    nid = 'remove_base_convo'
    tag = Tags.LEVEL_VARS

    keywords = ["String"]

class IncrementSupportPoints(EventCommand):
    nid = 'increment_support_points'
    tag = Tags.MODIFY_UNIT_PROPERTIES

    keywords = ['GlobalUnit', 'GlobalUnit', 'PositiveInteger']

class UnlockSupportRank(EventCommand):
    nid = 'unlock_support_rank'
    tag = Tags.MODIFY_UNIT_PROPERTIES

    keywords = ['GlobalUnit', 'GlobalUnit', 'SupportRank']

class AddMarketItem(EventCommand):
    nid = 'add_market_item'
    tag = Tags.GAME_VARS

    keywords = ["Item"]

class RemoveMarketItem(EventCommand):
    nid = 'remove_market_item'
    tag = Tags.GAME_VARS

    keywords = ["Item"]

class AddRegion(EventCommand):
    nid = 'add_region'
    tag = Tags.REGION

    keywords = ["Nid", "Position", "Size", "RegionType"]
    optional_keywords = ["String"]
    flags = ["only_once"]

class RegionCondition(EventCommand):
    nid = 'region_condition'
    tag = Tags.REGION

    keywords = ["Nid", "Condition"]

class RemoveRegion(EventCommand):
    nid = 'remove_region'
    tag = Tags.REGION

    keywords = ["Nid"]

class ShowLayer(EventCommand):
    nid = 'show_layer'
    tag = Tags.TILEMAP

    keywords = ["Layer"]
    optional_keywords = ["LayerTransition"]

class HideLayer(EventCommand):
    nid = 'hide_layer'
    tag = Tags.TILEMAP

    keywords = ["Layer"]
    optional_keywords = ["LayerTransition"]

class AddWeather(EventCommand):
    nid = 'add_weather'
    tag = Tags.TILEMAP

    keywords = ["Weather"]

class RemoveWeather(EventCommand):
    nid = 'remove_weather'
    tag = Tags.TILEMAP

    keywords = ["Weather"]

class ChangeObjectiveSimple(EventCommand):
    nid = 'change_objective_simple'
    tag = Tags.LEVEL_VARS

    keywords = ["String"]

class ChangeObjectiveWin(EventCommand):
    nid = 'change_objective_win'
    tag = Tags.LEVEL_VARS

    keywords = ["String"]

class ChangeObjectiveLoss(EventCommand):
    nid = 'change_objective_loss'
    tag = Tags.LEVEL_VARS

    keywords = ["String"]

class SetPosition(EventCommand):
    nid = 'set_position'
    tag = Tags.MISCELLANEOUS

    keywords = ["String"]

class MapAnim(EventCommand):
    nid = 'map_anim'
    tag = Tags.TILEMAP

    keywords = ["MapAnim", "Position"]
    flags = ["no_block"]

class MergeParties(EventCommand):
    nid = 'merge_parties'
    tag = Tags.MISCELLANEOUS
    # Merges the second party onto the first party
    # The second will still exist, but will have no money, bexp, 
    # items in convoy, or units associated with it
    # The first will gain all of those properties

    keywords = ["Party", "Party"]

class ArrangeFormation(EventCommand):
    nid = 'arrange_formation'
    tag = Tags.MISCELLANEOUS
    # Puts units on formation tiles automatically

class Prep(EventCommand):
    nid = 'prep'
    tag = Tags.MISCELLANEOUS

    optional_keywords = ["Bool", "Music"]  # Pick units

class Base(EventCommand):
    nid = 'base'
    tag = Tags.MISCELLANEOUS

    keywords = ["Panorama"]
    optional_keywords = ["Music"]

class Shop(EventCommand):
    nid = 'shop'
    tag = Tags.MISCELLANEOUS

    keywords = ["Unit", "ItemList"]
    optional_keywords = ["ShopFlavor"]

class Choice(EventCommand):
    nid = 'choice'
    tag = Tags.MISCELLANEOUS

    keywords = ['Nid', 'String', 'StringList']
    optional_keywords = ['Orientation']

class ChapterTitle(EventCommand):
    nid = 'chapter_title'
    tag = Tags.MISCELLANEOUS

    optional_keywords = ["Music", "String"]

class Alert(EventCommand):
    nid = 'alert'
    tag = Tags.DIALOGUE_TEXT

    keywords = ["String"]

class VictoryScreen(EventCommand):
    nid = 'victory_screen'
    tag = Tags.MISCELLANEOUS

class RecordsScreen(EventCommand):
    nid = 'records_screen'
    tag = Tags.MISCELLANEOUS

class LocationCard(EventCommand):
    nid = 'location_card'
    tag = Tags.DIALOGUE_TEXT

    keywords = ["String"]

class Credits(EventCommand):
    nid = 'credits'
    tag = Tags.DIALOGUE_TEXT

    keywords = ["String", "String"]
    flags = ['wait', 'center', 'no_split']

class Ending(EventCommand):
    nid = 'ending'
    tag = Tags.DIALOGUE_TEXT

    keywords = ["Portrait", "String", "String"]

class PopDialog(EventCommand):
    nid = 'pop_dialog'
    tag = Tags.DIALOGUE_TEXT
    desc = \
        """
Removes the most recent dialog text box from the screen. Generally only used in conjunction with the `ending` command to remove the Ending box during a transition.

Example:

```
ending;Coyote;Coyote, Man of Mystery;Too mysterious for words.
transition;Close
pop_dialog
transition;Open
```
        """

class Unlock(EventCommand):
    nid = 'unlock'
    tag = Tags.REGION

    keywords = ["Unit"]

class FindUnlock(EventCommand):
    nid = 'find_unlock'
    tag = Tags.HIDDEN

    keywords = ["Unit"]

class SpendUnlock(EventCommand):
    nid = 'spend_unlock'
    tag = Tags.HIDDEN

    keywords = ["Unit"]

class TriggerScript(EventCommand):
    nid = 'trigger_script'
    tag = Tags.MISCELLANEOUS

    keywords = ["Event"]
    optional_keywords = ["GlobalUnit", "GlobalUnit"]

class ChangeRoaming(EventCommand):
    nid = 'change_roaming'
    tag = Tags.MISCELLANEOUS
    desc = "Turn free roam mode on or off"

    keywords = ["Bool"]

class ChangeRoamingUnit(EventCommand):
    nid = 'change_roaming_unit'
    tag = Tags.MISCELLANEOUS
    desc = "Changes the level's current roaming unit."

    keywords = ["Unit"]

class CleanUpRoaming(EventCommand):
    nid = 'clean_up_roaming'
    tag = Tags.MISCELLANEOUS
    desc = "Removes all units other than the roaming unit"

    keywords = []

class AddToInitiative(EventCommand):
    nid = 'add_to_initiative'
    tag = Tags.MISCELLANEOUS
    desc = "Adds the specified unit to the specified point in the initiative order. 0 is the current initiative position."

    keywords = ["Unit", "Integer"]

class MoveInInitiative(EventCommand):
    nid = 'move_in_initiative'
    tag = Tags.MISCELLANEOUS
    desc = "Moves the initiative of the specified unit."

    keywords = ["Unit", "Integer"]

def get_commands():
    return EventCommand.__subclasses__()

def restore_command(dat):
    if len(dat) == 2:
        nid, values = dat
        display_values = None
    elif len(dat) == 3:
        nid, values, display_values = dat
    subclasses = EventCommand.__subclasses__()
    for command in subclasses:
        if command.nid == nid:
            copy = command(values, display_values)
            return copy
    print("Couldn't restore event command!")
    print(nid, values, display_values)
    return Comment([nid + ';' + str.join(';', display_values)])

def parse_text(text):
    if text.startswith('#'):
        return Comment([text])
    arguments = text.split(';')
    command_nid = arguments[0]
    subclasses = EventCommand.__subclasses__()
    for command in subclasses:
        if command.nid == command_nid or command.nickname == command_nid:
            cmd_args = arguments[1:]
            true_cmd_args = []
            command_info = command()
            for idx, arg in enumerate(cmd_args):
                if idx < len(command_info.keywords):
                    cmd_keyword = command_info.keywords[idx]
                elif idx - len(command_info.keywords) < len(command_info.optional_keywords):
                    cmd_keyword = command_info.optional_keywords[idx - len(command_info.keywords)]
                else:
                    cmd_keyword = "N/A"
                # if parentheses exists, then they contain the "true" arg, with everything outside parens essentially as comments
                if '(' in arg and ')' in arg and not cmd_keyword == 'Condition':
                    true_arg = arg[arg.find("(")+1:arg.find(")")]
                    true_cmd_args.append(true_arg)
                else:
                    true_cmd_args.append(arg)
            copy = command(true_cmd_args, cmd_args)
            return copy
    return Comment([text])

def parse(command):
    values = command.values
    num_keywords = len(command.keywords)
    true_values = values[:num_keywords]
    flags = {v for v in values[num_keywords:] if v in command.flags}
    optional_keywords = [v for v in values[num_keywords:] if v not in flags]
    true_values += optional_keywords
    return true_values, flags
