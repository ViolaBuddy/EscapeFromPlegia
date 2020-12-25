from app.data.database import DB

from app.utilities import utils
from app.engine import item_system, skill_system
from app.engine.objects.item import ItemObject
from app.engine.objects.skill import SkillObject

def is_magic(unit, item) -> bool:
    weapon_type = item_system.weapon_type(unit, item)
    if weapon_type and DB.weapons.get(weapon_type).magic:
        return True
    if item.magic:
        return True
    return False

def available(unit, item) -> bool:
    return item_system.available(unit, item) and skill_system.available(unit, item)

def buy_price(unit, item):
    value = item_system.buy_price(unit, item)
    value *= skill_system.modify_buy_price(unit, item)
    return value

def sell_price(unit, item):
    value = item_system.sell_price(unit, item)
    value *= skill_system.modify_sell_price(unit, item)
    return value

# def can_wield(unit, item) -> bool:
#     weapon = item_system.is_weapon(unit, item)
#     spell = item_system.is_weapon(unit, item)
#     avail = available(unit, item)
#     if (weapon or spell):
#         if avail:
#             return True
#         else:
#             return False
#     return True

def create_items(unit, item_nid_list: list) -> list:
    items = []
    for val in item_nid_list:
        if isinstance(val, tuple) or isinstance(val, list):
            item_nid, droppable = val
        else:
            item_nid = val
            droppable = False
        item_prefab = DB.items.get(item_nid)
        item = ItemObject.from_prefab(item_prefab)
        if unit:
            item.owner_nid = unit.nid
        item.droppable = droppable
        item_system.init(item)
        items.append(item)
    return items

def get_all_items(unit) -> list:
    """
    Use this to get all weapons if you want to be able to handle multi_items
    """
    
    items = []
    for item in unit.items:
        if item.multi_item:
            for subitem in item.multi_item.value:
                items.append(subitem)
        else:
            items.append(item)
    return items

def get_all_tradeable_items(unit) -> list:
    items = []
    for item in unit.items:
        if not item_system.locked(unit, item):
            items.append(item)
    return items

def inventory_full(unit, item) -> bool:
    if item_system.is_accessory(unit, item):
        return len(unit.accessories) >= DB.constants.value('num_accessories')
    else:
        return len(unit.nonaccessories) >= DB.constants.value('num_items')

def get_range(unit, item) -> set:
    min_range, max_range = 0, 0
    for component in item.components:
        if component.defines('minimum_range'):
            min_range = component.minimum_range(unit, item)
            break
    for component in item.components:
        if component.defines('maximum_range'):
            max_range = component.maximum_range(unit, item)
            break

    max_range += skill_system.modify_maximum_range(unit, item)
    limit_max = skill_system.limit_maximum_range(unit, item)
    max_range = utils.clamp(max_range, 0, limit_max)

    return set(range(min_range, max_range + 1))

def get_range_string(unit, item):
    if unit:
        item_range = get_range(unit, item)
        min_range = min(item_range)
        max_range = max(item_range)
    else:
        min_range = item_system.minimum_range(None, item)
        max_range = item_system.maximum_range(None, item)
    if min_range != max_range:
        rng = '%d-%d' % (min_range, max_range)
    else:
        rng = '%d' % max_range
    return rng

# Skill stuff
def create_skills(unit, skill_nid_list: list) -> list:
    skills = []
    for skill_nid in skill_nid_list:
        skill_prefab = DB.skills.get(skill_nid)
        if skill_prefab:
            skill = SkillObject.from_prefab(skill_prefab)
            skill.owner_nid = unit.nid
            skill_system.init(skill)
            skills.append(skill)
        else:
            print("Couldn't find skill %s" % skill_nid)
    return skills
