from app.data.database import DB

from app.extensions.list_dialogs import MultiAttrListDialog
from app.extensions.list_models import DragDropMultiAttrListModel

class TranslationMultiModel(DragDropMultiAttrListModel):
    def create_new(self):
        self._data.add_new_default(DB)

    def change_watchers(self, data, attr, old_value, new_value):
        if attr == 'nid':
            self._data.update_nid(data, new_value)

class TranslationDialog(MultiAttrListDialog):
    @classmethod
    def create(cls):
        dlg = cls(DB.translations, "Translation", ("nid", "text"),
                  TranslationMultiModel, (None, None, None), set())
        return dlg