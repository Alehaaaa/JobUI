try:
    from PySide2 import QtCore, QtWidgets, QtGui
except ImportError:
    from PySide6 import QtCore, QtWidgets, QtGui


class EditStudioDialog(QtWidgets.QDialog):
    studio_edited = QtCore.Signal(dict)

    def __init__(self, studio_data, parent=None):
        super(EditStudioDialog, self).__init__(parent)
        self.setWindowTitle(f"Edit {studio_data.get('name', 'Studio')}")
        self.resize(500, 300)
        self.studio_data = dict(studio_data)  # Make a copy

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(15, 15, 15, 15)

        # Title
        title = QtWidgets.QLabel("Edit Studio Details")
        font = title.font()
        font.setPointSize(12)
        font.setBold(True)
        title.setFont(font)
        self.layout.addWidget(title)

        # ID Warning
        id_warning = QtWidgets.QLabel(f"Editing ID: {self.studio_data.get('id')}")
        w_font = id_warning.font()
        w_font.setItalic(True)
        id_warning.setFont(w_font)

        palette = id_warning.palette()
        palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor("gray"))
        id_warning.setPalette(palette)

        self.layout.addWidget(id_warning)

        # Form Layout
        form_layout = QtWidgets.QFormLayout()
        form_layout.setSpacing(8)
        self.layout.addLayout(form_layout)

        # Name
        self.name_input = QtWidgets.QLineEdit(self.studio_data.get("name", ""))
        form_layout.addRow("Name:", self.name_input)

        # Logo URL
        self.logo_input = QtWidgets.QLineEdit(self.studio_data.get("logo_url", ""))
        form_layout.addRow("Logo URL:", self.logo_input)

        # Careers URL
        self.careers_input = QtWidgets.QLineEdit(self.studio_data.get("careers_url", ""))
        form_layout.addRow("Careers URL:", self.careers_input)

        # Website
        self.website_input = QtWidgets.QLineEdit(self.studio_data.get("website", ""))
        form_layout.addRow("Website:", self.website_input)

        # Scraping Strategy
        self.strategy_input = QtWidgets.QLineEdit(self.studio_data.get("scraping_strategy", ""))
        form_layout.addRow("Strategy:", self.strategy_input)

        self.layout.addStretch()

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)

        self.save_btn = QtWidgets.QPushButton("Save Changes")
        self.save_btn.clicked.connect(self.on_save)

        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        self.layout.addLayout(btn_layout)

    def on_save(self):
        name = self.name_input.text().strip()

        if not name:
            QtWidgets.QMessageBox.warning(self, "Validation Error", "Name is required.")
            return

        # Update copy
        self.studio_data["name"] = name
        self.studio_data["logo_url"] = self.logo_input.text().strip()
        self.studio_data["careers_url"] = self.careers_input.text().strip()
        self.studio_data["website"] = self.website_input.text().strip()
        self.studio_data["scraping_strategy"] = self.strategy_input.text().strip()

        self.studio_edited.emit(self.studio_data)
        self.accept()
