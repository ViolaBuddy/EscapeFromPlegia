from app.utilities.data import Prefab

class EventCommand(Prefab):
    nid: str = None
    nickname: str = None
    tag: str = 'general'

    keywords: list = []
    optional_keywords: list = []
    flags: list = []

    values: list = []

    def __init__(self, values=None):
        self.values = values or []

    def save(self):
        return self.nid, self.values

    def to_plain_text(self):
        return ';'.join([self.nid] + self.values)

class Comment(EventCommand):
    nid = "comment"
    nickname = '#'
    tag = None

    def to_plain_text(self):
        return self.values[0]

class If(EventCommand):
    nid = "if"
    tag = "flow"

    keywords = ['Condition']

class Elif(EventCommand):
    nid = "elif"
    tag = "flow"

    keywords = ['Condition']

class Else(EventCommand):
    nid = "else"
    tag = "flow"

class End(EventCommand):
    nid = "end"
    tag = "flow"

class Wait(EventCommand):
    nid = "wait"
    tag = "general"

    keywords = ['Time']

class EndSkip(EventCommand):
    nid = "end_skip"
    tag = "general"

class Music(EventCommand):
    nid = "music"
    nickname = "m"
    tag = "sound"

    keywords = ['Music']

class Sound(EventCommand):
    nid = "sound"
    tag = "sound"

    keywords = ['Sound']

class AddPortrait(EventCommand):
    nid = "add_portrait"
    nickname = "u"
    tag = "dialogue"

    keywords = ['Portrait', 'ScreenPosition']
    optional_keywords = ['Slide', 'ExpressionList']
    flags = ["mirror", "low_priority", "immediate", "no_block"]

class RemovePortrait(EventCommand):
    nid = "remove_portrait"
    nickname = "r"
    tag = "dialogue"

    keywords = ['Portrait']
    flags = ["immediate", "no_block"]

class MovePortrait(EventCommand):
    nid = "move_portrait"
    tag = "dialogue"

    keywords = ['Portrait', 'ScreenPosition']
    flags = ["immediate", "no_block"]

class BopPortrait(EventCommand):
    nid = "bop_portrait"
    nickname = "bop"
    tag = "dialogue"

    keywords = ['Portrait']
    flags = ["no_block"]

class Expression(EventCommand):
    nid = "expression"
    nickname = "e"
    tag = "dialogue"

    keywords = ['Portrait', 'ExpressionList']

class Speak(EventCommand):
    nid = "speak"
    nickname = "s"
    tag = "dialogue"

    keywords = ['Speaker', 'Text']
    optional_keywords = ['ScreenPosition', 'Width']

class Transition(EventCommand):
    nid = "transition"
    nickname = "t"
    tag = "background"

    optional_keywords = ['Direction', 'Speed', 'Color3']

class Background(EventCommand):
    # Also does remove background
    nid = "change_background"
    nickname = "b"
    tag = "background"

    optional_keywords = ['Panorama']
    flags = ["keep_portraits"]

class DispCursor(EventCommand):
    nid = "disp_cursor"
    tag = "cursor"
    keywords = ["Bool"]

class MoveCursor(EventCommand):
    nid = "move_cursor"
    nickname = "set_cursor"
    tag = "cursor"
    
    keywords = ["Position"]
    flags = ["immediate"]

class GameVar(EventCommand):
    nid = 'game_var'
    tag = 'general'

    keywords = ["Nid", "Condition"]

class LevelVar(EventCommand):
    nid = 'level_var'
    tag = 'general'

    keywords = ["Nid", "Condition"]

class WinGame(EventCommand):
    nid = 'win_game'
    tag = "general"

class LoseGame(EventCommand):
    nid = 'lose_game'
    tag = "general"

class AddUnit(EventCommand):
    nid = 'add_unit'
    nickname = 'add'
    tag = 'unit'

    keywords = ["Unit"]
    optional_keywords = ["Position", "EntryType", "Placement"]

class MoveUnit(EventCommand):
    nid = 'move_unit'
    nickname = 'move'
    tag = 'unit'

    keywords = ["Unit"]
    optional_keywords = ["Position", "MovementType", "Placement"]
    flags = ['no_block']

class RemoveUnit(EventCommand):
    nid = 'remove_unit'
    nickname = 'remove'
    tag = 'unit'

    keywords = ["Unit"]
    optional_keywords = ["RemoveType"]

class InteractUnit(EventCommand):
    nid = 'interact_unit'
    nickname = 'interact'
    tag = 'unit'

    keywords = ["Unit", "Unit"]
    optional_keywords = ["CombatScript", "Ability"]

class SetCurrentHP(EventCommand):
    nid = 'set_current_hp'
    tag = 'unit'
    keywords = ["Unit", "PositiveInteger"]

class AddGroup(EventCommand):
    nid = 'add_group'
    tag = 'unit'

    keywords = ["Group"]
    optional_keywords = ["EntryType", "Placement"]

class CreateGroup(EventCommand):
    nid = 'create_group'
    tag = 'unit'

    keywords = ["Group"]
    optional_keywords = ["EntryType", "Placement"]

class MorphGroup(EventCommand):
    nid = 'morph_group'
    nickname = 'move_group'
    tag = 'unit'

    keywords = ["StartingGroup", "StartingGroup"]
    optional_keywords = ["MovementType", "Placement", "Group"]
    flags = ['no_block']

class RemoveGroup(EventCommand):
    nid = 'remove_group'
    tag = 'unit'

    keywords = ["Group"]
    optional_keywords = ["RemoveType"]

class GiveItem(EventCommand):
    nid = 'give_item'
    tag = 'unit'
    
    keywords = ["GlobalUnit", "Item"]
    flags = ['no_banner']

class GiveExp(EventCommand):
    nid = 'give_exp'
    tag = 'unit'

    keywords = ["GlobalUnit", "PositiveInteger"]

class ChangeAI(EventCommand):
    nid = 'change_ai'
    tag = 'unit'

    keywords = ["GlobalUnit", "AI"] 

class AddTalk(EventCommand):
    nid = 'add_talk'
    tag = 'unit'

    keywords = ["Unit", "Unit"]

class RemoveTalk(EventCommand):
    nid = 'remove_talk'
    tag = 'unit'

    keywords = ["Unit", "Unit"]

class AddRegion(EventCommand):
    nid = 'add_region'
    tag = 'general'

    keywords = ["Nid", "Position", "Size", "RegionType"]
    optional_keywords = ["String"]
    flags = ["only_once"]

class RegionCondition(EventCommand):
    nid = 'region_condition'
    tag = 'general'

    keywords = ["Nid", "Condition"]

class RemoveRegion(EventCommand):
    nid = 'remove_region'
    tag = 'general'

    keywords = ["Nid"]

class Prep(EventCommand):
    nid = 'prep'
    tag = 'general'

    optional_keywords = ["Bool"]

class Shop(EventCommand):
    nid = 'shop'
    tag = 'general'

    keywords = ["ItemList"]
    optional_keywords = ["ShopFlavor"]  

class ChapterTitle(EventCommand):
    nid = 'chapter_title'
    tag = 'general'

    optional_keywords = ["Music", "String"]

def get_commands():
    return EventCommand.__subclasses__()

def restore_command(dat):
    nid, values = dat
    subclasses = EventCommand.__subclasses__()
    for command in subclasses:
        if command.nid == nid:
            copy = command(values)
            return copy
    return None

def parse_text(text):
    if text.startswith('#'):
        return Comment([text])
    arguments = text.split(';')
    command_nid = arguments[0]
    subclasses = EventCommand.__subclasses__()
    for command in subclasses:
        if command.nid == command_nid or command.nickname == command_nid:
            copy = command(arguments[1:])
            return copy
    return None

def parse(command):
    values = command.values
    num_keywords = len(command.keywords)
    true_values = values[:num_keywords]
    flags = {v for v in values[num_keywords:] if v in command.flags}
    optional_keywords = [v for v in values[num_keywords:] if v not in flags]
    true_values += optional_keywords
    return true_values, flags
