import os

from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtCore import Qt, QDir, QSettings
from PyQt5.QtGui import QPixmap, QIcon

from app.resources.animations import Animation
from app.resources.resources import RESOURCES

from app.utilities.data import Data
from app.data.database import DB
from app.data import item_components

from app.extensions.custom_gui import DeletionDialog

from app.editor.base_database_gui import ResourceCollectionModel

from app.utilities import str_utils

class AnimationModel(ResourceCollectionModel):
    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            animation = self._data[index.row()]
            text = animation.nid
            return text
        elif role == Qt.DecorationRole:
            animation = self._data[index.row()]
            pixmap = animation.pixmap
            width = pixmap.width() // animation.frame_x
            height = pixmap.height() // animation.frame_y
            median_frame = animation.num_frames // 2
            left = (median_frame % animation.frame_x) * width
            top = (median_frame // animation.frame_x) * height

            middle_frame = pixmap.copy(left, top, width, height)
            return QIcon(middle_frame)
        return None

    def create_new(self):
        settings = QSettings("rainlash", "Lex Talionis")
        starting_path = str(settings.value("last_open_path", QDir.currentPath()))
        fns, ok = QFileDialog.getOpenFileNames(self.window, "Select Animation PNG", starting_path, "PNG Files (*.png);;All Files(*)")
        if ok:
            for fn in fns:
                if fn.endswith('.png'):
                    nid = os.path.split(fn)[-1][:-4]
                    pix = QPixmap(fn)
                    nid = str_utils.get_next_name(nid, [d.nid for d in RESOURCES.animations])
                    new_animation = Animation(nid, fn, pix)
                    RESOURCES.animations.append(new_animation)
                else:
                    QMessageBox.critical(self.window, "File Type Error!", "Map Animation must be PNG format!")
            parent_dir = os.path.split(fns[-1])[0]
            settings.setValue("last_open_path", parent_dir)

    def delete(self, idx):
        # Check to see what is using me?
        res = self._data[idx]
        nid = res.nid
        affected_items = item_components.get_items_using(item_components.Type.MapAnimation, nid, DB)
        if affected_items:
            affected = Data(affected_items)
            from app.editor.item_database import ItemModel
            model = ItemModel
            msg = "Deleting Map Animation <b>%s</b> would affect these items."
            ok = DeletionDialog.inform(affected, model, msg, self.window)
            if ok:
                pass
            else:
                return
        super().delete(idx)

    def nid_change_watchers(self, animation, old_nid, new_nid):
        # What uses Animations
        # Certain item components
        affected_items = item_components.get_items_using(item_components.Type.MapAnimations, old_nid, DB)
        item_components.swap_values(affected_items, item_components.Type.MapAnimations, old_nid, new_nid)