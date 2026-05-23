APP_STYLESHEET = """
* {
    font-family: "Segoe UI", "Inter", "Noto Sans", Arial, sans-serif;
    font-size: 13px;
    letter-spacing: 0px;
}

QMainWindow, QWidget#Root {
    background: #f5f7fb;
    color: #172033;
}

QFrame#Sidebar {
    background: #121826;
    border: none;
}

QLabel#Brand {
    color: #ffffff;
    font-size: 22px;
    font-weight: 700;
}

QLabel#SubtleDark {
    color: #a8b3c7;
}

QPushButton#NavButton {
    background: transparent;
    border: 0;
    border-radius: 6px;
    color: #cbd5e1;
    padding: 10px 12px;
    text-align: left;
}

QPushButton#NavButton:hover {
    background: #1f2937;
    color: #ffffff;
}

QPushButton#NavButton[active="true"] {
    background: #e8f7f1;
    color: #0f5132;
    font-weight: 700;
}

QLabel#PageTitle {
    color: #121826;
    font-size: 24px;
    font-weight: 700;
}

QLabel#SectionTitle {
    color: #172033;
    font-size: 15px;
    font-weight: 700;
}

QLabel#PanelTitle {
    color: #0f172a;
    font-size: 16px;
    font-weight: 700;
}

QLabel#Muted {
    color: #667085;
}

QLabel#StatusPill {
    background: #e8f7f1;
    color: #0f5132;
    border-radius: 6px;
    padding: 6px 10px;
    font-weight: 700;
}

QFrame#Panel {
    background: #ffffff;
    border: 1px solid #e4e7ec;
    border-radius: 8px;
}

QScrollArea#PageScroll, QWidget#ScrollContent {
    background: transparent;
    border: none;
}

QLineEdit, QComboBox, QTextEdit {
    background: #ffffff;
    border: 1px solid #d0d5dd;
    border-radius: 6px;
    color: #172033;
    min-height: 34px;
    padding: 6px 9px;
}

QTextEdit {
    min-height: 120px;
}

QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
    border: 1px solid #0f766e;
}

QPushButton {
    background: #ffffff;
    border: 1px solid #d0d5dd;
    border-radius: 6px;
    color: #172033;
    min-height: 34px;
    padding: 7px 12px;
}

QPushButton:hover {
    background: #f8fafc;
}

QPushButton#Primary {
    background: #0f766e;
    border: 1px solid #0f766e;
    color: #ffffff;
    font-weight: 700;
}

QPushButton#Primary:hover {
    background: #115e59;
}

QPushButton#Danger {
    border: 1px solid #f2b8b5;
    color: #b42318;
}

QPushButton:disabled {
    background: #f2f4f7;
    border-color: #e4e7ec;
    color: #98a2b3;
}

QTableWidget {
    background: #ffffff;
    border: 1px solid #e4e7ec;
    border-radius: 8px;
    gridline-color: #eef2f6;
    selection-background-color: #dff3ec;
    selection-color: #172033;
}

QTableWidget::item {
    padding: 6px 10px;
}

QHeaderView::section {
    background: #f8fafc;
    border: none;
    border-bottom: 1px solid #e4e7ec;
    color: #475467;
    font-weight: 700;
    padding: 8px;
}

QCheckBox {
    color: #172033;
    spacing: 8px;
}

QScrollBar:vertical {
    background: #f5f7fb;
    width: 12px;
}

QScrollBar::handle:vertical {
    background: #cbd5e1;
    border-radius: 6px;
    min-height: 24px;
}
"""
