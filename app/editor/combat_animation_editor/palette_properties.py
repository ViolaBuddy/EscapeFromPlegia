import os

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QFileDialog, QVBoxLayout, \
    QGraphicsView, QGraphicsScene, QLineEdit, QLabel, QSizePolicy, QPushButton, \
    QSpinBox, QMessageBox, QDialog
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPen, QPixmap, QImage, QPainter

from app.constants import WINWIDTH, WINHEIGHT
from app.resources.resources import RESOURCES

from app.editor.settings import MainSettingsController

from app.editor import timer
from app.utilities import utils, str_utils
from app.extensions.custom_gui import PropertyBox, ComboBox, Dialog
from app.extensions.color_icon import ColorIcon
from app.extensions.color_slider import RGBSlider, HSVSlider
from app.editor.combat_animation_editor.frame_selector import FrameSelector
from app.editor.combat_animation_editor import combat_animation_model
from app.resources.combat_anims import Frame
from app.resources.combat_palettes import Palette
from app.editor.icon_editor.icon_view import IconView
import app.editor.utilities as editor_utilities
from app.resources import combat_anims

class AnimView(IconView):
    def get_color_at_pos(self, pixmap, pos):
        image = pixmap.toImage()
        current_color = image.pixel(*pos)
        color = QColor(current_color)
        return (color.red(), color.green(), color.blue())

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        scene_pos = self.mapToScene(event.pos())
        pos = int(scene_pos.x()), int(scene_pos.y())

        # Need to get original frame with base palette
        frame = self.window.current_frame
        if not frame:
            return
        offset_x, offset_y = frame.offset
        pos = pos[0] - offset_x, pos[1] - offset_y
        pixmap = frame.pixmap

        if event.button() == Qt.LeftButton:
            base_color = self.get_color_at_pos(pixmap, pos)
            palette = self.window.current_palette
            if not palette:
                return
            base_colors = palette.colors.keys()
            if base_color not in base_colors:
                print("Cannot find color: %s in %s" % (base_color, base_colors))
                return
            c = palette.colors[base_color]
            print(c, flush=True)
            self.window.color_editor_widget.set_current(c)

class ColorSelectorWidget(QGraphicsView):
    palette_size = 32
    square_size = 8
    selectionChanged = pyqtSignal(object)

    def __init__(self, parent):
        super().__init__(parent)
        self.window = parent

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setMouseTracking(True)
        self.setStyleSheet("background-color:rgb(192,192,192);")

        self.current_palette = None
        self.current_frame = None
        self.current_color = None

        self.working_image = None

        timer.get_timer().tick_elapsed.connect(self.tick)

    def tick(self):
        if self.current_palette:
            self.update_view()

    def clear_scene(self):
        self.scene.clear()

    def update_view(self):
        if self.current_palette:
            self.working_image = QPixmap.fromImage(self.get_palette_image())
            self.show_image()
        else:
            self.clear_scene()

    def show_image(self):
        self.clear_scene()
        self.scene.addPixmap(self.working_image)

    def get_coords_used_in_frame(self, frame: Frame) -> list:
        im = QImage(frame.pixmap)
        unique_colors = editor_utilities.find_palette(im)
        coords = [(uc[1], uc[2]) for uc in unique_colors]
        return coords

    def get_palette_image(self) -> QImage:
        side_length = self.palette_size * self.square_size
        base_image = QImage(side_length, side_length, QImage.Format_ARGB32)
        base_image.fill(QColor(192, 192, 192, 255))

        painter = QPainter()
        painter.begin(base_image)
        if self.current_frame:
            painter.setPen(QPen(QColor(0, 0, 0, 255), 1, Qt.SolidLine))
            for coord in self.get_coords_used_in_frame(self.current_frame):
                painter.drawRect(coord[0] * self.palette_size + 1, coord[1] * self.palette_size + 1, self.palette_size - 2, self.palette_size - 2)
        # Outline chosen color in bright yellow
        if self.current_color:
            painter.setPen(QPen(QColor(0, 255, 255, 255), 2, Qt.SolidLine))
            coord = self.current_color
            painter.drawRect(coord[0] * self.palette_size, coord[1] * self.palette_size, self.palette_size, self.palette_size)
        # draw actual colors
        for coord, color in self.current_palette.colors.items():
            write_color = QColor(color[0], color[1], color[2])
            painter.fillRect(coord[0] * self.palette_size + 2, coord[1] * self.palette_size + 2, self.palette_size - 4, self.palette_size - 4, write_color)
        painter.end()
        return base_image

    def set_current(self, current_palette: Palette, current_frame: Frame):
        self.current_palette = current_palette
        self.current_frame = current_frame
        self.current_color = None
        self.update_view()
        self.selectionChanged.emit(None)

    def get_current_color(self) -> tuple:
        """
        Returns 3-tuple of color
        """
        return self.current_palette.colors.get(self.current_color)

    def set_current_color(self, color: QColor):
        if self.current_palette and self.current_color:
            self.current_palette.colors[self.current_color] = tuple(color.getRgb()[:3])

    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        tile_pos = int(scene_pos.x() // self.palette_size), \
            int(scene_pos.y() // self.palette_size)

        if event.button() == Qt.LeftButton:
            print(tile_pos)
            self.current_color = tile_pos
            self.selectionChanged.emit(self.current_palette.colors.get(self.current_color))

class ChannelBox(QWidget):
    colorChanged = pyqtSignal(QColor)

    def __init__(self, parent):
        super().__init__(parent)

        self.color: QColor = QColor(0, 0, 0)

        self.hue_slider = HSVSlider('hue', self)
        self.hue_slider.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self.hue_slider.setMinimumSize(200, 20)
        self.saturation_slider = HSVSlider('saturation', self)
        self.saturation_slider.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self.saturation_slider.setMinimumSize(200, 20)
        self.value_slider = HSVSlider('value', self)
        self.value_slider.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self.value_slider.setMinimumSize(200, 20)

        self.hue_label = QLabel('H')
        self.saturation_label = QLabel('S')
        self.value_label = QLabel('V')

        self.hue_spin = QSpinBox()
        self.hue_spin.setRange(0, 360)
        self.saturation_spin = QSpinBox()
        self.saturation_spin.setRange(0, 255)
        self.value_spin = QSpinBox()
        self.value_spin.setRange(0, 255)

        self.red_slider = RGBSlider('red', self)
        self.red_slider.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self.red_slider.setMinimumSize(200, 20)
        self.green_slider = RGBSlider('green', self)
        self.green_slider.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self.green_slider.setMinimumSize(200, 20)
        self.blue_slider = RGBSlider('blue', self)
        self.blue_slider.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self.blue_slider.setMinimumSize(200, 20)

        self.red_label = QLabel('R')
        self.green_label = QLabel('G')
        self.blue_label = QLabel('B')

        self.red_spin = QSpinBox()
        self.red_spin.setRange(0, 255)
        self.green_spin = QSpinBox()
        self.green_spin.setRange(0, 255)
        self.blue_spin = QSpinBox()
        self.blue_spin.setRange(0, 255)

        self.manual_edit: bool = False  # Guard so that we don't get infinite change

        self.hue_slider.hueChanged.connect(self.change_hue)
        self.saturation_slider.saturationChanged.connect(self.change_saturation)
        self.value_slider.valueChanged.connect(self.change_value)

        self.hue_spin.valueChanged.connect(self.change_hue_i)
        self.saturation_spin.valueChanged.connect(self.change_saturation_i)
        self.value_spin.valueChanged.connect(self.change_value_i)

        self.red_slider.redChanged.connect(self.change_red)
        self.green_slider.greenChanged.connect(self.change_green)
        self.blue_slider.blueChanged.connect(self.change_blue)

        self.red_spin.valueChanged.connect(self.change_red_i)
        self.green_spin.valueChanged.connect(self.change_green_i)
        self.blue_spin.valueChanged.connect(self.change_blue_i)

        main_layout = QVBoxLayout()
        hue_layout = QHBoxLayout()
        saturation_layout = QHBoxLayout()
        value_layout = QHBoxLayout()
        hue_layout.addWidget(self.hue_label)
        hue_layout.addWidget(self.hue_spin)
        hue_layout.addWidget(self.hue_slider)
        saturation_layout.addWidget(self.saturation_label)
        saturation_layout.addWidget(self.saturation_spin)
        saturation_layout.addWidget(self.saturation_slider)
        value_layout.addWidget(self.value_label)
        value_layout.addWidget(self.value_spin)
        value_layout.addWidget(self.value_slider)
        main_layout.addLayout(hue_layout)
        main_layout.addLayout(saturation_layout)
        main_layout.addLayout(value_layout)

        red_layout = QHBoxLayout()
        green_layout = QHBoxLayout()
        blue_layout = QHBoxLayout()
        red_layout.addWidget(self.red_label)
        red_layout.addWidget(self.red_spin)
        red_layout.addWidget(self.red_slider)
        green_layout.addWidget(self.green_label)
        green_layout.addWidget(self.green_spin)
        green_layout.addWidget(self.green_slider)
        blue_layout.addWidget(self.blue_label)
        blue_layout.addWidget(self.blue_spin)
        blue_layout.addWidget(self.blue_slider)
        main_layout.addLayout(red_layout)
        main_layout.addLayout(green_layout)
        main_layout.addLayout(blue_layout)

        self.setLayout(main_layout)

    def change_color(self, color: QColor):
        if self.color != color:
            self.color = color
            self.change_hue(color)
            self.change_saturation(color)
            self.change_value(color)
            self.change_red(color)
            self.change_green(color)
            self.change_blue(color)

    def change_hue(self, color: QColor):
        self.manual_edit = False
        self.hue_slider.set_hue(color)
        self.hue_spin.setValue(color.hue())

        self.saturation_slider.change_hue(color)
        self.value_slider.change_hue(color)

        self.color = self.hue_slider.color
        self.colorChanged.emit(self.color)

        self.update_rgb_sliders(self.color)

    def change_hue_i(self, i: int):
        if self.manual_edit:
            new_color = QColor.fromHsv(i, 0, 0)
            self.change_hue(new_color)
        self.manual_edit = True

    def change_saturation(self, color: QColor):
        self.manual_edit = False
        self.saturation_slider.set_saturation(color)
        self.saturation_spin.setValue(color.saturation())

        self.hue_slider.change_saturation(color)
        self.value_slider.change_saturation(color)

        self.color = self.saturation_slider.color
        self.colorChanged.emit(self.color)

        self.update_rgb_sliders(self.color)

    def change_saturation_i(self, i: int):
        if self.manual_edit:
            new_color = QColor.fromHsv(0, i, 0)
            self.change_saturation(new_color)
        self.manual_edit = True

    def change_value(self, color: QColor):
        self.manual_edit = False
        self.value_slider.set_value(color)
        self.value_spin.setValue(color.value())

        self.hue_slider.change_value(color)
        self.saturation_slider.change_value(color)

        self.color = self.value_slider.color
        self.colorChanged.emit(self.color)

        self.update_rgb_sliders(self.color)

    def change_value_i(self, i: int):
        if self.manual_edit:
            new_color = QColor.fromHsv(0, 0, i)
            self.change_value(new_color)
        self.manual_edit = True

    def update_hsv_sliders(self, color: QColor):
        self.hue_slider.change_hue(color)
        self.hue_slider.change_saturation(color)
        self.hue_slider.change_value(color)
        self.saturation_slider.change_hue(color)
        self.saturation_slider.change_saturation(color)
        self.saturation_slider.change_value(color)
        self.value_slider.change_hue(color)
        self.value_slider.change_saturation(color)
        self.value_slider.change_value(color)

        self.hue_spin.setValue(color.hue())
        self.saturation_spin.setValue(color.saturation())
        self.value_spin.setValue(color.value())

    def change_red(self, color: QColor):
        self.manual_edit = False
        self.red_slider.set_red(color)
        self.red_spin.setValue(color.red())

        self.green_slider.change_red(color)
        self.blue_slider.change_red(color)

        self.color = self.red_slider.color
        self.colorChanged.emit(self.color)

        self.update_hsv_sliders(self.color)

    def change_red_i(self, i: int):
        if self.manual_edit:
            new_color = QColor.fromRgb(i, 0, 0)
            self.change_red(new_color)
        self.manual_edit = True

    def change_green(self, color: QColor):
        self.manual_edit = False
        self.green_slider.set_green(color)
        self.green_spin.setValue(color.green())

        self.red_slider.change_green(color)
        self.blue_slider.change_green(color)

        self.color = self.green_slider.color
        self.colorChanged.emit(self.color)

        self.update_hsv_sliders(self.color)

    def change_green_i(self, i: int):
        if self.manual_edit:
            new_color = QColor.fromRgb(0, i, 0)
            self.change_green(new_color)
        self.manual_edit = True

    def change_blue(self, color: QColor):
        self.manual_edit = False
        self.blue_slider.set_blue(color)
        self.blue_spin.setValue(color.blue())

        self.red_slider.change_blue(color)
        self.green_slider.change_blue(color)

        self.color = self.blue_slider.color
        self.colorChanged.emit(self.color)

        self.update_hsv_sliders(self.color)

    def change_blue_i(self, i: int):
        if self.manual_edit:
            new_color = QColor.fromRgb(0, 0, i)
            self.change_blue(new_color)
        self.manual_edit = True

    def update_rgb_sliders(self, color: QColor):
        self.red_slider.change_red(color)
        self.red_slider.change_green(color)
        self.red_slider.change_blue(color)
        self.green_slider.change_red(color)
        self.green_slider.change_green(color)
        self.green_slider.change_blue(color)
        self.blue_slider.change_red(color)
        self.blue_slider.change_green(color)
        self.blue_slider.change_blue(color)
        
        self.red_spin.setValue(color.red())
        self.green_spin.setValue(color.green())
        self.blue_spin.setValue(color.blue())

class ColorEditorWidget(QWidget):
    colorChanged = pyqtSignal(QColor)

    def __init__(self, parent):
        super().__init__(parent)
        self.window = parent

        self.current_color = QColor(0, 0, 0)

        self.color_icon = ColorIcon(self.current_color, self)
        self.color_icon.colorChanged.connect(self.on_color_change)

        self.channel_box = ChannelBox(self)
        self.channel_box.colorChanged.connect(self.on_color_change)

        self.hex_label = PropertyBox('Hex Code', QLabel, self)
        self.hex_label.edit.setText(utils.color_to_hex(self.current_color.getRgb()))

        main_layout = QHBoxLayout()
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.color_icon)
        left_layout.addWidget(self.hex_label)
        main_layout.addLayout(left_layout)
        main_layout.addWidget(self.channel_box)
        self.setLayout(main_layout)

    def on_color_change(self, color: QColor):
        self.set_current(color)

    def set_current(self, color: QColor):
        if color != self.current_color:
            self.current_color: QColor = color

            self.color_icon.change_color(color)
            tuple_color = color.getRgb()
            self.hex_label.edit.setText(utils.color_to_hex(tuple_color))
            self.channel_box.change_color(color)

            self.colorChanged.emit(color)

class WeaponAnimSelection(Dialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.window = parent

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        self.current_combat_anim = None

        self.combat_box = PropertyBox("Combat Animations", ComboBox, self)
        self.combat_box.edit.addItems(RESOURCES.combat_anims.keys())
        self.current_combat_anim = RESOURCES.combat_anims[0]
        self.combat_box.edit.currentIndexChanged.connect(self.combat_changed)
        
        self.weapon_box = PropertyBox("Weapon Animations", ComboBox, self)
        if RESOURCES.combat_anims:
            weapon_anims = self.current_combat_anim.weapon_anims
            self.weapon_box.edit.addItems(weapon_anims.keys())

        main_layout.addWidget(self.combat_box)
        main_layout.addWidget(self.weapon_box)
        main_layout.addWidget(self.buttonbox)

    def combat_changed(self, idx):
        combat_text = self.combat_box.edit.currentText()
        self.current_combat_anim = RESOURCES.combat_anims.get(combat_text)
        self.weapon_box.edit.clear()
        weapon_anims = self.current_combat_anim.weapon_anims
        self.weapon_box.edit.addItems([weapon_anim.nid for weapon_anim in weapon_anims])

    @classmethod
    def get(cls, parent):
        dlg = cls(parent)
        result = dlg.exec_()
        if result == QDialog.Accepted:
            return dlg.combat_box.edit.currentText(), dlg.weapon_box.edit.currentText()
        else:
            return None, None

class PaletteProperties(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.window = parent
        self._data = self.window._data
        self.model = self.window.left_frame.model

        self.settings = MainSettingsController()

        self.current_palette = None
        self.current_frame = None

        self.nid_box = PropertyBox("Unique ID", QLineEdit, self)
        self.nid_box.edit.textChanged.connect(self.nid_changed)
        self.nid_box.edit.editingFinished.connect(self.nid_done_editing)

        self.import_box = QPushButton("Import from PNG Image...")
        self.import_box.clicked.connect(self.import_palette_from_image)

        left_frame = self.window.left_frame
        grid = left_frame.layout()
        grid.addWidget(self.import_box, 3, 0, 1, 2)
        grid.addWidget(self.nid_box, 4, 0, 1, 2)
        
        self.raw_view = AnimView(self)
        self.raw_view.static_size = True
        self.raw_view.setSceneRect(0, 0, WINWIDTH, WINHEIGHT)
        self.raw_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.select_frame_button = QPushButton("Select Frame", self)
        self.select_frame_button.clicked.connect(self.select_frame)

        self.color_selector_widget = ColorSelectorWidget(self)
        self.color_editor_widget = ColorEditorWidget(self)

        self.color_editor_widget.colorChanged.connect(self.color_changed)
        self.color_selector_widget.selectionChanged.connect(self.selection_changed)
        
        main_layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.color_selector_widget)
        view_layout = QVBoxLayout()
        view_layout.addWidget(self.raw_view)
        view_layout.addWidget(self.select_frame_button)
        top_layout.addLayout(view_layout)
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.color_editor_widget)
        self.setLayout(main_layout)

    def nid_changed(self, text):
        self.current_palette.nid = text
        self.window.update_list()

    def nid_done_editing(self):
        # Check validity of nid!
        other_nids = [d.nid for d in self._data.values() if d is not self.current_palette]
        if self.current_palette.nid in other_nids:
            QMessageBox.warning(self.window, 'Warning', 'Palette ID %s already in use' % self.current_palette.nid)
            self.current_palette.nid = str_utils.get_next_name(self.current_palette.nid, other_nids)
        self.model.on_nid_changed(self._data.find_key(self.current_palette), self.current_palette.nid)
        self._data.update_nid(self.current_palette, self.current_palette.nid)
        self.window.update_list()

    @property
    def current(self):
        return self.current_palette

    def set_current(self, current):
        self.current_palette = current
        self.nid_box.edit.setText(self.current_palette.nid)
        self.color_selector_widget.set_current(current, self.current_frame)
        if self.current_palette:
            current_color = self.color_selector_widget.get_current_color()
            if current_color:
                self.color_editor_widget.setEnabled(True)
                self.color_editor_widget.set_current(current_color)
            else:
                self.color_editor_widget.setEnabled(False)
            self.draw_frame()

    def get_current_palette(self):
        return self.current_palette.nid

    def select_frame(self):
        combat_anim_nid, weapon_anim_nid = WeaponAnimSelection.get(self)
        combat_anim = RESOURCES.combat_anims.get(combat_anim_nid)
        if not combat_anim:
            return
        weapon_anim = combat_anim.weapon_anims.get(weapon_anim_nid)
        if not weapon_anim:
            return        
        frame, ok = FrameSelector.get(combat_anim, weapon_anim, self)
        if frame and ok:
            self.current_frame = frame
            self.color_selector_widget.set_current(self.current_palette, self.current_frame)
            self.draw_frame()

    def selection_changed(self, selection):
        current = self.color_selector_widget.get_current_color()
        if current:
            self.color_editor_widget.setEnabled(True)
            self.color_editor_widget.set_current(QColor(*current))
        else:
            self.color_editor_widget.setEnabled(True)
            self.color_editor_widget.set_current(QColor(0, 0, 0))
            # self.color_editor_widget.setEnabled(False)

    def color_changed(self, color: QColor):
        if self.current_palette:
            self.color_selector_widget.set_current_color(color)
        self.draw_frame()

    def draw_frame(self):
        if self.current_frame:
            im = combat_animation_model.palette_swap(self.current_frame.pixmap, self.get_current_palette())
            base_image = QImage(WINWIDTH, WINHEIGHT, QImage.Format_ARGB32)
            base_image.fill(editor_utilities.qCOLORKEY)
            painter = QPainter()
            painter.begin(base_image)
            offset_x, offset_y = self.current_frame.offset
            painter.drawImage(offset_x, offset_y, im)
            painter.end()
            self.raw_view.set_image(QPixmap.fromImage(base_image))
            self.raw_view.show_image()

    def import_palette_from_image(self):
        starting_path = self.settings.get_last_open_path()
        fns, ok = QFileDialog.getOpenFileNames(self.window, "Select Legacy Script Files", starting_path, "PNG Files (*.png);;All Files (*)")
        if fns and ok:
            parent_dir = os.path.split(fns[-1])[0]
            self.settings.set_last_open_path(parent_dir)

            did_import = False
            for image_fn in fns:
                if image_fn.endswith('.png'):
                    head, tail = os.path.split(image_fn)
                    palette_nid = tail[:-4]
                    palette_nid = str_utils.get_next_name(palette_nid, RESOURCES.combat_palettes.keys())
                    pix = QPixmap(image_fn)
                    palette_colors = editor_utilities.find_palette(pix.toImage())
                    new_palette = Palette(palette_nid)
                    colors = {(int(idx % 8), int(idx / 8)): color for idx, color in enumerate(palette_colors)}
                    new_palette.colors = colors
                    RESOURCES.combat_palettes.append(new_palette)
                    did_import = True
            if did_import:
                # Move view
                self.model.move_to_bottom()
