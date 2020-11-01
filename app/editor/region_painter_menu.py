from PyQt5.QtWidgets import QPushButton, QLineEdit, \
    QWidget, QVBoxLayout, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QColor, QPixmap

from app.utilities import utils, str_utils
from app.utilities.data import Data

from app.extensions.custom_gui import PropertyBox, ComboBox, RightClickListView
from app.editor.base_database_gui import DragDropCollectionModel
from app.editor.custom_widgets import SkillBox

class RegionMenu(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.window = parent
        self.main_editor = self.window
        self.map_view = self.main_editor.map_view
        self.current_level = self.main_editor.current_level
        if self.current_level:
            self._data = self.current_level.regions
        else:
            self._data = Data()

        grid = QVBoxLayout()
        self.setLayout(grid)

        def duplicate_func(model, index):
            return False

        self.view = RightClickListView((None, duplicate_func, None), parent=self)
        self.view.currentChanged = self.on_item_changed

        self.model = RegionModel(self._data, self)
        self.view.setModel(self.model)

        grid.addWidget(self.view)

        self.create_button = QPushButton("Create Region...")
        self.create_button.clicked.connect(self.create_region)
        grid.addWidget(self.create_button)

        self.modify_region_widget = ModifyRegionWidget(self._data, self)
        grid.addWidget(self.modify_region_widget)

        self.last_touched_region = None
        self.display = None

    def on_visibiity_changed(self, state):
        pass

    def tick(self):
        pass

    def set_current_level(self, level):
        self.current_level = level
        self._data = self.current_level.regions
        self.model._data = self._data
        self.model.update()

    def select(self, idx):
        index = self.model.index(idx)
        self.view.setCurrentIndex(index)

    def deselect(self):
        self.view.clearSelection()

    def on_item_changed(self, curr, prev):
        if self._data:
            region = self._data[curr.row()]
            self.map_view.center_on_pos(region.center)
            self.modify_region_widget.set_current(region)

    def get_current(self):
        for index in self.view.selectionModel().selectedIndexes():
            idx = index.row()
            if len(self._data) > 0 and idx < len(self._data):
                return self._data[idx]
        return None

    def create_region(self, example=None):
        created_region = Region.default()
        self._data.append(created_region)
        self.model.update()
        # Select the region
        idx = self._data.index(created_region.nid)
        index = self.model.index(idx)
        self.view.setCurrentIndex(index)
        self.window.update_view()
        return created_region

class RegionModel(DragDropCollectionModel):
    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            region = self._data[index.row()]
            text = region.nid + ': ' + region.region_type
            if region.region_type == 'Status':
                text += ' ' + region.sub_nid
            elif region.region_type == 'Event':
                text += ' ' + region.sub_nid
                text += '\n' + region.condition
            return text
        elif role == Qt.DecorationRole:
            color = utils.hash_to_color(hash(region.nid))
            pixmap = QPixmap(32, 32)
            pixmap.fill(QColor(color))
            return QIcon(pixmap)
        return None

    def new(self, idx):
        ok = self.window.create_region()
        if ok:
            self._data.move_index(len(self._data) - 1, idx + 1)
            self.layoutChanged.emit()

            self.update_watchers(idx + 1)

class ModifyRegionWidget(QWidget):
    def __init__(self, data, parent=None, current=None):
        super().__init__(parent)
        self.window = parent
        self._data = data

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.current = current

        self.nid_box = PropertyBox("Unique ID", QLineEdit, self)
        new_nid = str_utils.get_next_generic_nid(self.current, self._data.keys())
        self.nid_box.edit.setText(new_nid)
        self.nid_box.edit.textChanged.connect(self.nid_changed)
        self.nid_box.edit.editingFinished.connect(self.nid_done_editing)
        layout.addWidget(self.nid_box)

        self.region_type_box = PropertyBox("Region Type", ComboBox, self)
        self.region_type_box.edit.addItems(region.region_types)
        self.region_type_box.edit.setValue(self.current.region_type)
        self.region_type_box.edit.currentIndexChanged.connect(self.region_type_changed)
        layout.addWidget(self.region_type_box)

        self.sub_nid_box = PropertyBox("Event Name", QLineEdit, self)
        if self.current.sub_nid and self.current.region_type == 'Event':
            self.sub_nid_box.edit.setText(self.current.sub_nid)
        self.sub_nid_box.textChanged.connect(self.sub_nid_changed)
        layout.addWidget(self.sub_nid_box)

        self.condition_box = PropertyBox("Condition", QLineEdit, self)
        self.condition_box.edit.setText(self.current.condition)
        self.condition_box.textChanged.connect(self.condition_changed)
        layout.addWidget(self.condition_box)

        self.status_box = SkillBox(self) 
        if self.current.sub_nid and self.current.region_type == 'Status':
            self.status_box.edit.setText(self.current.sub_nid)
        self.status_box.currentIndexChanged.connect(self.status_changed)
        layout.addWidget(self.status_box)

        self.sub_nid_box.hide()
        self.condition_box.hide()
        self.status_box.hide()

    def nid_changed(self, text):
        self.current.nid = text
        self.window.update_list()

    def nid_done_editing(self):
        # Check validity of nid!
        other_nids = [d.nid for d in self._data.values() if d is not self.current]
        if self.current.nid in other_nids:
            QMessageBox.warning(self.window, 'Warning', 'Region ID %s already in use' % self.current.nid)
            self.current.nid = str_utils.get_next_generic_nid(self.current.nid, other_nids)
        self._data.update_nid(self.current, self.current.nid)
        self.window.update_list()

    def region_type_changed(self, index):
        self.current.region_type = self.region_type_box.edit.currentText()
        if self.current.region_type in ('Normal', 'Formation'):
            self.sub_nid_box.hide()
            self.condition_box.hide()
            self.status_box.hide()
        elif self.current.region_type == 'Status':
            self.sub_nid_box.hide()
            self.condition_box.hide()
            self.status_box.show()
        elif self.current.region_type == 'Event':
            self.sub_nid_box.show()
            self.condition_box.show()
            self.status_box.hide()

    def sub_nid_changed(self, text):
        self.current.sub_nid = text

    def condition_changed(self, text):
        self.current.condition = text

    def status_changed(self, index):
        self.current.sub_nid = self.status_box.edit.currentText()

    def set_current(self, current):
        self.current = current
        self.nid_box.edit.setText(current.nid)
        self.region_type_box.edit.setValue(current.region_type)
        self.condition_box.edit.setText(current.condition)
        if current.region_type == 'Status':
            self.status_box.setValue(current.sub_nid)
        elif current.region_type == 'Event':
            self.sub_nid_box.setText(current.sub_nid)
