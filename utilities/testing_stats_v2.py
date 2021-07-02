import math
from dataclasses import dataclass

@dataclass
class Character():
    name: str = ''
    LVL: int = 1
    HP: int = 1
    POW: int = 0
    SKL: int = 0
    SPD: int = 0
    BRV: int = 0
    DEF: int = 0

@dataclass
class Growths():
    name: str = ''
    HP: float = 0
    POW: float = 0
    SKL: float = 0
    SPD: float = 0
    BRV: float = 0
    DEF: float = 0

def create_char(char: Character, growths: Growths, lvl: int):
    new_char = Character(char.name, lvl)
    increase = lvl - char.LVL
    offset = 50 if increase > 0 else -50
    new_char.HP = char.HP + int((growths.HP * increase + offset) / 100)
    new_char.POW = char.POW + int((growths.POW * increase + offset) / 100)
    new_char.SKL = char.SKL + int((growths.SKL * increase + offset) / 100)
    new_char.SPD = char.SPD + int((growths.SPD * increase + offset) / 100)
    new_char.BRV = char.BRV + int((growths.BRV * increase + offset) / 100)
    new_char.DEF = char.DEF + int((growths.DEF * increase + offset) / 100)
    return new_char

myrm = Character('Myrmidon', 5, 21, 13, 17, 12, 11, 3)
fighter = Character('Fighter', 5, 31, 22, 10, 5, 7, 5)
knight = Character('Knight', 5, 26, 17, 16, 2, 2, 11)
merc = Character('Mercenary', 5, 28, 16, 18, 7, 8, 4)
cavalier = Character('Cavalier', 5, 25, 16, 13, 7, 6, 5)
peg_knight = Character('Peg Knight', 5, 19, 12, 15, 12, 10, 2)
wyvern_knight = Character('Wyvern', 5, 29, 20, 12, 4, 6, 9)
thief = Character('Thief', 5, 19, 11, 14, 13, 7, 1)
soldier = Character('Soldier', 5, 22, 16, 17, 3, 1, 5)
brigand = Character('Brigand', 5, 32, 20, 8, 4, 9, 1)
lord = Character('Lord', 5, 27, 15, 15, 9, 9, 4)

myrm_growths = Growths('Myrmidon', 105, 50, 70, 65, 55, 25)
fighter_growths = Growths('Fighter', 150, 70, 40, 40, 45, 40)
knight_growths = Growths('Knight', 120, 60, 75, 30, 25, 55)
merc_growths = Growths('Mercenary', 135, 55, 65, 55, 60, 30)
cav_growths = Growths('Cavalier', 115, 60, 70, 45, 40, 45)
peg_growths = Growths('Peg Knight', 90, 40, 55, 75, 70, 20)
wyvern_growths = Growths('Wyvern', 140, 65, 50, 40, 50, 50)
thief_growths = Growths('Thief', 95, 35, 50, 80, 35, 25)
soldier_growths = Growths('Soldier', 110, 60, 70, 35, 25, 45)
brigand_growths = Growths('Brigand', 160, 65, 30, 40, 55, 25)
lord_growths = Growths('Lord', 125, 55, 65, 55, 65, 45)

for stat, growth in [(myrm, myrm_growths), (fighter, fighter_growths), (knight, knight_growths),
                     (merc, merc_growths), (cavalier, cav_growths), (peg_knight, peg_growths),
                     (wyvern_knight, wyvern_growths), (thief, thief_growths), (soldier, soldier_growths),
                     (brigand, brigand_growths), (lord, lord_growths)]:
    c1 = create_char(stat, growth, 1)
    c5 = create_char(stat, growth, 5)
    c10 = create_char(stat, growth, 10)
    c20 = create_char(stat, growth, 20)
    c30 = create_char(stat, growth, 30)
    print(c1)
    print(c5)
    print(c10)
    print(c20)
    print(c30)

myrm20 = create_char(myrm, myrm_growths, 10)
fighter20 = create_char(fighter, fighter_growths, 10)
knight20 = create_char(knight, knight_growths, 10)
lord20 = create_char(lord, lord_growths, 10)

swordmaster30 = Character('Swordmaster', 30, 47, 29, 36, 34, 29, 11)
warrior30 = Character('Warrior', 30, 68, 39, 23, 20, 24, 16)
general30 = Character('General', 30, 56, 34, 36, 12, 14, 24)

def arena(u1, u2):
    mt1 = max(1, u1.POW - u2.DEF)
    mt2 = max(1, u2.POW - u1.DEF)
    hit1 = u1.SKL*4 + 50 - u2.SPD*4 - 10
    hit2 = u2.SKL*4 + 50 - u1.SPD*4 - 10
    as1 = u1.BRV > u2.SPD
    as2 = u2.BRV > u1.SPD

    print("%s: HP: %d Mt: %d Hit: %d Double: %s" % (u1.name, u1.HP, mt1, hit1, as1))
    print("%s: HP: %d Mt: %d Hit: %d Double: %s" % (u2.name, u2.HP, mt2, hit2, as2))
    min_num_rounds_to_ko1 = math.ceil(u2.HP / mt1 / (1.5 if as1 else 1)) if hit1 > 0 else 99
    min_num_rounds_to_ko2 = math.ceil(u1.HP / mt2 / (1.5 if as2 else 1)) if hit2 > 0 else 99
    avg_num_rounds_to_ko1 = math.ceil(u2.HP / (mt1 * min(1, hit1/100)) / (1.5 if as1 else 1)) if hit1 > 0 else 99
    avg_num_rounds_to_ko2 = math.ceil(u1.HP / (mt2 * min(1, hit2/100)) / (1.5 if as2 else 1)) if hit2 > 0 else 99
    print("%s KOs %s in %d rounds (min: %d rounds)" % (u1.name, u2.name, avg_num_rounds_to_ko1, min_num_rounds_to_ko1))
    print("%s KOs %s in %d rounds (min: %d rounds)" % (u2.name, u1.name, avg_num_rounds_to_ko2, min_num_rounds_to_ko2))

"""
arena(myrm, fighter)
print("")
arena(myrm, knight)
print("")
arena(fighter, knight)
print("")
arena(myrm20, fighter20)
print("")
arena(myrm20, knight20)
print("")
arena(fighter20, knight20)
print("")
arena(swordmaster30, warrior30)
print("")
arena(swordmaster30, general30)
print("")
arena(warrior30, general30)
print("")
arena(fighter, merc)
print("")
arena(myrm, myrm)
print("")
arena(fighter, fighter)
print("")
arena(knight, knight)
"""
import itertools
comb = [myrm, knight, fighter, merc, cavalier, peg_knight, wyvern_knight, thief, soldier, brigand, lord]
comb = [myrm, knight, fighter]
comb = [lord20, knight20, fighter20]
# comb = []
for pair in itertools.combinations(comb, 2):
    print("")
    arena(*pair)
