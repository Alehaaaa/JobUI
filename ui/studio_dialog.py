try:
    from PySide2 import QtCore, QtWidgets
except ImportError:
    from PySide6 import QtCore, QtWidgets
import json


class StudioDialog(QtWidgets.QDialog):
    """
    Unified dialog for Adding or Editing Studio configurations.
    If studio_data is provided, it operates in 'Edit' mode.
    """

    saved = QtCore.Signal(dict)

    @staticmethod
    def expand_json(data):
        """Recursively search for strings that are JSON and parse them."""
        if isinstance(data, dict):
            return {k: StudioDialog.expand_json(v) for k, v in data.items()}
        if isinstance(data, list):
            return [StudioDialog.expand_json(i) for i in data]
        if isinstance(data, str):
            s = data.strip()
            if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
                try:
                    parsed = json.loads(data)
                    return StudioDialog.expand_json(parsed)
                except Exception:
                    pass
        return data

    @staticmethod
    def compact_json(data):
        """Re-encode dicts/lists as compact strings if they are values in the root dict."""
        if not isinstance(data, dict):
            return data

        out = {}
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                # Convert back to compact string for compatibility
                out[k] = json.dumps(v, separators=(",", ":"))
            else:
                out[k] = v
        return out

    def __init__(self, studio_data=None, parent=None):
        super(StudioDialog, self).__init__(parent)
        self.studio_data = dict(studio_data) if studio_data else None
        self.is_edit = self.studio_data is not None

        mode_title = "Edit" if self.is_edit else "Add"
        self.setWindowTitle(f"{mode_title} Studio")
        self.setMinimumWidth(600)
        self.setMinimumHeight(650)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(15, 15, 15, 15)

        # -- Header --
        title_lbl = QtWidgets.QLabel(f"{mode_title} Studio Configuration")
        font = title_lbl.font()
        font.setBold(True)
        font.setPointSize(11)
        title_lbl.setFont(font)
        self.layout.addWidget(title_lbl)

        # -- ID Info/Input --
        id_layout = QtWidgets.QHBoxLayout()
        id_lbl = QtWidgets.QLabel("<b>Internal ID:</b>")
        id_lbl.setFixedWidth(100)
        id_layout.addWidget(id_lbl)

        if self.is_edit:
            self.id_display = QtWidgets.QLabel(self.studio_data.get("id", ""))
            self.id_display.setStyleSheet("color: #888;")
            id_layout.addWidget(self.id_display)
        else:
            self.id_input = QtWidgets.QLineEdit()
            self.id_input.setPlaceholderText("internal_id (e.g. disney)")
            id_layout.addWidget(self.id_input)

        id_layout.addStretch()
        self.layout.addLayout(id_layout)

        # -- Scroll Area for Form --
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.container = QtWidgets.QWidget()
        self.form_layout = QtWidgets.QVBoxLayout(self.container)
        self.form_layout.setSpacing(15)
        self.scroll.setWidget(self.container)
        self.layout.addWidget(self.scroll)

        # -- 1. Basic Info Section --
        basic_group = QtWidgets.QGroupBox("Basic Information")
        basic_form = QtWidgets.QFormLayout(basic_group)
        basic_form.setSpacing(8)

        self.name_input = QtWidgets.QLineEdit()
        self.name_input.setPlaceholderText("Studio Display Name")
        basic_form.addRow("Display Name:", self.name_input)

        self.logo_input = QtWidgets.QLineEdit()
        self.logo_input.setPlaceholderText("https://url.to/logo.png")
        basic_form.addRow("Logo URL:", self.logo_input)

        self.careers_input = QtWidgets.QLineEdit()
        self.careers_input.setPlaceholderText("Scraping target URL")
        basic_form.addRow("Careers URL:", self.careers_input)

        self.website_input = QtWidgets.QLineEdit()
        self.website_input.setPlaceholderText("Studio website")
        basic_form.addRow("Website:", self.website_input)

        self.form_layout.addWidget(basic_group)

        # -- 2. Scraping Strategy --
        strat_group = QtWidgets.QGroupBox("Scraping Strategy")
        strat_vbox = QtWidgets.QVBoxLayout(strat_group)

        h_strat = QtWidgets.QHBoxLayout()
        self.radio_html = QtWidgets.QRadioButton("HTML (CSS Selectors)")
        self.radio_json = QtWidgets.QRadioButton("JSON (API Paths)")
        self.radio_html.setChecked(True)
        self.btn_group_strat = QtWidgets.QButtonGroup(self)
        self.btn_group_strat.addButton(self.radio_html)
        self.btn_group_strat.addButton(self.radio_json)
        h_strat.addWidget(self.radio_html)
        h_strat.addWidget(self.radio_json)
        h_strat.addStretch()
        strat_vbox.addLayout(h_strat)

        self.tabs = QtWidgets.QTabWidget()
        strat_vbox.addWidget(self.tabs)

        # --- TAB: Mapping ---
        self.tab_mapping = QtWidgets.QWidget()
        map_vbox = QtWidgets.QVBoxLayout(self.tab_mapping)
        self.stack_root = QtWidgets.QStackedWidget()
        map_vbox.addWidget(self.stack_root)

        # HTML Root
        self.page_html_root = QtWidgets.QWidget()
        html_root_form = QtWidgets.QFormLayout(self.page_html_root)
        self.html_container = QtWidgets.QLineEdit()
        html_root_form.addRow("Container:", self.html_container)

        # JSON Root
        self.page_json_root = QtWidgets.QWidget()
        json_root_form = QtWidgets.QFormLayout(self.page_json_root)
        self.json_path = QtWidgets.QLineEdit()
        json_root_form.addRow("Items Path:", self.json_path)

        self.stack_root.addWidget(self.page_html_root)
        self.stack_root.addWidget(self.page_json_root)

        mapping_group = QtWidgets.QGroupBox("Field Mappings")
        mapping_vbox = QtWidgets.QVBoxLayout(mapping_group)

        self.field_title, self.field_title_opts = self._add_field(mapping_vbox, "Title", options=["source"])
        self.field_link, self.field_link_opts = self._add_field(
            mapping_vbox, "Link", options=["source", "attr", "prefix", "suffix"]
        )
        self.field_location, self.field_loc_opts = self._add_field(
            mapping_vbox, "Location", options=["source", "index", "regex", "suffix", "remove_from_title"]
        )
        self.find_prev_widget, self.field_find_prev = self._add_labelled_field(mapping_vbox, "Find Prev (HTML):")

        map_vbox.addWidget(mapping_group)
        self.tab_mapping.setLayout(map_vbox)
        self.tabs.addTab(self.tab_mapping, "Mappings")

        # --- TAB: Request ---
        self.tab_request = QtWidgets.QWidget()
        req_form = QtWidgets.QFormLayout(self.tab_request)
        self.req_method = QtWidgets.QComboBox()
        self.req_method.addItems(["GET", "POST"])
        req_form.addRow("HTTP Method:", self.req_method)
        self.req_params = QtWidgets.QPlainTextEdit()
        self.req_params.setPlaceholderText('JSON query parameters (e.g. {"category": "vfx"})')
        self.req_params.setFixedHeight(80)
        req_form.addRow("Params:", self.req_params)
        self.req_payload = QtWidgets.QPlainTextEdit()
        self.req_payload.setFixedHeight(80)
        req_form.addRow("Payload:", self.req_payload)
        self.req_headers = QtWidgets.QPlainTextEdit()
        self.req_headers.setFixedHeight(80)
        req_form.addRow("Headers:", self.req_headers)
        self.tabs.addTab(self.tab_request, "Request")

        # --- TAB: Filters ---
        self.tab_filters = QtWidgets.QWidget()
        filt_form = QtWidgets.QFormLayout(self.tab_filters)
        self.filter_key = QtWidgets.QLineEdit()
        filt_form.addRow("Filter Key:", self.filter_key)
        self.filter_sw = QtWidgets.QLineEdit()
        filt_form.addRow("Starts With:", self.filter_sw)
        self.tabs.addTab(self.tab_filters, "JSON Filters")

        self.form_layout.addWidget(strat_group)

        # -- Footer --
        btn_layout = QtWidgets.QHBoxLayout()
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setFixedHeight(26)

        save_label = "Update Studio" if self.is_edit else "Add Studio"
        self.save_btn = QtWidgets.QPushButton(save_label)
        self.save_btn.clicked.connect(self.on_save)
        self.save_btn.setFixedHeight(26)
        self.save_btn.setDefault(True)

        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        self.layout.addLayout(btn_layout)

        # -- Connections --
        self.radio_html.toggled.connect(self._on_strat_changed)

        if self.is_edit:
            self.init_data()
        else:
            self._on_strat_changed()  # Force initial visibility state

    def _on_strat_changed(self):
        is_html = self.radio_html.isChecked()
        self.stack_root.setCurrentIndex(0 if is_html else 1)
        self.tabs.setTabEnabled(2, not is_html)
        self.find_prev_widget.setVisible(is_html)

    def _add_field(self, parent_layout, label, options=None):
        container = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(2)
        main_h = QtWidgets.QHBoxLayout()
        lbl = QtWidgets.QLabel(f"<b>{label}:</b>")
        lbl.setFixedWidth(100)
        main_h.addWidget(lbl)
        main_input = QtWidgets.QLineEdit()
        main_h.addWidget(main_input)
        vbox.addLayout(main_h)
        opt_widgets = {}
        if options:
            opt_h = QtWidgets.QHBoxLayout()
            opt_h.setContentsMargins(110, 0, 0, 0)
            opt_h.setSpacing(8)
            for opt in options:
                if opt == "remove_from_title":
                    cb = QtWidgets.QCheckBox("Clean Title")
                    cb.setStyleSheet("font-size: 10px;")
                    opt_h.addWidget(cb)
                    opt_widgets[opt] = cb
                elif opt == "source":
                    h = QtWidgets.QHBoxLayout()
                    h.setSpacing(3)
                    lbl = QtWidgets.QLabel("source:")
                    lbl.setStyleSheet("font-size: 10px; color: #888;")
                    combo = QtWidgets.QComboBox()
                    combo.addItems(["item", "url"])
                    combo.setFixedHeight(18)
                    combo.setStyleSheet("font-size: 10px;")
                    h.addWidget(lbl)
                    h.addWidget(combo)
                    opt_h.addLayout(h)
                    opt_widgets[opt] = combo
                else:
                    h = QtWidgets.QHBoxLayout()
                    h.setSpacing(3)
                    lbl = QtWidgets.QLabel(f"{opt}:")
                    lbl.setStyleSheet("font-size: 10px; color: #888;")
                    edit = QtWidgets.QLineEdit()
                    edit.setFixedHeight(18)
                    edit.setStyleSheet("font-size: 10px;")
                    if opt in ["index", "attr"]:
                        edit.setFixedWidth(50)
                    h.addWidget(lbl)
                    h.addWidget(edit)
                    opt_h.addLayout(h)
                    opt_widgets[opt] = edit
            opt_h.addStretch()
            vbox.addLayout(opt_h)
        parent_layout.addWidget(container)
        parent_layout.addSpacing(4)
        return (main_input, opt_widgets) if options else main_input

    def _add_labelled_field(self, parent_layout, label, placeholder=""):
        container = QtWidgets.QWidget()
        h = QtWidgets.QHBoxLayout(container)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(2)
        lbl = QtWidgets.QLabel(f"<b>{label}</b>")
        lbl.setFixedWidth(100)
        h.addWidget(lbl)
        edit = QtWidgets.QLineEdit()
        edit.setPlaceholderText(placeholder)
        h.addWidget(edit)
        parent_layout.addWidget(container)
        parent_layout.addSpacing(4)
        return container, edit

    def init_data(self):
        if not self.studio_data:
            return

        self.name_input.setText(self.studio_data.get("name", ""))
        logo_url = self.studio_data.get("logo_url", "")
        self.logo_input.setText(logo_url)

        c_url = self.studio_data.get("careers_url", "")
        if isinstance(c_url, list):
            self.careers_input.setText(", ".join(c_url))
        else:
            self.careers_input.setText(str(c_url))

        self.website_input.setText(self.studio_data.get("website", ""))

        scrap = self.studio_data.get("scraping", {})
        mapping = scrap.get("map", {})
        strat = scrap.get("strategy", "html")

        if scrap.get("url_location_regex"):
            # Migration path: if old field exists, put it in location source
            self.field_location.setText("")
            self.field_loc_opts["source"].setCurrentText("url")
            self.field_loc_opts["regex"].setText(scrap.get("url_location_regex"))

        if strat == "json":
            self.radio_json.setChecked(True)
            self.json_path.setText(scrap.get("path", ""))

            # Title
            t = mapping.get("title", "")
            if isinstance(t, dict):
                self.field_title.setText(t.get("path", ""))
                if "source" in t:
                    self.field_title_opts["source"].setCurrentText(t["source"])
            else:
                self.field_title.setText(str(t))

            # Location
            loc = mapping.get("location", "")
            if isinstance(loc, dict):
                self.field_location.setText(loc.get("path", ""))
                if "source" in loc:
                    self.field_loc_opts["source"].setCurrentText(loc["source"])
                self.field_loc_opts["regex"].setText(loc.get("regex", ""))
            else:
                self.field_location.setText(str(loc))

            link = mapping.get("link", "")
            if isinstance(link, dict):
                self.field_link.setText(link.get("path", ""))
                if "source" in link:
                    self.field_link_opts["source"].setCurrentText(link["source"])
                self.field_link_opts["prefix"].setText(link.get("prefix", ""))
                self.field_link_opts["suffix"].setText(link.get("suffix", ""))
            else:
                self.field_link.setText(str(link))
            # Filter
            f = scrap.get("filter", {})
            self.filter_key.setText(f.get("key", ""))
            self.filter_sw.setText(f.get("startswith", ""))
        else:
            self.radio_html.setChecked(True)
            self.html_container.setText(scrap.get("container", ""))
            # Title
            t = mapping.get("title", "")
            if isinstance(t, dict):
                self.field_title.setText(t.get("selector", ""))
                self.field_find_prev.setText(t.get("find_previous", ""))
                if "source" in t:
                    self.field_title_opts["source"].setCurrentText(t["source"])
            else:
                self.field_title.setText(str(t))

            # Link
            link = mapping.get("link", "")
            if isinstance(link, dict):
                self.field_link.setText(link.get("selector", ""))
                self.field_link_opts["attr"].setText(link.get("attr", "href"))
                self.field_link_opts["prefix"].setText(link.get("prefix", ""))
                self.field_link_opts["suffix"].setText(link.get("suffix", ""))
                if "source" in link:
                    self.field_link_opts["source"].setCurrentText(link["source"])
            else:
                self.field_link.setText(str(link))

            # Location
            loc = mapping.get("location", "")
            if isinstance(loc, dict):
                self.field_location.setText(loc.get("selector", ""))
                self.field_loc_opts["index"].setText(loc.get("index", ""))
                self.field_loc_opts["regex"].setText(loc.get("regex", ""))
                self.field_loc_opts["suffix"].setText(loc.get("suffix", ""))
                if "source" in loc:
                    self.field_loc_opts["source"].setCurrentText(loc["source"])
            else:
                self.field_location.setText(str(loc))
            self.field_loc_opts["remove_from_title"].setChecked(mapping.get("remove_location_from_title", False))

        # Request
        self.req_method.setCurrentText(scrap.get("method", "GET"))

        # Pretty-print Request fields with expanded JSON strings for better editing
        if "params" in scrap:
            pretty_params = StudioDialog.expand_json(scrap["params"])
            self.req_params.setPlainText(json.dumps(pretty_params, indent=2))

        if "payload" in scrap:
            pretty_payload = StudioDialog.expand_json(scrap["payload"])
            self.req_payload.setPlainText(json.dumps(pretty_payload, indent=2))

        if "headers" in scrap:
            pretty_headers = StudioDialog.expand_json(scrap["headers"])
            self.req_headers.setPlainText(json.dumps(pretty_headers, indent=2))
        self._on_strat_changed()

    def on_save(self):
        sid = self.studio_data.get("id") if self.is_edit else self.id_input.text().strip()
        name = self.name_input.text().strip()

        if not sid or not name:
            QtWidgets.QMessageBox.warning(self, "Validation Error", "ID and Name are required.")
            return

        is_html = self.radio_html.isChecked()
        scrap = {"strategy": "html" if is_html else "json"}
        mapping = {}

        def build_map(input_field, options, key_name):
            val = input_field.text().strip()
            src = options.get("source").currentText() if "source" in options else "item"

            # Build object if any advanced option is set
            is_complex = src != "item"
            for k, v in options.items():
                if k == "source":
                    continue
                if isinstance(v, QtWidgets.QLineEdit) and v.text().strip():
                    is_complex = True

            if not is_complex:
                return val

            m = {("selector" if is_html else "path"): val}
            if src != "item":
                m["source"] = src
            for k, v in options.items():
                if k == "source":
                    continue
                if isinstance(v, QtWidgets.QLineEdit):
                    txt = v.text().strip()
                    if txt:
                        m[k] = txt
                elif isinstance(v, QtWidgets.QCheckBox):
                    # remove_from_title is handled specially in some cases but let's see
                    pass
            return m

        mapping["title"] = build_map(self.field_title, self.field_title_opts, "title")
        mapping["link"] = build_map(self.field_link, self.field_link_opts, "link")
        mapping["location"] = build_map(self.field_location, self.field_loc_opts, "location")

        if self.field_loc_opts["remove_from_title"].isChecked():
            mapping["remove_location_from_title"] = True

        if is_html:
            fp = self.field_find_prev.text().strip()
            if fp:
                # If title is already a dict from build_map, update it. Otherwise, create a new dict.
                if isinstance(mapping["title"], dict):
                    mapping["title"]["find_previous"] = fp
                else:
                    mapping["title"] = {"selector": mapping["title"], "find_previous": fp}
        else:
            scrap["path"] = self.json_path.text().strip()
            fk = self.filter_key.text().strip()
            fs = self.filter_sw.text().strip()
            if fk and fs:
                scrap["filter"] = {"key": fk, "startswith": fs}

        scrap["map"] = mapping

        # Method/Params/Payload/Headers
        if self.req_method.currentText() == "POST":
            scrap["method"] = "POST"

        pm = self.req_params.toPlainText().strip()
        if pm:
            try:
                p_obj = json.loads(pm)
                # Compact any nested objects back to strings for site compatibility
                scrap["params"] = StudioDialog.compact_json(p_obj)
            except Exception:
                pass

        pl = self.req_payload.toPlainText().strip()
        if pl:
            try:
                p_obj = json.loads(pl)
                # For Payload, we usually keep it as a real object unless it's a specific Workday-style thing.
                # But to follow "formatted for compatibility", we perform the same compaction check.
                scrap["payload"] = StudioDialog.compact_json(p_obj)
            except Exception:
                pass

        hd = self.req_headers.toPlainText().strip()
        if hd:
            try:
                p_obj = json.loads(hd)
                scrap["headers"] = StudioDialog.compact_json(p_obj)
            except Exception:
                pass

        if not self.studio_data:
            self.studio_data = {"id": sid}

        c_url_text = self.careers_input.text().strip()
        if "," in c_url_text or ";" in c_url_text:
            # Split by comma or semicolon and clean up
            import re

            c_urls = [u.strip() for u in re.split(r"[,;]", c_url_text) if u.strip()]
            careers_url = c_urls if len(c_urls) > 1 else c_urls[0] if c_urls else ""
        else:
            careers_url = c_url_text

        self.studio_data.update(
            {
                "name": name,
                "logo_url": self.logo_input.text().strip(),
                "careers_url": careers_url,
                "website": self.website_input.text().strip(),
                "scraping": scrap,
            }
        )

        self.saved.emit(self.studio_data)
        self.accept()
