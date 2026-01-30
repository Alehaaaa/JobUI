from PySide2 import QtWidgets, QtCore


class EditStudioDialog(QtWidgets.QDialog):
    studio_edited = QtCore.Signal(dict)

    def __init__(self, studio_data, parent=None):
        super(EditStudioDialog, self).__init__(parent)
        self.setWindowTitle(f"Edit {studio_data.get('name', 'Studio')}")
        self.resize(500, 400)
        self.studio_data = dict(studio_data)  # Make a copy

        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #cccccc;
                font-size: 14px;
                font-weight: bold;
            }
            QLineEdit, QComboBox {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                color: #ffffff;
                padding: 8px;
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #007acc;
            }
            QPushButton {
                background-color: #007acc;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0062a3;
            }
            QPushButton:pressed {
                background-color: #004d80;
            }
            QPushButton#cancel_btn {
                background-color: #3d3d3d;
            }
            QPushButton#cancel_btn:hover {
                background-color: #4d4d4d;
            }
        """)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setSpacing(15)
        self.layout.setContentsMargins(25, 25, 25, 25)

        # Title
        title = QtWidgets.QLabel("Edit Studio Details")
        title.setStyleSheet("font-size: 18px; color: white; margin-bottom: 10px;")
        self.layout.addWidget(title)

        # ID Warning
        id_warning = QtWidgets.QLabel(f"Editing ID: {self.studio_data.get('id')}")
        id_warning.setStyleSheet("color: #666; font-size: 12px; margin-bottom: 10px; font-style: italic;")
        self.layout.addWidget(id_warning)

        # Form Layout
        form_layout = QtWidgets.QFormLayout()
        form_layout.setSpacing(10)
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
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.clicked.connect(self.reject)

        self.save_btn = QtWidgets.QPushButton("Save Changes")
        self.save_btn.clicked.connect(self.on_save)

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
