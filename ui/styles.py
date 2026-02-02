JOB_WIDGET_STYLE = """
    JobWidget {
        border: 1px solid #555;
        border-radius: 4px;
        background-color: rgba(255, 255, 255, 0.03);
    }
    JobWidget:hover {
        background-color: rgba(255, 255, 255, 0.05);
        border-color: #666;
    }
    JobWidget:disabled {
        background-color: rgba(255, 255, 255, 0.01);
        border-color: #4C4C4C;
    }
    QToolTip {
        background-color: #333;
        color: #f0f0f0;
        border: 1px solid #444;
        padding: 1px;
        border-radius: 3px;
    }
    #job_link_btn {
        border: 1px solid #555;
        background-color: transparent;
        border-radius: 3px;
        padding: 2px;
    }
    #job_link_btn:hover {
        background-color: #444;
        border-color: #777;
    }
"""

STUDIO_WIDGET_STYLE = """
    #studio_widget {
        border: 1px solid #333;
        border-radius: 4px;
        background-color: transparent;
    }
    QLabel {
        border: none;
        background: transparent;
    }
    QToolTip {
        background-color: #333;
        color: #f0f0f0;
        border: 1px solid #444;
        padding: 1px;
        border-radius: 3px;
    }
"""

SCROLL_AREA_STYLE = """
    QScrollArea {
        border: 1px solid #333;
        background: transparent;
    }
"""

GLOBAL_STYLE = """
    QLineEdit {
        border: 1px solid #444;
        color: #ddd;
        padding: 1px;
    }
    QToolTip {
        background-color: #333;
        color: #f0f0f0;
        border: 1px solid #444;
        padding: 1px;
        border-radius: 3px;
    }
"""

NO_RESULTS_STYLE = "QLabel { color: #666; font-style: italic; }"
LOCATION_STYLE = "QLabel { color: #888; } QLabel:disabled { color: #555; }"
TITLE_STYLE = "QLabel { color: #eee; font-weight: bold; } QLabel:disabled { color: #666; }"
