try:
    from PySide2 import QtCore, QtWidgets
except ImportError:
    from PySide6 import QtCore, QtWidgets

import json
import re

from .flow_layout import FlowLayout
from .widgets import WaitingSpinner, ClickableLabel
from .studio_test import MockBrowser, TestWorker, TestPreviewDialog


class StudioDialog(QtWidgets.QDialog):
    """
    Unified dialog for Adding or Editing Studio configurations.
    """
    saved = QtCore.Signal(dict)

    @staticmethod
    def expand_json_strings(data):
        if isinstance(data, dict):
            return {key: StudioDialog.expand_json_strings(value) for key, value in data.items()}
        if isinstance(data, list):
            return [StudioDialog.expand_json_strings(item) for item in data]
        if isinstance(data, str):
            trimmed_str = data.strip()
            if (trimmed_str.startswith("{") and trimmed_str.endswith("}")) or (trimmed_str.startswith("[") and trimmed_str.endswith("]")):
                try:
                    parsed_json = json.loads(data)
                    return StudioDialog.expand_json_strings(parsed_json)
                except Exception:
                    pass
        return data

    @staticmethod
    def compact_json_objects(data):
        if not isinstance(data, dict):
            return data
        compacted_data = {}
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                compacted_data[key] = json.dumps(value, separators=(",", ":"))
            else:
                compacted_data[key] = value
        return compacted_data

    def __init__(self, studio_data=None, parent=None, existing_ids=None, config_manager=None):
        super(StudioDialog, self).__init__(parent)
        self.studio_data = dict(studio_data) if studio_data else None
        self.is_edit_mode = self.studio_data is not None
        self.existing_studio_ids = existing_ids or []
        self.config_manager = config_manager
        
        self.last_test_jobs = []
        self.last_test_config = None
        self.last_test_logo_path = None
        self.test_worker = None
        
        self.interacted_fields = set()
        self.mandatory_labels = {}
        self.regex_error_labels = {}
        self.regex_input_fields = {}
        self.initial_studio_config = None

        mode_title = "Edit" if self.is_edit_mode else "Add"
        self.setWindowTitle(mode_title + " Studio")
        self.setMinimumWidth(720)
        self.setMinimumHeight(650)

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setSpacing(12)
        self.main_layout.setContentsMargins(15, 15, 15, 15)

        title_label = QtWidgets.QLabel(mode_title + " Studio Configuration")
        f = title_label.font()
        f.setBold(True)
        f.setPointSize(12)
        title_label.setFont(f)
        self.main_layout.addWidget(title_label)

        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.content_container = QtWidgets.QWidget()
        self.content_layout = QtWidgets.QVBoxLayout(self.content_container)
        self.content_layout.setSpacing(15)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_area.setWidget(self.content_container)
        self.main_layout.addWidget(self.scroll_area)

        identity_group = QtWidgets.QGroupBox("Studio Identity")
        self.identity_form = QtWidgets.QFormLayout(identity_group)
        self.identity_form.setLabelAlignment(QtCore.Qt.AlignRight)
        self.identity_form.setSpacing(10)
        self.identity_form.setContentsMargins(15, 15, 15, 15)

        if not self.is_edit_mode:
            self.id_input = QtWidgets.QLineEdit()
            self.id_input.setPlaceholderText("internal_id")
            self.id_input.textChanged.connect(lambda: self._on_field_interacted("id"))
            self._add_mandatory_row("Internal ID *:", self.id_input, "id")
        else:
            self.id_display = QtWidgets.QLabel(self.studio_data.get("id", ""))
            self.id_display.setStyleSheet("color: #888; font-family: monospace;")
            self.identity_form.addRow("Internal ID:", self.id_display)

        self.name_input = QtWidgets.QLineEdit()
        self.name_input.textChanged.connect(self._on_studio_name_changed)
        self._add_mandatory_row("Name *:", self.name_input, "name")

        c_row = QtWidgets.QHBoxLayout()
        self.careers_input = QtWidgets.QLineEdit()
        self.careers_input.textChanged.connect(lambda: self._on_field_interacted("careers"))
        c_row.addWidget(self.careers_input, 1)
        btn_p_c = self._create_utility_button("🔗", "Preview Careers")
        btn_p_c.clicked.connect(lambda: self._open_internal_browser(self.careers_input.text()))
        c_row.addWidget(btn_p_c)
        self._add_mandatory_row("Careers URL *:", c_row, "careers")

        w_row = QtWidgets.QHBoxLayout()
        self.website_input = QtWidgets.QLineEdit()
        w_row.addWidget(self.website_input, 1)
        btn_p_w = self._create_utility_button("🔗", "Preview Website")
        btn_p_w.clicked.connect(lambda: self._open_internal_browser(self.website_input.text()))
        w_row.addWidget(btn_p_w)
        self.identity_form.addRow("Website:", w_row)

        l_row = QtWidgets.QHBoxLayout()
        self.logo_input = QtWidgets.QLineEdit()
        l_row.addWidget(self.logo_input, 1)
        btn_p_l = self._create_utility_button("🖼️", "Preview Logo")
        btn_p_l.clicked.connect(lambda: self._open_internal_browser(self.logo_input.text()))
        l_row.addWidget(btn_p_l)
        self.identity_form.addRow("Logo URL:", l_row)
        
        self.content_layout.addWidget(identity_group)

        strategy_group = QtWidgets.QGroupBox("Scraping Strategy")
        s_layout = QtWidgets.QVBoxLayout(strategy_group)
        s_sel = QtWidgets.QHBoxLayout()
        self.radio_html_strategy = QtWidgets.QRadioButton("HTML")
        self.radio_json_strategy = QtWidgets.QRadioButton("JSON")
        self.radio_html_strategy.setChecked(True)
        self.strategy_button_group = QtWidgets.QButtonGroup(self)
        self.strategy_button_group.addButton(self.radio_html_strategy)
        self.strategy_button_group.addButton(self.radio_json_strategy)
        s_sel.addWidget(self.radio_html_strategy)
        s_sel.addWidget(self.radio_json_strategy)
        s_sel.addStretch()
        s_layout.addLayout(s_sel)
        
        self.strategy_tabs = QtWidgets.QTabWidget()
        self.strategy_tabs.currentChanged.connect(self._on_tab_switched)
        s_layout.addWidget(self.strategy_tabs)

        self.mapping_tab = QtWidgets.QWidget()
        m_layout = QtWidgets.QVBoxLayout(self.mapping_tab)
        self.root_selector_stack = QtWidgets.QStackedWidget()
        
        self.html_root_page = QtWidgets.QWidget()
        hr_layout = QtWidgets.QHBoxLayout(self.html_root_page)
        self.label_html_root = QtWidgets.QLabel("<b>Container *:</b>")
        self.html_container_input = QtWidgets.QLineEdit()
        self.html_container_input.textChanged.connect(lambda: self._on_field_interacted("html_root"))
        hr_layout.addWidget(self.label_html_root)
        hr_layout.addWidget(self.html_container_input)
        self.mandatory_labels["html_root"] = self.label_html_root
        
        self.json_root_page = QtWidgets.QWidget()
        jr_layout = QtWidgets.QHBoxLayout(self.json_root_page)
        self.label_json_root = QtWidgets.QLabel("<b>JSON Path *:</b>")
        self.json_items_path_input = QtWidgets.QLineEdit()
        self.json_items_path_input.textChanged.connect(lambda: self._on_field_interacted("json_root"))
        jr_layout.addWidget(self.label_json_root)
        jr_layout.addWidget(self.json_items_path_input)
        self.mandatory_labels["json_root"] = self.label_json_root

        self.root_selector_stack.addWidget(self.html_root_page)
        self.root_selector_stack.addWidget(self.json_root_page)
        m_layout.addWidget(self.root_selector_stack)
        
        opts_list = ["source", "attr", "index", "regex", "prefix", "suffix", "find_previous", "find_next_sibling"]
        self.title_mapping_input, self.title_mapping_options = self._add_field_mapping_card(m_layout, "Title", opts_list + ["remove_from_title"])
        self.link_mapping_input, self.link_mapping_options = self._add_field_mapping_card(m_layout, "Link", opts_list)
        self.location_mapping_input, self.location_mapping_options = self._add_field_mapping_card(m_layout, "Location", opts_list)
        
        m_layout.addStretch()
        self.strategy_tabs.addTab(self.mapping_tab, "Mappings")

        self.request_tab = QtWidgets.QWidget()
        req_layout = QtWidgets.QVBoxLayout(self.request_tab)
        
        method_layout = QtWidgets.QHBoxLayout()
        method_layout.addWidget(QtWidgets.QLabel("<b>HTTP Method:</b>"))
        self.request_method_combo = QtWidgets.QComboBox()
        self.request_method_combo.addItems(["GET", "POST"])
        self.request_method_combo.currentTextChanged.connect(lambda: self._on_field_interacted("method"))
        method_layout.addWidget(self.request_method_combo)
        method_layout.addStretch()
        req_layout.addLayout(method_layout)
        
        self.request_params_input = self._create_json_text_input("Parameters:", req_layout)
        self.request_payload_input = self._create_json_text_input("Payload:", req_layout)
        self.request_headers_input = self._create_json_text_input("Headers:", req_layout)
        self.strategy_tabs.addTab(self.request_tab, "Request")

        self.strategy_tabs.addTab(QtWidgets.QWidget(), "Filters")
        self.content_layout.addWidget(strategy_group)

        footer = QtWidgets.QHBoxLayout()
        self.test_spinner = WaitingSpinner()
        self.test_spinner.setFixedSize(16, 16)
        self.test_spinner.hide()
        
        self.test_status_label = ClickableLabel("")
        self.test_status_label.setStyleSheet("font-size: 11px;")
        self.test_status_label.clicked.connect(self.on_show_test_preview)
        
        footer.addWidget(self.test_spinner)
        footer.addWidget(self.test_status_label)
        footer.addStretch()
        
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.test_btn = QtWidgets.QPushButton("Test")
        self.test_btn.clicked.connect(self.on_test_config)
        
        btn_label = "Update Studio" if self.is_edit_mode else "Add Studio"
        self.save_btn = QtWidgets.QPushButton(btn_label)
        self.save_btn.clicked.connect(self.on_save_config)
        self.save_btn.setDefault(True)
        
        footer.addWidget(self.cancel_btn)
        footer.addWidget(self.test_btn)
        footer.addWidget(self.save_btn)
        self.main_layout.addLayout(footer)
        
        self.radio_html_strategy.toggled.connect(self._on_tab_switched)
        if self.is_edit_mode:
            self.interacted_fields.update(["name", "careers", "html_root", "json_root"])
            self.load_studio_data()
        else:
            self._on_tab_switched(0)
            
        self._connect_all_fields()
        self.initial_studio_config = self._build_studio_config_dict()
        self._validate_all_fields(show_visual_errors=self.is_edit_mode)
        self._check_for_changes()

    def _create_utility_button(self, icon, tip):
        b = QtWidgets.QPushButton(icon)
        b.setFixedSize(24, 24)
        b.setToolTip(tip)
        b.setCursor(QtCore.Qt.PointingHandCursor)
        b.setStyleSheet("QPushButton { background: rgba(128,128,128,20); border: 1px solid rgba(128,128,128,30); border-radius: 3px; }")
        return b

    def _open_internal_browser(self, url):
        if not url:
            return
        url = url.strip()
        if not (url.startswith("http") or url.startswith("/")):
            return
        if url.startswith("/"):
            base = self.website_input.text().strip() or self.careers_input.text().strip()
            if base:
                url = base.rstrip('/') + url
        d = MockBrowser(url, self)
        d.exec_()

    def _on_field_interacted(self, k):
        self.interacted_fields.add(k)
        self._validate_field(k)
        self._check_for_changes()

    def _check_for_changes(self):
        if self.initial_studio_config is None:
            return
        current = self._build_studio_config_dict()
        has_changed = current != self.initial_studio_config
        self.save_btn.setEnabled(has_changed)
        # Visual hint for disabled state
        if has_changed:
            self.save_btn.setStyleSheet("")
        else:
            self.save_btn.setStyleSheet("color: #777; background: rgba(128,128,128,10);")

    def _connect_all_fields(self):
        # Basic fields
        self.website_input.textChanged.connect(lambda: self._on_field_interacted("website"))
        self.logo_input.textChanged.connect(lambda: self._on_field_interacted("logo"))
        
        # Mapping inputs
        for inp in [self.title_mapping_input, self.link_mapping_input, self.location_mapping_input]:
            inp.textChanged.connect(lambda: self._on_field_interacted("mapping"))
            
        # Mapping options
        for opts in [self.title_mapping_options, self.link_mapping_options, self.location_mapping_options]:
            for w in opts.values():
                if isinstance(w, QtWidgets.QCheckBox):
                    w.toggled.connect(lambda: self._on_field_interacted("mapping_opt"))
                elif isinstance(w, QtWidgets.QSpinBox):
                    w.valueChanged.connect(lambda: self._on_field_interacted("mapping_opt"))
                elif isinstance(w, QtWidgets.QLineEdit):
                    w.textChanged.connect(lambda: self._on_field_interacted("mapping_opt"))

        # Request fields
        for inp in [self.request_params_input, self.request_payload_input, self.request_headers_input]:
            inp.textChanged.connect(lambda: self._on_field_interacted("request"))
        self.request_method_combo.currentTextChanged.connect(lambda: self._on_field_interacted("method"))

    def _on_studio_name_changed(self, name):
        self._on_field_interacted("name")
        if not self.is_edit_mode and name and hasattr(self, 'id_input'):
            slug = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')
            curr = self.id_input.text()
            if not curr or curr.startswith(slug[:-1]) or slug.startswith(curr):
                self.id_input.setText(slug)

    def _add_mandatory_row(self, txt, w, k):
        l = QtWidgets.QLabel("<b>" + str(txt) + "</b>")
        self.mandatory_labels[k] = l
        self.identity_form.addRow(l, w)

    def _validate_field(self, k):
        is_html = self.radio_html_strategy.isChecked()
        has_err, msg = False, ""
        if k == "id" and not self.is_edit_mode and hasattr(self, 'id_input'):
            val = self.id_input.text().strip()
            if not val:
                has_err, msg = True, "ID is required."
            elif val in self.existing_studio_ids:
                has_err, msg = True, "ID exists."
        elif k == "name":
            if not self.name_input.text().strip():
                has_err, msg = True, "Name required."
        elif k == "careers":
            val = self.careers_input.text().strip()
            if not val:
                has_err, msg = True, "Careers required."
            elif not re.match(r"^(https?://|/)", val):
                has_err, msg = True, "Invalid URL."
        elif k == "html_root" and is_html:
            if not self.html_container_input.text().strip():
                has_err, msg = True, "Selector required."
        elif k == "json_root" and not is_html:
            if not self.json_items_path_input.text().strip():
                has_err, msg = True, "Path required."
        elif k.startswith("regex_") and k in self.regex_input_fields:
            p = self.regex_input_fields[k].text().strip()
            if p:
                try:
                    re.compile(p)
                except Exception as e:
                    has_err, msg = True, str(e)
        l = self.mandatory_labels.get(k) or self.regex_error_labels.get(k)
        if l:
            if k in self.interacted_fields:
                if has_err:
                    l.setStyleSheet("color: #ff5555;")
                    l.setToolTip(msg)
                else:
                    color_style = "color: #5cb85c;" if k.startswith("regex_") and self.regex_input_fields[k].text().strip() else ""
                    l.setStyleSheet(color_style)
                    l.setToolTip("")
            else:
                l.setStyleSheet("")
                l.setToolTip("")
        return has_err, msg

    def _validate_all_fields(self, show_visual_errors=True):
        if show_visual_errors:
            self.interacted_fields.update(["id", "name", "careers", "html_root", "json_root"])
            self.interacted_fields.update(self.regex_input_fields.keys())
        errs = []
        check_keys = ["id", "name", "careers", "html_root", "json_root"] + list(self.regex_input_fields.keys())
        for k in check_keys:
            h, m = self._validate_field(k)
            if h:
                errs.append(m)
        return errs

    def _create_json_text_input(self, txt, layout):
        layout.addWidget(QtWidgets.QLabel("<b>" + str(txt) + "</b>"))
        e = QtWidgets.QPlainTextEdit()
        e.setMaximumHeight(80)
        e.setStyleSheet("font-family: monospace; font-size: 11px;")
        layout.addWidget(e)
        return e

    def _add_field_mapping_card(self, layout, txt, opts=None):
        cf = QtWidgets.QFrame()
        cf.setStyleSheet("QFrame { background: rgba(128,128,128,15); border: 1px solid rgba(128,128,128,30); border-radius: 6px; }")
        cl = QtWidgets.QVBoxLayout(cf)
        cl.setContentsMargins(10, 10, 10, 6)
        cl.setSpacing(6)
        r = QtWidgets.QHBoxLayout()
        h = QtWidgets.QLabel("<b>" + str(txt) + ":</b>")
        h.setFixedWidth(80)
        h.setAlignment(QtCore.Qt.AlignRight)
        r.addWidget(h)
        inp = QtWidgets.QLineEdit()
        r.addWidget(inp)
        cl.addLayout(r)
        mapped = {}
        if opts:
            oc = QtWidgets.QWidget()
            oc.setContentsMargins(85, 0, 0, 4)
            fl = FlowLayout(oc, 0, 12, 6)
            for ok in opts:
                row = QtWidgets.QHBoxLayout()
                row.setContentsMargins(0, 0, 0, 0)
                row.setSpacing(4)
                if ok in ["source", "remove_from_title"]:
                    label_text = "From URL" if ok == "source" else "Clean Location"
                    w = QtWidgets.QCheckBox(label_text)
                    w.setStyleSheet("font-size: 10px;")
                    row.addWidget(w)
                    mapped[ok] = w
                elif ok == "index":
                    l = QtWidgets.QLabel("Index:")
                    sb = QtWidgets.QSpinBox()
                    sb.setRange(-999, 999)
                    sb.setFixedSize(50, 18)
                    row.addWidget(l)
                    row.addWidget(sb)
                    mapped[ok] = sb
                else:
                    d = {"attr": "Attr:", "regex": "Regex:", "prefix": "Pre:", "suffix": "Suf:", "find_previous": "Prev:", "find_next_sibling": "Next:"}
                    label_name = d.get(ok, str(ok) + ":")
                    l = QtWidgets.QLabel(label_name)
                    l.setStyleSheet("font-size: 10px;")
                    i = QtWidgets.QLineEdit()
                    i.setFixedSize(60 if ok=="attr" else 90, 18)
                    if ok in ["regex", "find_previous", "find_next_sibling"]:
                        rk = "regex_" + str(txt).lower() + "_" + str(ok)
                        self.regex_error_labels[rk] = l
                        self.regex_input_fields[rk] = i
                        i.textChanged.connect(lambda _, k=rk: self._on_field_interacted(k))
                    row.addWidget(l)
                    row.addWidget(i)
                    mapped[ok] = i
                wr = QtWidgets.QWidget()
                wr.setLayout(row)
                fl.addWidget(wr)
            cl.addWidget(oc)
        layout.addWidget(cf)
        return inp, mapped

    def _on_tab_switched(self, idx):
        is_h = self.radio_html_strategy.isChecked()
        self.root_selector_stack.setCurrentIndex(0 if is_h else 1)
        self._on_field_interacted("strategy")
        self._validate_all_fields(False)

    def _apply_mapping(self, val, inp, opts, is_h):
        if not isinstance(val, dict):
            inp.setText(str(val))
            return
        inp.setText(str(val.get("selector" if is_h else "path", "")))
        for k, w in opts.items():
            if k == "source":
                w.setChecked(val.get("source") == "url")
            elif isinstance(w, QtWidgets.QSpinBox):
                try:
                    w.setValue(int(val.get(k, 0)))
                except (ValueError, TypeError):
                    w.setValue(0)
            elif isinstance(w, QtWidgets.QLineEdit):
                w.setText(str(val.get(k, "")))

    def load_studio_data(self):
        if not self.studio_data:
            return
        self.name_input.setText(self.studio_data.get("name", ""))
        self.logo_input.setText(self.studio_data.get("logo_url", ""))
        curl = self.studio_data.get("careers_url", "")
        self.careers_input.setText(", ".join(curl) if isinstance(curl, list) else str(curl))
        self.website_input.setText(self.studio_data.get("website", ""))
        sc = self.studio_data.get("scraping", {})
        strat = sc.get("strategy", "html")
        is_h = strat != "json"
        fm = sc.get("map", {})
        if sc.get("url_location_regex"):
            self.location_mapping_options["source"].setChecked(True)
            self.location_mapping_options["regex"].setText(sc.get("url_location_regex"))
        if strat == "json":
            self.radio_json_strategy.setChecked(True)
            self.json_items_path_input.setText(sc.get("path", ""))
        else:
            self.radio_html_strategy.setChecked(True)
            self.html_container_input.setText(sc.get("container", ""))
        self._apply_mapping(fm.get("title", ""), self.title_mapping_input, self.title_mapping_options, is_h)
        self._apply_mapping(fm.get("link", ""), self.link_mapping_input, self.link_mapping_options, is_h)
        self._apply_mapping(fm.get("location", ""), self.location_mapping_input, self.location_mapping_options, is_h)
        if "remove_from_title" in self.title_mapping_options:
            self.title_mapping_options["remove_from_title"].setChecked(fm.get("remove_location_from_title", False))
        
        # Method
        m = str(sc.get("method", "GET")).upper()
        idx = self.request_method_combo.findText(m)
        if idx >= 0: self.request_method_combo.setCurrentIndex(idx)
        
        for k, inp in [("params", self.request_params_input), ("payload", self.request_payload_input), ("headers", self.request_headers_input)]:
            if k in sc:
                text_val = json.dumps(StudioDialog.expand_json_strings(sc[k]), indent=2)
                inp.setPlainText(text_val)

    def _build_studio_config_dict(self):
        if self.is_edit_mode:
            sid = self.id_display.text()
        else:
            sid = self.id_input.text().strip() if hasattr(self, 'id_input') else "temp"
            
        is_h = self.radio_html_strategy.isChecked()
        
        # Start with original scraping config if it exists
        if self.is_edit_mode and self.studio_data:
            sc = dict(self.studio_data.get("scraping", {}))
        else:
            sc = {}
            
        sc["strategy"] = "html" if is_h else "json"
        sc["method"] = self.request_method_combo.currentText()
        
        fm = {}
        def build_f(mi, opts):
            sel = mi.text().strip()
            is_u = opts.get("source").isChecked() if "source" in opts else False
            ho = is_u
            for k, w in opts.items():
                if k in ["source", "remove_from_title"]: continue
                if (isinstance(w, QtWidgets.QSpinBox) and w.value() != 0) or (isinstance(w, QtWidgets.QLineEdit) and w.text().strip()):
                    ho = True
                    break
            if not ho: return sel
            key_name = "selector" if is_h else "path"
            d = {key_name: sel}
            if is_u: d["source"] = "url"
            for k, w in opts.items():
                if k in ["source", "remove_from_title"]: continue
                if isinstance(w, QtWidgets.QSpinBox):
                    if w.value() != 0: d[k] = w.value()
                elif isinstance(w, QtWidgets.QLineEdit):
                    if w.text().strip(): d[k] = w.text().strip()
            return d
        fm["title"] = build_f(self.title_mapping_input, self.title_mapping_options)
        fm["link"] = build_f(self.link_mapping_input, self.link_mapping_options)
        fm["location"] = build_f(self.location_mapping_input, self.location_mapping_options)
        if self.title_mapping_options.get("remove_from_title") and self.title_mapping_options["remove_from_title"].isChecked():
            fm["remove_location_from_title"] = True
        sc["map"] = fm
        if is_h:
            sc["container"] = self.html_container_input.text().strip()
            sc.pop("path", None)
        else:
            sc["path"] = self.json_items_path_input.text().strip()
            sc.pop("container", None)
        for k, inp in [("params", self.request_params_input), ("payload", self.request_payload_input), ("headers", self.request_headers_input)]:
            txt = inp.toPlainText().strip()
            if txt:
                try: 
                    sc[k] = StudioDialog.compact_json_objects(json.loads(txt))
                except: pass
        curls = [u.strip() for u in re.split(r"[,;]", self.careers_input.text().strip()) if u.strip()]
        res = {
            "id": sid,
            "name": self.name_input.text().strip(),
            "logo_url": self.logo_input.text().strip(),
            "careers_url": curls if len(curls) > 1 else curls[0] if curls else "",
            "website": self.website_input.text().strip(),
            "scraping": sc
        }
        return res

    def on_test_config(self):
        errs = self._validate_all_fields(True)
        if errs:
            QtWidgets.QMessageBox.warning(self, "Errors", "\n".join("- "+e for e in errs))
            return
            
        cfg = self._build_studio_config_dict()
        self.last_test_config = cfg
        self.test_btn.setEnabled(False)
        self.test_status_label.setText("Testing...")
        self.test_status_label.setStyleSheet("color: #888; text-decoration: none;")
        self.test_status_label.setCursor(QtCore.Qt.ArrowCursor)
        self.test_spinner.show()
        
        self.test_worker = TestWorker(cfg)
        self.test_worker.finished.connect(self._on_test_finished)
        self.test_worker.error.connect(self._on_test_error)
        self.test_worker.start()

    def _on_test_finished(self, results):
        self.last_test_jobs = results["jobs"]
        self.last_test_logo_path = results["logo_path"]
        
        count = len(self.last_test_jobs)
        if count == 0:
            self.test_status_label.setText("⚠ Success (0 jobs)")
            self.test_status_label.setStyleSheet("color: #f0ad4e; text-decoration: underline;")
        else:
            self.test_status_label.setText("✅ Found " + str(count) + " jobs")
            self.test_status_label.setStyleSheet("color: #5cb85c; text-decoration: underline;")
            
        self.test_status_label.setCursor(QtCore.Qt.PointingHandCursor)
        self.test_spinner.hide()
        self.test_btn.setEnabled(True)

    def _on_test_error(self, err_msg):
        self.test_spinner.hide()
        self.test_btn.setEnabled(True)
        self.test_status_label.setText("❌ Failed")
        self.test_status_label.setStyleSheet("color: #ff5555; text-decoration: none;")
        self.test_status_label.setCursor(QtCore.Qt.ArrowCursor)
        QtWidgets.QMessageBox.critical(self, "Test Failed", str(err_msg))

    def on_show_test_preview(self):
        if self.test_worker and self.test_worker.isRunning():
            return
        if not self.last_test_config:
            return
        p = TestPreviewDialog(self.last_test_config, self.last_test_jobs, self.last_test_logo_path, self)
        p.exec_()

    def on_save_config(self):
        errs = self._validate_all_fields(True)
        if errs:
            QtWidgets.QMessageBox.warning(self, "Errors", "\n".join("- "+e for e in errs))
            return
        self.studio_data = self._build_studio_config_dict()
        self.saved.emit(self.studio_data)
        self.accept()
