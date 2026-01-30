from PySide2 import QtWidgets, QtCore


class AddStudioDialog(QtWidgets.QDialog):
    studio_added = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super(AddStudioDialog, self).__init__(parent)
        self.setWindowTitle("Add New Studio")
        self.resize(500, 400)
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
                selection-background-color: #007acc;
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
        title = QtWidgets.QLabel("Add Studio Toolkit")
        title.setStyleSheet("font-size: 18px; color: white; margin-bottom: 10px;")
        self.layout.addWidget(title)

        # Form Layout
        form_layout = QtWidgets.QFormLayout()
        form_layout.setSpacing(10)
        self.layout.addLayout(form_layout)

        # ID
        self.id_input = QtWidgets.QLineEdit()
        self.id_input.setPlaceholderText("e.g. disney")
        form_layout.addRow("ID:", self.id_input)

        # Name
        self.name_input = QtWidgets.QLineEdit()
        self.name_input.setPlaceholderText("e.g. Walt Disney Animation")
        form_layout.addRow("Name:", self.name_input)

        # Logo URL
        self.logo_input = QtWidgets.QLineEdit()
        self.logo_input.setPlaceholderText("https://...")
        form_layout.addRow("Logo URL:", self.logo_input)

        # Careers URL
        self.careers_input = QtWidgets.QLineEdit()
        self.careers_input.setPlaceholderText("https://...")
        form_layout.addRow("Careers URL:", self.careers_input)

        # Website
        self.website_input = QtWidgets.QLineEdit()
        self.website_input.setPlaceholderText("https://...")
        form_layout.addRow("Website:", self.website_input)

        # Scraping Strategy
        self.strategy_input = QtWidgets.QLineEdit()
        self.strategy_input.setPlaceholderText("e.g. greenhouse_html")
        form_layout.addRow("Strategy:", self.strategy_input)

        self.layout.addStretch()

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.clicked.connect(self.reject)

        self.save_btn = QtWidgets.QPushButton("Add Studio")
        self.save_btn.clicked.connect(self.on_save)

        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        self.layout.addLayout(btn_layout)

    def on_save(self):
        studio_id = self.id_input.text().strip()
        name = self.name_input.text().strip()

        if not studio_id or not name:
            QtWidgets.QMessageBox.warning(self, "Validation Error", "ID and Name are required.")
            return

        data = {
            "id": studio_id,
            "name": name,
            "logo_url": self.logo_input.text().strip(),
            "careers_url": self.careers_input.text().strip(),
            "website": self.website_input.text().strip(),
            "scraping_strategy": self.strategy_input.text().strip(),
        }

        self.studio_added.emit(data)
        self.accept()
