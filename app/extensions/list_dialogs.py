from PyQt5.QtWidgets import QPushButton, QDialog, QDialogButtonBox, QGridLayout
from PyQt5.QtCore import Qt

from app.extensions.custom_gui import RightClickListView, RightClickTreeView, IntDelegate
from app.extensions.simple_list_models import SingleListModel, MultiAttrListModel

# === LIST DIALOGS ===========================================================
class SingleListDialog(QDialog):
    def __init__(self, data, title, parent=None):
        super().__init__(parent)
        self.initiate(data, title, parent)

        self.model = SingleListModel(self._data, title, self)
        self.view = RightClickListView(parent=self)
        self.view.setModel(self.model)

        self.placement(title)

    def initiate(self, data, title, parent):
        self.window = parent
        self._data = data

        self.setWindowTitle("%s Editor" % title)
        self.setStyleSheet("font: 10pt;")
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self.saved_data = self.save()

    def placement(self, title):
        layout = QGridLayout(self)
        layout.addWidget(self.view, 0, 0, 1, 2)
        self.setLayout(layout)

        self.add_button = QPushButton("Add %s" % title)
        self.add_button.clicked.connect(self.model.append)
        layout.addWidget(self.add_button, 1, 0, alignment=Qt.AlignLeft)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        layout.addWidget(self.buttonbox, 1, 1)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

    def save(self):
        return self._data

    def restore(self, data):
        self._data = data

    def accept(self):
        super().accept()

    def reject(self):
        self.restore(self.saved_data)
        super().reject()

class MultiAttrListDialog(SingleListDialog):
    def __init__(self, data, title, attrs, model=MultiAttrListModel, deletion_criteria=None, locked: set = None, parent=None):
        QDialog.__init__(self, parent)
        self.initiate(data, title, parent)

        self.model = model(self._data, attrs, self)
        if locked:
            self.model.edit_locked = locked
        self.view = RightClickTreeView(deletion_criteria, self)
        self.view.setModel(self.model)
        int_columns = [i for i, attr in enumerate(attrs) if type(getattr(self._data[0], attr)) == int]
        delegate = IntDelegate(self.view, int_columns)
        self.view.setItemDelegate(delegate)
        for col in range(len(attrs)):
            self.view.resizeColumnToContents(col)

        self.placement(title)

    def save(self):
        return self._data.save()

    def restore(self, data):
        self._data.restore(data)