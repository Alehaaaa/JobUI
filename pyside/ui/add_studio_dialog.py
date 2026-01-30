try:
    from PySide2 import QtCore, QtWidgets
except ImportError:
    from PySide6 import QtCore, QtWidgets


class AddStudioDialog(QtWidgets.QDialog):
    studio_added = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super(AddStudioDialog, self).__init__(parent)
        self.setWindowTitle("Add New Studio")
        self.resize(500, 300)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(15, 15, 15, 15)

        # Title
        # Native font handling if needed, or just let it inherit
        title = QtWidgets.QLabel("Add Studio Toolkit")
        font = title.font()
        font.setPointSize(12)
        font.setBold(True)
        title.setFont(font)
        self.layout.addWidget(title)

        # Form Layout
        form_layout = QtWidgets.QFormLayout()
        form_layout.setSpacing(8)
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
        self.cancel_btn.clicked.connect(self.reject)

        self.save_btn = QtWidgets.QPushButton("Add Studio")
        self.save_btn.clicked.connect(self.on_save)

        btn_layout.addStretch()
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
