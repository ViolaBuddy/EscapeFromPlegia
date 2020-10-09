import os

from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtCore import Qt, QDir, QSettings
from PyQt5.QtGui import QPixmap, QIcon

from app.utilities import str_utils
from app.resources.icons import Icon
from app.resources.resources import RESOURCES
from app.utilities.data import Data
from app.data.database import DB
from app.editor.base_database_gui import ResourceCollectionModel
from app.extensions.custom_gui import DeletionDialog

from app.editor.icon_editor import icon_view

class IconModel(ResourceCollectionModel):
    def __init__(self, data, window):
        super().__init__(data, window)
        self.sub_data = Data()
        for icon in self._data:
            new_icons = icon_view.icon_slice(icon, self.width, self.height)
            for i in new_icons:
                self.sub_data.append(i)

    def rowCount(self, parent=None):
        return len(self.sub_data)
    
    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            item = self.sub_data[index.row()]
            text = item.nid
            return text
        elif role == Qt.DecorationRole:
            item = self.sub_data[index.row()]
            if item.pixmap:
                pixmap = item.pixmap.scaled(max(self.width, 32), max(self.height, 32))
                return QIcon(pixmap)
        return None

    def setData(self, index, value, role):
        if not index.isValid():
            return False
        return True

    def flags(self, index):
        if index.isValid():
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable
        else:
            return Qt.NoItemFlags

    def create_new(self):
        raise NotImplementedError

    def append(self):
        self.create_new()
        view = self.window.view
        # self.dataChanged.emit(self.index(0), self.index(self.rowCount()))
        self.layoutChanged.emit()
        last_index = self.index(self.rowCount() - 1)
        view.setCurrentIndex(last_index)
        self.update_watchers(self.rowCount() - 1)
        return last_index

    def new(self, index):
        item = self.sub_data[index]
        # idx = self._data.index(item.nid)
        # self.create_new()
        # self._data.move_index(len(self._data) - 1, idx + 1)
        # self.layoutChanged.emit()
        # self.update_watchers(self.rowCount() - 1)

    def update_watchers(self, idx):
        pass

    def nid_change_watchers(self, old_nid, new_nid):
        pass

    def do_delete(self, nid):
        self.layoutAboutToBeChanged.emit()
        for i in self._data:
            if i.nid == nid:
                self._data.delete(i)
        for i in self.sub_data._list[:]:
            if i.nid == nid or i.parent_nid == nid:
                self.sub_data.delete(i)
        self.layoutChanged.emit()

class Icon16Model(IconModel):
    database = RESOURCES.icons16
    width, height = 16, 16

    def create_new(self):
        settings = QSettings("rainlash", "Lex Talionis")
        starting_path = str(settings.value("last_open_path", QDir.currentPath()))
        fns, ok = QFileDialog.getOpenFileNames(self.window, "Choose %s", starting_path, "PNG Files (*.png);;All Files(*)")
        if ok:
            for fn in fns:
                if fn.endswith('.png'):
                    nid = os.path.split(fn)[-1][:-4]  # Get rid of .png ending
                    pix = QPixmap(fn)
                    if pix.width() % self.width == 0 and pix.height() % self.height == 0:
                        nid = str_utils.get_next_name(nid, [d.nid for d in self.database])
                        icon = Icon(nid, fn)
                        icon.pixmap = pix
                        self._data.append(icon)
                        new_icons = icon_view.icon_slice(icon, self.width, self.height)
                        for i in new_icons:
                            self.sub_data.append(i)
                    else:
                        QMessageBox.critical(self.window, "File Size Error!", "Icon width and height must be exactly divisible by %dx%d pixels!" % (self.width, self.height))
                else:
                    QMessageBox.critical(self.window, "File Type Error!", "Icon must be PNG format!")
            parent_dir = os.path.split(fns[-1])[0]
            settings.setValue("last_open_path", parent_dir)
            self.window.update_list()

    def delete(self, index):
        icon = self.sub_data[index.row()]
        if icon.parent_nid:
            # Are you sure you want to delete all ?
            nid = icon.parent_nid
        else:
            nid = icon.nid
        # What uses 16x16 icons
        # Items, Weapons, (Later on Affinities, Skills/Statuses)
        affected_items = [item for item in DB.items if item.icon_nid == nid]
        affected_weapons = [weapon for weapon in DB.weapons if weapon.icon_nid == nid]
        if affected_items or affected_weapons:
            if affected_items:
                affected = Data(affected_items)
                from app.editor.item_database import ItemModel
                model = ItemModel
            elif affected_weapons:
                affected = Data(affected_weapons)
                from app.editor.weapon_database import WeaponModel
                model = WeaponModel
            msg = "Deleting Icon <b>%s</b> would affect these objects."
            ok = DeletionDialog.inform(affected, model, msg, self.window)
            if ok:
                pass
            else:
                return

        self.do_delete(nid)

    def nid_change_watchers(self, old_nid, new_nid):
        # What uses 16x16 icons
        # Items, Weapons, (Later on Affinities, Skills/Statuses)
        for item in DB.items:
            if item.icon_nid == old_nid:
                item.icon_nid = new_nid
        for weapon in DB.weapons:
            if weapon.icon_nid == old_nid:
                weapon.icon_nid = new_nid

class Icon32Model(Icon16Model):
    database = RESOURCES.icons32
    width, height = 32, 32

    def delete(self, index):
        icon = self.sub_data[index.row()]
        if icon.parent_nid:
            # Are you sure you want to delete all ?
            nid = icon.parent_nid
        else:
            nid = icon.nid
        # What uses 32x32 icons
        # Factions
        affected_factions = [faction for faction in DB.factions if faction.icon_nid == nid]
        if affected_factions:
            affected = Data(affected_factions)
            from app.editor.faction_database import FactionModel
            model = FactionModel
            msg = "Deleting Icon <b>%s</b> would affect these factions."
            ok = DeletionDialog.inform(affected, model, msg, self.window)
            if ok:
                pass
            else:
                return
        
        self.do_delete(nid)

    def nid_change_watchers(self, old_nid, new_nid):
        # What uses 32x32 icons
        # Factions
        for faction in DB.factions:
            if faction.icon_nid == old_nid:
                faction.icon_nid = new_nid

class Icon80Model(Icon16Model):
    database = RESOURCES.icons80
    width, height = 80, 72

    def delete(self, index):
        icon = self.sub_data[index.row()]
        if icon.parent_nid:
            # Are you sure you want to delete all ?
            nid = icon.parent_nid
        else:
            nid = icon.nid
        # What uses 80x72 icons
        # Classes
        affected_classes = [klass for klass in DB.classes if klass.icon_nid == nid]
        if affected_classes:
            affected = Data(affected_classes)
            from app.editor.class_database import ClassModel
            model = ClassModel
            msg = "Deleting Icon <b>%s</b> would affect these classes."
            ok = DeletionDialog.inform(affected, model, msg, self.window)
            if ok:
                pass
            else:
                return
        
        self.do_delete(nid)

    def nid_change_watchers(self, old_nid, new_nid):
        # What uses 80x72 icons
        # Classes
        for klass in DB.classes:
            if klass.icon_nid == old_nid:
                klass.icon_nid = new_nid