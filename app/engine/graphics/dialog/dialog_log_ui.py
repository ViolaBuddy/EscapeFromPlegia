from __future__ import annotations

from app.engine.fonts import FONT
from app.constants import WINWIDTH, WINHEIGHT

from app.engine.graphics.ui_framework.ui_framework import UIComponent
from app.engine.graphics.ui_framework.ui_framework_layout import UILayoutType, VAlignment, ListLayoutStyle
from app.engine.graphics.ui_framework.premade_components import TextComponent
from app.engine.graphics.ui_framework.premade_animations import component_scroll_anim

class DialogEntryComponent(UIComponent):
    def __init__(self, name, speaker, text, parent=None):
        super().__init__(name=name, parent=parent)

        self.props.layout = UILayoutType.LIST

        self.props.list_style = ListLayoutStyle.COLUMN
        self.speaker = TextComponent("speaker", speaker, self)
        self.speaker.padding = (5, 0, 0, 0)
        self.speaker.set_font(FONT['text-yellow'])

        self.text = TextComponent("dialog text", text, self)
        self.text.padding = (5, 5, 0, 10)
        self.text.set_num_lines(0)
        self.size = self.calculate_size()

        self.add_child(self.speaker)
        self.add_child(self.text)

    def calculate_size(self):
        width = self.parent.width
        height = self.text.height + self.speaker.height
        return (width, height)


class DialogLogContainer(UIComponent):
    def __init__(self, name, parent=None):
        super().__init__(name=name, parent=parent)
        self.props.layout = UILayoutType.LIST
        self.props.bg_color = (33, 33, 33, 225)
        self.props.list_style = ListLayoutStyle.COLUMN
        self.text_objects: List[TextComponent] = []
        self.scroll_height = self.parent.height

    def scroll_up_down(self, dist):
        self.scroll = (self.scroll[0], self.scroll[1] + dist)

    def scroll_all(self):
        self.scroll = (self.scroll[0], self.scroll_height)

    def update_scroll_height(self):
        scroll_height = 0
        for text in self.text_objects:
            scroll_height += text.height

        self.scroll_height = max(scroll_height, self.parent.height)
        self.height = self.scroll_height

    def add_entry(self, dialog_entry: DialogEntryComponent):
        self.add_child(dialog_entry)
        self.text_objects.append(dialog_entry)
        self.update_scroll_height()

    def remove_entry(self, entry_ui):
        self.remove_child(entry_ui.name)
        self.text_objects.remove(entry_ui)
        self.update_scroll_height()

    def get_last_entry(self):
        if self.text_objects:
            return self.text_objects[-1]
        else:
            return None


class DialogLogUI:
    entry_count = 0

    def __init__(self):
        self.base_component = UIComponent.create_base_component(WINWIDTH, WINHEIGHT)
        self.base_component.name = "base"

        self.log_container = DialogLogContainer('container', parent=self.base_component) # Component contains all the dialog log entries.
        self.base_component.add_child(self.log_container)

    def add_entry(self, speaker: str, text: str):
        # Create and add new entry to ui.
        entry = DialogEntryComponent(f"entry no. {self.entry_count}", speaker, text, parent=self.log_container)
        self.log_container.add_entry(entry)
        self.entry_count += 1
        return entry # Return ui component

    def remove_entry(self, entry: DialogEntryComponent):
        self.log_container.remove_entry(entry)
        self.entry_count -= 1

    def scroll_up(self):
        self.log_container.scroll_up_down(-20)

    def scroll_down(self):
        self.log_container.scroll_up_down(20)

    def scroll_all(self):
        self.log_container.scroll_all()

    def get_last_entry(self):
        return self.log_container.get_last_entry()

    def draw(self, surf):
        ui_surf = self.base_component.to_surf()
        surf.blit(ui_surf, (0, 0))
        return surf