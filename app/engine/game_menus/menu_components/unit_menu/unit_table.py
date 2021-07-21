from __future__ import annotations

from typing import Callable, List, Tuple

import app.engine.graphics.ui_framework as uif
from app.constants import WINHEIGHT, WINWIDTH
from app.data.database import DB
from app.data.stats import StatPrefab
from app.data.weapons import WeaponType
from app.engine import engine, icons, image_mods, item_system
from app.engine.base_surf import create_base_surf, create_highlight_surf
from app.engine.bmpfont import BmpFont
from app.engine.fonts import FONT
from app.engine.game_counters import ANIMATION_COUNTERS
from app.engine.graphics.ui_framework.premade_animations.animation_templates import \
    component_scroll_anim
from app.engine.graphics.ui_framework.ui_framework_layout import HAlignment
from app.engine.graphics.ui_framework.ui_framework_styling import UIMetric
from app.engine.gui import ScrollArrow, ScrollBar
from app.engine.objects.unit import UnitObject
from app.sprites import SPRITES
from app.utilities.enums import Direction
from app.utilities.utils import tclamp, tuple_add, tuple_sub

CURSOR_PERTURBATION = [0, 1, 2, 3, 4, 3, 2, 1]
ICON_SIZE = (16, 16)

class Column():
    def __init__(self, width: str, stat_name: str, header_align: uif.HAlignment,
                 header_icon: engine.Surface, get_stat: Callable[[UnitObject], str],
                 get_icon: Callable[[UnitObject], engine.Surface],
                 sort_by: Callable[[UnitObject], str | int] = None,
                 font: BmpFont = FONT['text-blue']):
        self.width = width
        self.stat_name = stat_name
        self.header_align = header_align
        self.header_icon = header_icon
        self.get_stat = get_stat
        self.get_icon = get_icon
        if not sort_by:
            self.sort_by = get_stat
        else:
            self.sort_by = sort_by
        self.font = font

def get_all_weapon_types() -> List[WeaponType]:
    return [wtype for wtype in DB.weapons.values() if wtype.nid != "Default"]

def get_all_character_stats() -> List[StatPrefab]:
    return [stat for stat in DB.stats if stat.position != 'hidden']

def get_formatted_stat_pages() -> List[Tuple[str, List[Column]]]:
    all_pages = []
    first_page = [
        Column('30%', 'Class', uif.HAlignment.LEFT, None, lambda unit: DB.classes.get(unit.klass).name, None, font=FONT['text-white']),
        Column('16%', 'Lv', uif.HAlignment.RIGHT, None, lambda unit: unit.level, None),
        Column('16%', 'Exp', uif.HAlignment.RIGHT, None, lambda unit: unit.exp, None),
        Column('16%', 'HP', uif.HAlignment.RIGHT, None, lambda unit: unit.get_hp(), None),
        Column('16%', 'Max', uif.HAlignment.LEFT, None, lambda unit: '/' + str(unit.get_max_hp()), None),
    ]
    all_pages.append(('Character', first_page))

    new_character_stat_page = []
    for idx, stat in enumerate(get_all_character_stats()):
        new_character_stat_page.append(
            # truncate the name to 5 digits
            Column('16%', stat.name[:5], uif.HAlignment.RIGHT, None, lambda unit, nid=stat.nid: unit.get_stat(nid), None)
        )
        if len(new_character_stat_page) == 6 or idx == len(get_all_character_stats()) - 1:
            all_pages.append(('Vital Statistics', new_character_stat_page[:]))
            new_character_stat_page = []

    equipment_page = [
        Column('50%', 'Equip', uif.HAlignment.LEFT, engine.create_surface(ICON_SIZE, True),
                lambda unit: (unit.equipped_weapon.name if unit.equipped_weapon else None),
                lambda unit: (icons.get_icon(unit.equipped_weapon) if unit.equipped_weapon else None),
                lambda unit: (item_system.weapon_type(unit, unit.equipped_weapon) if unit.equipped_weapon else "",
                              unit.equipped_weapon.name if unit.equipped_weapon else "",),
                font=FONT['text-white']
               ),
        Column('16%', 'Atk', uif.HAlignment.RIGHT, None,
               lambda unit: str(unit.get_damage_with_current_weapon()) if unit.get_damage_with_current_weapon() > 0 else '--',
               None),
        Column('16%', 'Hit', uif.HAlignment.RIGHT, None,
               lambda unit: str(unit.get_accuracy_with_current_weapon()) if unit.get_accuracy_with_current_weapon() > 0 else '--',
               None),
        Column('16%', 'Avoid', uif.HAlignment.RIGHT, None,
               lambda unit: str(unit.get_avoid_with_current_weapon()) if unit.get_avoid_with_current_weapon() > 0 else '--',
               None),
    ]
    all_pages.append(('Equipment', equipment_page))

    new_weapon_rank_page = []
    for idx, wtype in enumerate(get_all_weapon_types()):
        new_weapon_rank_page.append(
            Column('12%', "", uif.HAlignment.LEFT, icons.get_icon(wtype),
                   lambda unit: (DB.weapon_ranks.get_rank_from_wexp(unit.wexp[wtype.nid])
                                 if DB.weapon_ranks.get_rank_from_wexp(unit.wexp[wtype.nid])
                                 else '-'),
                   None)
        )
        if len(new_weapon_rank_page) == 8 or idx == len(get_all_weapon_types()) - 1:
            all_pages.append(('Weapon Level', new_weapon_rank_page[:]))
            new_weapon_rank_page = []

    return all_pages

class UnitStatisticsTable(uif.UIComponent):
    def __init__(self, name: str = None, parent: UnitInformationTable = None, data: List[UnitObject]=None):
        super().__init__(name=name, parent=parent)
        self.parent = parent
        self.STAT_PAGES = get_formatted_stat_pages()
        self.MAX_PAGES = len(self.STAT_PAGES)
        self.size = ('80%', '100%')
        self.overflow = (0, 0, 0, 0)
        self.max_width = '80%'
        self.max_height = '100%'
        self.padding = (ICON_SIZE[0], 0, 0, 0)
        self.data = data
        self.page = 0

        self.cursor_sprite: engine.Surface = SPRITES.get('menu_hand')

        # children layout
        self.props.layout = uif.UILayoutType.LIST
        self.props.list_style = uif.ListLayoutStyle.ROW

        self.table: List[uif.HeaderList[uif.IconRow]] = []

        self.recreate_table()

        self.width = self.max_width * self.MAX_PAGES

    @property
    def cursor_pos(self):
        return self.parent.cursor_pos

    def recreate_table(self):
        self.children.clear()
        for page in self.STAT_PAGES:
            page_width_so_far: int = 0
            for idx, column in enumerate(page[1]):
                left_margin = 0
                right_margin = 0
                if idx != len(page[1]) - 1:
                    col_width = UIMetric.parse(column.width).to_pixels(self.width - ICON_SIZE[0])
                    page_width_so_far += col_width
                    right_margin = 0
                else:
                    col_width = self.width - page_width_so_far
                    col_width = UIMetric.parse(column.width).to_pixels(self.width - ICON_SIZE[0])
                    right_margin = self.width - col_width - page_width_so_far
                col_list: uif.HeaderList = uif.HeaderList(
                    name=column.stat_name,
                    parent=self,
                    header_row=uif.IconRow(text=column.stat_name, text_align=column.header_align, icon=column.header_icon),
                    data_rows=self.get_rows(column),
                    height = self.height - 8,
                    width = col_width,
                    should_freeze=True
                )
                col_list.margin = (left_margin, right_margin, 0, 0)
                col_list.overflow = (col_list.overflow[0], col_list.overflow[1], 0, 0)
                self.table.append(col_list)
        for column in self.table:
            self.add_child(column)

    def num_cols_in_current_page(self) -> int:
        return len(self.STAT_PAGES[self.page])

    def col_indices_for_page(self, page_num: int) -> List[int]:
        num_cols_so_far = 1
        for pnum in range(page_num):
            num_cols_so_far += len(self.STAT_PAGES[pnum][1])
        return list(range(num_cols_so_far, num_cols_so_far + len(self.STAT_PAGES[page_num][1])))

    def num_cols_total(self) -> int:
        return len(self.table)

    def get_rows(self, col: Column) -> List[uif.IconRow]:
        get_stat_value = col.get_stat
        get_stat_icon = col.get_icon
        rows = []
        for unit in self.data:
            val = get_stat_value(unit) if get_stat_value else ""
            icon = get_stat_icon(unit) if get_stat_icon else None
            rows.append(uif.IconRow(unit.name, text=str(val), icon=icon, text_align=col.header_align, font=col.font))
        return rows

    def is_scrolling(self) -> bool:
        return self.is_animating()

    def scroll_right(self):
        if self.page < self.MAX_PAGES:
            scroll_right_anim = component_scroll_anim(self.scroll, (min(self.scroll[0] + self.width, self.twidth - self.width), self.scroll[1]), 250)
            self.queue_animation(animations=[scroll_right_anim])
            self.page += 1

    def scroll_left(self):
        if self.page > 0:
            scroll_left_anim = component_scroll_anim(self.scroll, (self.scroll[0] - self.width, self.scroll[1]), 250)
            self.queue_animation(animations=[scroll_left_anim])
            self.page -= 1

    def scroll_down(self):
        for header_list in self.table:
            header_list.scroll_down()

    def scroll_up(self):
        for header_list in self.table:
            header_list.scroll_up()

    def get_page_num(self) -> int:
        return self.page

    def get_num_pages(self) -> int:
        return self.MAX_PAGES

    def get_page_title(self) -> str:
        return self.STAT_PAGES[self.page][0]

    def get_column_format_by_index(self, index: int) -> Column:
        all_cols = []
        for page in self.STAT_PAGES:
            for col in page[1]:
                all_cols.append(col)
        return all_cols[index]

    def cursor_hover(self) -> UnitObject | Tuple[str, Callable[[UnitObject], int | str]] | None:
        if self.cursor_pos[1] > 0: # we're hovering a unit, not our problem
            return
        elif self.cursor_pos == (0, 0): # we're hovering the name header, not our problem
            return
        elif self.cursor_pos[1] == 0 and self.cursor_pos[0] > 0: # we're hovering a table header
            col = self.get_column_format_by_index(self.cursor_pos[0] - 1)
            return (col.stat_name, col.sort_by)
        else:
            return None

    def update_cursor(self):
        if self.cursor_pos[1] == 0 and self.cursor_pos[0] > 0: # we're hovering a header
            # fancy math to position the cursor
            selected_list_left = self.layout_handler.generate_child_positions(True)[self.cursor_pos[0] - 1][0]
            if not self.table[self.cursor_pos[0] - 1].header_row.text.text: # purely an icon
                selected_list_text_offset = 0
            else:
                selected_list_text_offset = self.table[self.cursor_pos[0] - 1].header_row.get_text_topleft()[0]
            selected_list_left = selected_list_left + selected_list_text_offset - self.cursor_sprite.get_width()
            perturbation = CURSOR_PERTURBATION[ANIMATION_COUNTERS.fps6_360counter.count % 8]
            cursor_position = (selected_list_left + perturbation, 2)
            self.manual_surfaces.clear()
            self.add_surf(self.cursor_sprite, cursor_position)
        else:
            if self.manual_surfaces:
                self.manual_surfaces.clear()

    def to_surf(self, no_cull=False) -> engine.Surface:
        self.update_cursor()
        return super().to_surf(no_cull=no_cull)

class UnitInformationTable(uif.UIComponent):
    MENU_BOTTOM_BORDER_THICKNESS = 8
    def __init__(self, name: str = None, parent: uif.UIComponent = None, data: List[UnitObject] = None):
        super().__init__(name=name, parent=parent)
        self.page_num = 1
        self.data = data
        self.size = (WINWIDTH - 8, WINHEIGHT * 0.75) # specifically, 232 x 120
        self.overflow = (16, 16, 16, 0)
        self.margin = (0, 0, 0, 3)
        self.padding = (0, 0, 3, 0)
        self.props.v_alignment = uif.VAlignment.BOTTOM
        self.props.h_alignment = uif.HAlignment.CENTER

        self.initialize_background()

        self.cursor_sprite = SPRITES.get('menu_hand')

        # children layout
        self.props.layout = uif.UILayoutType.LIST
        self.props.list_style = uif.ListLayoutStyle.ROW

        self.cursor_pos = (0, 0)
        self.left_unit_name_list = None
        self.right_unit_data_grid = None

        self.initialize_components()

        # UIF X GUI crossover pog
        # we have to adjust for the uif internal overflow
        lscroll_topleft = tuple_add((0, 3), self.overflow[::2])
        rscroll_topleft = tuple_add((self.width - 8, 3), self.overflow[::2])
        self.lscroll_arrow = ScrollArrow('left', lscroll_topleft)
        self.rscroll_arrow = ScrollArrow('right', rscroll_topleft)

        self.scroll_bar = ScrollBar()
        self.scroll_bar_topright = tuple_add((self.width - 6, 15), self.overflow[::2])

        self.highlight_surf = create_highlight_surf(self.width - 8)
        self.highlight_cycle_time = 30

    @property
    def table_size(self) -> Tuple[int, int]:
        y_bound = len(self.data)
        x_bound = self.right_unit_data_grid.num_cols_total()
        return (x_bound, y_bound)

    def initialize_components(self):
        # if reinitializing
        prev_name_list_scroll = None
        prev_grid_scroll = None
        prev_page = None
        if self.left_unit_name_list:
            prev_name_list_scroll = self.left_unit_name_list.scroll
        if self.right_unit_data_grid:
            prev_grid_scroll = self.right_unit_data_grid.scroll
            prev_page = self.right_unit_data_grid.page

        # initialize name_column
        self.header_row = uif.IconRow(text='Name', icon=engine.create_surface(ICON_SIZE, True))
        self.name_rows: List[uif.IconRow] = self.generate_name_rows()
        self.left_unit_name_list = uif.HeaderList[uif.IconRow](name = 'unit_names',
                                                  parent = self,
                                                  header_row = self.header_row,
                                                  data_rows = self.name_rows,
                                                  height = self.height - self.MENU_BOTTOM_BORDER_THICKNESS,
                                                  width = '20%')
        self.left_unit_name_list.padding = (3, 0, 0, 0)
        overflow_list = list(self.left_unit_name_list.overflow)
        overflow_list[3] = 0
        self.left_unit_name_list.overflow = tuple(overflow_list)

        # init stats table
        self.right_unit_data_grid = UnitStatisticsTable('unit_statistics', self, data=self.data)

        if prev_name_list_scroll:
            self.left_unit_name_list.scroll = prev_name_list_scroll
        if prev_grid_scroll:
            self.right_unit_data_grid.scroll = prev_grid_scroll
            self.right_unit_data_grid.page = prev_page

        self.children.clear()
        self.add_child(self.left_unit_name_list)
        self.add_child(self.right_unit_data_grid)

    def set_data(self, data: List[UnitObject]):
        self.data = data
        self.initialize_components()

    def initialize_background(self):
        # background hackery
        background_surf = engine.create_surface(self.size, True)

        bottom_border_thickness = self.MENU_BOTTOM_BORDER_THICKNESS # we want the menu bg, but without the bottom border
        header_thickness = 20

        # make header
        menu_bg_before_processing = create_base_surf(self.width, header_thickness + bottom_border_thickness, 'menu_bg_white')
        translucent_menu_bg = image_mods.make_translucent(menu_bg_before_processing, 0.1)
        background_header = engine.subsurface(translucent_menu_bg, (0, 0, self.width, header_thickness))
        header_shadow: engine.Surface = image_mods.make_translucent(engine.image_load(SPRITES['header_shadow'].full_path, convert_alpha=True), 0.7)
        background_header.blit(header_shadow, (0, 10))

        # make body; we don't have to know the thickness of the top since we can just cut the entire top part off and replace it with our header
        body_menu_bg_before_processing = create_base_surf(self.width, self.height, 'menu_bg_base')
        translucent_body_bg = image_mods.make_translucent(body_menu_bg_before_processing, 0.1)
        background_body = engine.subsurface(translucent_body_bg, (0, header_thickness, self.width, self.height - header_thickness))

        # combine header and body
        background_surf.blit(background_header, (0, 0))
        background_surf.blit(background_body, (0, header_thickness))
        self.props.bg = background_surf

    def generate_name_rows(self):
        rows = []
        for unit in self.data:
            unit_sprite = unit.sprite.create_image('passive')
            unit_icon = uif.UIComponent()
            unit_icon.size = ICON_SIZE
            unit_icon.overflow = (12, 0, 12, 0) # the unit sprites are kind of enormous
            unit_icon.add_surf(unit_sprite, (-24, -24))
            row = uif.IconRow(unit.nid, text=unit.name, icon=unit_icon)
            row.overflow = (12, 0, 12, 0)
            rows.append(row)
        return rows

    def scroll_down(self):
        if self.cursor_pos[1] >= len(self.name_rows) - 1:
            return
        self.left_unit_name_list.scroll_down()
        self.right_unit_data_grid.scroll_down()

    def scroll_up(self):
        if self.cursor_pos[1] <= 1:
            return
        self.left_unit_name_list.scroll_up()
        self.right_unit_data_grid.scroll_up()

    def scroll_right(self):
        if self.cursor_pos[0] == self.right_unit_data_grid.num_cols_total():
            return
        self.right_unit_data_grid.scroll_right()

    def scroll_left(self):
        if self.cursor_pos[0] == 0 and self.get_page_num() == 0:
            return
        self.right_unit_data_grid.scroll_left()

    def get_page_num(self) -> int:
        return self.right_unit_data_grid.get_page_num()

    def get_num_pages(self) -> int:
        return self.right_unit_data_grid.get_num_pages()

    def get_page_title(self) -> str:
        return self.right_unit_data_grid.get_page_title()

    def update_unit_icons(self):
        for idx, row in enumerate(self.name_rows):
            if row.enabled and row.on_screen and idx > self.left_unit_name_list.scrolled_index - 1:
                unit = self.data[idx]
                unit_sprite = unit.sprite.create_image('passive')
                row.icon.manual_surfaces.clear()
                row.icon.add_surf(unit_sprite, (-24, -24))

    def update_highlight(self):
        if self.cursor_pos[0] < 0 or self.cursor_pos[1] < 0:
            if self.manual_surfaces:
                self.manual_surfaces.clear()
            return
        if self.cursor_pos[1] > 0: # we're hovering a unit, draw highlight
            # this is just math that allows highlight flicker to oscillate between 0 and 0.5
            highlight_flicker = abs((ANIMATION_COUNTERS.fps2_360counter.count % self.highlight_cycle_time) - self.highlight_cycle_time / 2) / (self.highlight_cycle_time * 1.25)

            colored_highlight = image_mods.make_white(self.highlight_surf, highlight_flicker)
            pos = (4, (0.75 + self.cursor_pos[1] - self.left_unit_name_list.scrolled_index) * self.left_unit_name_list.row_height)
            self.manual_surfaces.clear()
            self.add_surf(colored_highlight, pos, -1)
        elif self.cursor_pos == (0, 0): # we're hovering over the name header
            perturbation = CURSOR_PERTURBATION[ANIMATION_COUNTERS.fps6_360counter.count % 8]
            top_left = (1 + perturbation, self.padding[2] + 2) # magic position, don't worry about it
            self.manual_surfaces.clear()
            self.add_surf(self.cursor_sprite, top_left, 1)
        else: # we don't need to draw anything, let the table handle it
            if self.manual_surfaces:
                self.manual_surfaces.clear()

    def move_cursor(self, direction: Direction):
        new_cursor_pos = self.cursor_pos
        cx, cy = self.cursor_pos
        table_cols = self.right_unit_data_grid.col_indices_for_page(self.right_unit_data_grid.page)
        if direction == Direction.UP:
            if cy <= self.left_unit_name_list.scrolled_index + 2:
                if self.left_unit_name_list.is_scrolling():
                    return
                self.scroll_up()
            new_cursor_pos = (cx, cy - 1)
        elif direction == Direction.DOWN:
            if cy >= self.left_unit_name_list.scrolled_index + 5:
                if self.left_unit_name_list.is_scrolling():
                    return
                self.scroll_down()
            new_cursor_pos = (cx, cy + 1)
        elif direction == Direction.LEFT: # easy part is over.
            self.lscroll_arrow.pulse()
            if cx == 0 or cy > 0: # we're leftscrolling
                # can we even leftscroll?
                if self.right_unit_data_grid.page == 0: # no
                    pass
                else: # yes
                    if self.right_unit_data_grid.is_scrolling():
                        return
                    self.scroll_left()
                    if cy > 0: # we're leftscrolling from the grid itself
                        new_cursor_pos = (0, cy)
                    else: # leftscrolling from a header, preserve header location
                        new_cursor_pos = (table_cols[0] - 1,
                                          cy)
            elif cx > 0 and cy == 0: # we're shifting headers
                if cx == table_cols[0]: # we're on the first table header, change to the name header
                    new_cursor_pos = (0, 0)
                else: # we're not, which means move normally
                    new_cursor_pos = (cx - 1, cy)
        elif direction == Direction.RIGHT:
            self.rscroll_arrow.pulse()
            if cx == table_cols[-1] or cy > 0: # we're right scrolling
                # can we even rightscroll?
                if self.right_unit_data_grid.page == self.right_unit_data_grid.MAX_PAGES - 1: # no
                    pass
                else: # yes
                    if self.right_unit_data_grid.is_scrolling():
                        return
                    self.scroll_right()
                    new_cursor_pos = (0, cy)
            elif cy == 0: # we're shifting headers
                if cx == 0: # we're going from the name to the table
                    new_cursor_pos = (table_cols[0], cy)
                else: # we're moving inside the table
                    new_cursor_pos = (cx + 1, cy)
        self.cursor_pos = tclamp(new_cursor_pos, (0, 0), (self.table_size))

    def cursor_hover(self) -> UnitObject | Tuple[str, Callable[[UnitObject], int | str]] | None:
        if self.cursor_pos[1] > 0: # we're hovering a unit
            return self.data[self.cursor_pos[1] - 1]
        elif self.cursor_pos == (0, 0): # we're hovering the name header
            def sort_func(unit: UnitObject) -> str:
                return unit.name
            return (self.header_row.text.text, sort_func)
        elif self.cursor_pos[1] == 0 and self.cursor_pos[0] > 0: # we're hovering a table header
            return self.right_unit_data_grid.cursor_hover()
        else:
            return None

    def to_surf(self, no_cull=False) -> engine.Surface:
        self.update_unit_icons()
        self.update_highlight()
        surf = super().to_surf(no_cull)
        # draw scroll bars
        self.lscroll_arrow.draw(surf)
        self.rscroll_arrow.draw(surf)
        if len(self.data) > 6:
            self.scroll_bar.draw(surf, self.scroll_bar_topright, self.left_unit_name_list.scrolled_index, 6, len(self.data))
        return surf
