from PyQt5.QtWidgets import QPushButton
from PyQt5.QtCore import QSize

# Custom Widgets
from app.data.data import Data
from app.data.database import DB

from app.extensions.custom_gui import PropertyBox, ComboBox

class ObjBox(PropertyBox):
    def __init__(self, title, model, database, parent=None, button=False):
        super().__init__(title, ComboBox, parent)
        self.model = model(database, parent)
        self.edit.setModel(self.model)
        if button:
            b = QPushButton('...')
            b.setMaximumWidth(40)
            self.add_button(b)

class UnitBox(ObjBox):
    def __init__(self, parent=None, button=False, exclude=None):
        from app.editor.unit_database import UnitModel
        database = DB.units
        if exclude:
            database = Data([d for d in DB.units if d is not exclude])
        super().__init__("Unit", UnitModel, database, parent, button)
        self.edit.setIconSize(QSize(32, 32))
        self.edit.view().setUniformItemSizes(True)

class ClassBox(ObjBox):
    def __init__(self, parent=None, button=False, exclude=None):
        from app.editor.class_database import ClassModel
        database = DB.classes
        if exclude:
            database = Data([d for d in DB.classes if d is not exclude])
        super().__init__("Class", ClassModel, database, parent, button)
        self.edit.setIconSize(QSize(32, 32))
        self.edit.view().setUniformItemSizes(True)

class FactionBox(ObjBox):
    def __init__(self, parent=None, button=False):
        from app.editor.faction_database import FactionModel
        super().__init__("Faction", FactionModel, DB.factions, parent, button)

class ItemBox(ObjBox):
    def __init__(self, parent=None, button=False, exclude=None):
        from app.editor.item_database import ItemModel
        database = DB.items
        if exclude:
            database = Data([d for d in DB.items if d is not exclude])
        super().__init__("Item", ItemModel, database, parent, button)

class AIBox(ObjBox):
    def __init__(self, parent=None, button=False, exclude=None):
        from app.editor.ai_database import AIModel
        database = DB.ai
        if exclude:
            database = Data([d for d in DB.ai if d is not exclude])
        super().__init__("AI", AIModel, database, parent, button)

class WeaponTypeBox(ObjBox):
    def __init__(self, parent=None, button=False, exclude=None):
        from app.editor.weapon_database import WeaponModel
        database = DB.weapons
        if exclude:
            database = Data([d for d in DB.weapons if d is not exclude])
        super().__init__("Weapon Type", WeaponModel, database, parent, button)

class MovementCostBox(ObjBox):
    def __init__(self, parent=None, button=False):
        from app.editor.mcost_dialog import MovementCostModel
        super().__init__("Movement Cost", MovementCostModel, DB.mcost, parent, button)

class MovementClassBox(ObjBox):
    def __init__(self, parent=None, button=False):
        from app.editor.mcost_dialog import MovementClassModel
        super().__init__("Movement Class", MovementClassModel, DB.mcost, parent, button)
