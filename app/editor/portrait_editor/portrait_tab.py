from app.resources.resources import RESOURCES

# from app.data.database import DB

from app.extensions.custom_gui import ResourceListView
from app.editor.data_editor import SingleDatabaseEditor
from app.editor.base_database_gui import DatabaseTab

from app.editor.portrait_editor import portrait_model, portrait_properties

class PortraitDatabase(DatabaseTab):
    @classmethod
    def create(cls, parent=None):
        data = RESOURCES.portraits
        title = "Unit Portrait"
        right_frame = portrait_properties.PortraitProperties
        collection_model = portrait_model.PortraitModel
        deletion_criteria = None

        dialog = cls(data, title, right_frame, deletion_criteria,
                     collection_model, parent, button_text="Add New %s...",
                     view_type=ResourceListView)
        return dialog

# Testing
# Run "python -m app.editor.unit_editor.unit_tab" from main directory
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    RESOURCES.load('default.ltproj')
    # DB.load('default.ltproj')
    window = SingleDatabaseEditor(PortraitDatabase)
    window.show()
    app.exec_()
