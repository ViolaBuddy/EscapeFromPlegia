from PyQt5.QtWidgets import QLabel, QVBoxLayout, QApplication, QDoubleSpinBox, QCheckBox
from PyQt5.QtCore import Qt

from app import dark_theme
from app.extensions.custom_gui import ComboBox, PropertyBox, PropertyCheckBox, Dialog

from app.editor.settings import MainSettingsController

from app.editor import timer

name_to_button = {'L-click': Qt.LeftButton,
                  'R-click': Qt.RightButton}
button_to_name = {v: k for k, v in name_to_button.items()}

class PreferencesDialog(Dialog):
    theme_options = ['Light', 'Dark', 'Discord', 'Sidereal', 'Mist']

    def __init__(self, parent):
        super().__init__(parent)
        self.window = parent
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.settings = MainSettingsController()

        self.saved_preferences = {}
        self.saved_preferences['select_button'] = self.settings.get_select_button(Qt.LeftButton)
        self.saved_preferences['place_button'] = self.settings.get_place_button(Qt.RightButton)
        self.saved_preferences['theme'] = self.settings.get_theme(0)
        self.saved_preferences['event_autocomplete'] = self.settings.get_event_autocomplete(1)
        self.saved_preferences['autosave_time'] = self.settings.get_autosave_time()

        self.available_options = name_to_button.keys()

        label = QLabel("Modify mouse preferences for Unit and Tile Painter Menus")

        self.select = PropertyBox('Select', ComboBox, self)
        for option in self.available_options:
            self.select.edit.addItem(option)
        self.place = PropertyBox('Place', ComboBox, self)
        for option in self.available_options:
            self.place.edit.addItem(option)
        self.select.edit.setValue(button_to_name[self.saved_preferences['select_button']])
        self.place.edit.setValue(button_to_name[self.saved_preferences['place_button']])
        self.select.edit.currentIndexChanged.connect(self.select_changed)
        self.place.edit.currentIndexChanged.connect(self.place_changed)

        self.theme = PropertyBox('Theme', ComboBox, self)
        for option in self.theme_options:
            self.theme.edit.addItem(option)
        self.theme.edit.setValue(self.theme_options[self.saved_preferences['theme']])
        self.theme.edit.currentIndexChanged.connect(self.theme_changed)

        self.autocomplete = PropertyCheckBox('Event Autocomplete', QCheckBox, self)
        self.autocomplete.edit.setChecked(bool(self.saved_preferences['event_autocomplete']))

        self.autosave = PropertyBox('Autosave Time (minutes)', QDoubleSpinBox, self)
        self.autosave.edit.setRange(0.5, 99)
        self.autosave.edit.setValue(self.saved_preferences['autosave_time'])
        self.autosave.edit.valueChanged.connect(self.autosave_time_changed)

        self.layout.addWidget(label)
        self.layout.addWidget(self.select)
        self.layout.addWidget(self.place)
        self.layout.addWidget(self.theme)
        self.layout.addWidget(self.autocomplete)
        self.layout.addWidget(self.autosave)
        self.layout.addWidget(self.buttonbox)

    def select_changed(self, idx):
        choice = self.select.edit.currentText()
        if choice == 'L-click':
            self.place.edit.setValue('R-click')
        else:
            self.place.edit.setValue('L-click')

    def place_changed(self, idx):           
        choice = self.place.edit.currentText()
        if choice == 'L-click':
            self.select.edit.setValue('R-click')
        else:
            self.select.edit.setValue('L-click')

    def theme_changed(self, idx):
        choice = self.theme.edit.currentText()
        ap = QApplication.instance()
        dark_theme.set(ap, idx)
        self.window.set_icons(idx)  # Change icons of main editor

    def autosave_time_changed(self, val):
        t = timer.get_timer()
        t.autosave_timer.stop()
        t.autosave_timer.setInterval(val * 60 * 1000)
        t.autosave_timer.start()

    def accept(self):
        self.settings.set_select_button(name_to_button[self.select.edit.currentText()])
        self.settings.set_place_button(name_to_button[self.place.edit.currentText()])
        self.settings.set_theme(self.theme.edit.currentIndex())
        # For some reason Qt doesn't save booleans correctly
        # resorting to int
        autocomplete = 1 if self.autocomplete.edit.isChecked() else 0
        self.settings.set_event_autocomplete(autocomplete)
        autosave = float(self.autosave.edit.value())
        self.settings.set_autosave_time(autosave)
        super().accept()

    def reject(self):
        super().reject()
