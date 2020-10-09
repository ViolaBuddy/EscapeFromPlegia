import functools

from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QLineEdit, \
    QMessageBox, QHBoxLayout, QAction, QToolButton, QToolBar, \
    QDialog, QVBoxLayout, QSizePolicy, QSpacerItem, QMenu, QWidgetAction
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

import app.engine.item_component_access as ICA

from app.extensions.custom_gui import PropertyBox, QHLine
from app.editor.icons import ItemIcon16
from app.editor import component_database
from app import utilities

class ItemProperties(QWidget):
    def __init__(self, parent, current=None):
        super().__init__(parent)
        self.window = parent
        self.model = self.window.left_frame.model
        self._data = self.window._data
        self.database_editor = self.window.window
        self.main_editor = self.database_editor.window

        self.current = current

        top_section = QHBoxLayout()

        self.icon_edit = ItemIcon16(self)
        top_section.addWidget(self.icon_edit)

        horiz_spacer = QSpacerItem(40, 10, QSizePolicy.Fixed, QSizePolicy.Fixed)
        top_section.addSpacerItem(horiz_spacer)

        name_section = QVBoxLayout()

        self.nid_box = PropertyBox("Unique ID", QLineEdit, self)
        self.nid_box.edit.textChanged.connect(self.nid_changed)
        self.nid_box.edit.editingFinished.connect(self.nid_done_editing)
        name_section.addWidget(self.nid_box)

        self.name_box = PropertyBox("Display Name", QLineEdit, self)
        self.name_box.edit.setMaxLength(13)
        self.name_box.edit.textChanged.connect(self.name_changed)
        name_section.addWidget(self.name_box)

        top_section.addLayout(name_section)

        main_section = QGridLayout()

        self.desc_box = PropertyBox("Description", QLineEdit, self)
        self.desc_box.edit.textChanged.connect(self.desc_changed)
        main_section.addWidget(self.desc_box, 0, 0, 1, 3)

        component_section = QGridLayout()
        component_label = QLabel("Components")
        component_label.setAlignment(Qt.AlignBottom)
        component_section.addWidget(component_label, 0, 0, Qt.AlignBottom)

        # Create actions
        self.actions = {}
        for component in ICA.get_item_components():
            new_func = functools.partial(self.add_component, component)
            new_action = QAction(QIcon(), component.class_name(), self, triggered=new_func)
            self.actions[component.nid] = new_action

        # Create toolbar
        self.toolbar = QToolBar(self)
        self.menus = {}

        for component in ICA.get_item_components():
            if component.tag not in self.menus:
                new_menu = QMenu(self)
                self.menus[component.tag] = new_menu
                toolbutton = QToolButton(self)
                toolbutton.setIcon(QIcon("icons/component_%s.png" % component.tag))
                toolbutton.setMenu(new_menu)
                toolbutton.setPopupMode(QToolButton.InstantPopup)
                toolbutton_action = QWidgetAction(self)
                toolbutton_action.setDefaultWidget(toolbutton)
                self.toolbar.addAction(toolbutton_action)
            menu = self.menus[component.tag]
            menu.addAction(self.actions.get(component.nid))

        component_section.addWidget(self.toolbar, 1, 0, 1, 2)

        self.component_list = component_database.ComponentList(self)
        component_section.addWidget(self.component_list, 2, 0, 1, 2)
        self.component_list.order_swapped.connect(self.component_moved)

        total_section = QVBoxLayout()
        self.setLayout(total_section)
        total_section.addLayout(top_section)
        total_section.addLayout(main_section)
        h_line = QHLine()
        total_section.addWidget(h_line)
        total_section.addLayout(component_section)

    def nid_changed(self, text):
        # Also change name if they are identical
        if self.current.name == self.current.nid:
            self.name_box.edit.setText(text)
        self.current.nid = text
        self.window.update_list()

    def nid_done_editing(self):
        # Check validity of nid!
        other_nids = [d.nid for d in self._data.values() if d is not self.current]
        if self.current.nid in other_nids:
            QMessageBox.warning(self.window, 'Warning', 'Item Type ID %s already in use' % self.current.nid)
            self.current.nid = utilities.get_next_name(self.current.nid, other_nids)
        self.model.change_nid(self._data.find_key(self.current), self.current.nid)
        self._data.update_nid(self.current, self.current.nid)
        self.window.update_list()

    def name_changed(self, text):
        self.current.name = text
        self.window.update_list()

    def desc_changed(self, text):
        self.current.desc = text

    def add_component(self, component_class):
        component = component_class(component_class.value)
        self.current.components.append(component)
        self.add_component_widget(component)

    def add_component_widget(self, component):
        c = component_database.get_display_widget(component, self)
        self.component_list.add_component(c)

    def remove_component(self, component_widget):
        data = component_widget._data
        self.component_list.remove_component(component_widget)
        self.current.components.delete(data)

    def component_moved(self, start, end):
        self.current.components.move_index(start, end)

    def set_current(self, current):
        self.current = current
        self.nid_box.edit.setText(current.nid)
        self.name_box.edit.setText(current.name)
        self.desc_box.edit.setText(current.desc)
        self.icon_edit.set_current(current.icon_nid, current.icon_index)
        self.component_list.clear()
        for component in current.components.values():
            self.add_component_widget(component)

    def add_components(self):
        components = ICA.get_item_components()
        dlg = component_database.ComponentDialog(components, "Item Components", self)
        result = dlg.exec_()
        if result == QDialog.Accepted:
            checked = dlg.get_checked()
            for nid in checked:
                c = ICA.get_component(nid)
                self.add_component(c)
        else:
            pass