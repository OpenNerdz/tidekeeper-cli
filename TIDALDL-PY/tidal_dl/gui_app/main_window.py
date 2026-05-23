from __future__ import annotations

import webbrowser
from typing import Dict, List

from PySide6.QtCore import Qt, QThreadPool, QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..enums import AudioQuality, Type, VideoQuality
from ..settings import SETTINGS
from .backend import SearchItem, TidekeeperBackend
from .style import APP_STYLESHEET
from .workers import DownloadWorker, TaskWorker


SCREEN_ORDER = ("search", "queue", "settings", "account")


def _button(text: str, primary: bool = False, danger: bool = False) -> QPushButton:
    button = QPushButton(text)
    if primary:
        button.setObjectName("Primary")
    if danger:
        button.setObjectName("Danger")
    button.setCursor(Qt.PointingHandCursor)
    return button


def _panel(layout) -> QFrame:
    frame = QFrame()
    frame.setObjectName("Panel")
    frame.setLayout(layout)
    return frame


def _label(text: str, name: str | None = None) -> QLabel:
    label = QLabel(text)
    if name:
        label.setObjectName(name)
    return label


class MainWindow(QMainWindow):
    def __init__(self, backend: TidekeeperBackend):
        super().__init__()
        self.backend = backend
        self.thread_pool = QThreadPool.globalInstance()
        self.results: List[SearchItem] = []
        self.queue: List[SearchItem] = []
        self.nav_buttons: Dict[str, QPushButton] = {}
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll_device_login)
        self.login_polling = False

        self.setWindowTitle("Tidekeeper")
        self.setMinimumSize(1040, 680)
        self.resize(1180, 740)
        self.setStyleSheet(APP_STYLESHEET)
        self._build()
        self.version_label.setText(f"v{self.backend.version()}")
        self.refresh_settings()
        self.refresh_auth_status()
        self.show_screen("search")

    def _build(self):
        root = QWidget()
        root.setObjectName("Root")
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_sidebar())

        self.stack = QStackedWidget()
        self.pages = {
            "search": self._build_search_page(),
            "queue": self._build_queue_page(),
            "settings": self._build_settings_page(),
            "account": self._build_account_page(),
        }
        for name in SCREEN_ORDER:
            self.stack.addWidget(self.pages[name])
        root_layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(210)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 22, 18, 18)
        layout.setSpacing(10)

        brand = _label("Tidekeeper", "Brand")
        sub = _label("Desktop", "SubtleDark")
        layout.addWidget(brand)
        layout.addWidget(sub)
        layout.addSpacing(20)

        for name, title in (
            ("search", "Search"),
            ("queue", "Queue"),
            ("settings", "Settings"),
            ("account", "Account"),
        ):
            button = QPushButton(title)
            button.setObjectName("NavButton")
            button.setProperty("active", False)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False, screen=name: self.show_screen(screen))
            self.nav_buttons[name] = button
            layout.addWidget(button)

        layout.addStretch(1)
        self.version_label = _label("Ready", "SubtleDark")
        layout.addWidget(self.version_label)
        return sidebar

    def _page(self, title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)
        layout.addWidget(_label(title, "PageTitle"))
        if subtitle:
            layout.addWidget(_label(subtitle, "Muted"))
        return page, layout

    def _build_search_page(self) -> QWidget:
        page, layout = self._page("Search", "Find albums, tracks, videos, playlists, artists, or paste a TIDAL URL.")

        search_layout = QHBoxLayout()
        self.search_type = QComboBox()
        for item in (Type.Track, Type.Album, Type.Playlist, Type.Artist, Type.Video):
            self.search_type.addItem(item.name, item)
        self.search_type.setFixedWidth(150)
        self.search_text = QLineEdit()
        self.search_text.setPlaceholderText("Search or paste URL")
        self.search_button = _button("Search", primary=True)
        self.search_button.clicked.connect(self.run_search)
        self.search_text.returnPressed.connect(self.run_search)
        search_layout.addWidget(self.search_type)
        search_layout.addWidget(self.search_text, 1)
        search_layout.addWidget(self.search_button)
        layout.addWidget(_panel(search_layout))

        direct_layout = QHBoxLayout()
        self.direct_text = QLineEdit()
        self.direct_text.setPlaceholderText("Direct download: TIDAL URL, numeric ID, mix ID, or .txt file")
        self.direct_browse_button = _button("File")
        self.direct_queue_button = _button("Add Direct")
        self.direct_download_button = _button("Download Direct", primary=True)
        self.direct_browse_button.clicked.connect(self.browse_direct_file)
        self.direct_queue_button.clicked.connect(self.add_direct_to_queue)
        self.direct_download_button.clicked.connect(self.download_direct)
        direct_layout.addWidget(self.direct_text, 1)
        direct_layout.addWidget(self.direct_browse_button)
        direct_layout.addWidget(self.direct_queue_button)
        direct_layout.addWidget(self.direct_download_button)
        layout.addWidget(_panel(direct_layout))

        self.results_table = QTableWidget(0, 6)
        self._setup_table(self.results_table, ["Type", "Title", "Artists", "Quality", "Duration", "ID"])
        self.results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.results_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.results_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.results_table.setColumnWidth(3, 150)
        self.results_table.setColumnWidth(4, 90)
        self.results_table.setColumnWidth(5, 120)
        self.results_table.setSelectionMode(QTableWidget.ExtendedSelection)
        layout.addWidget(self.results_table, 1)

        action_layout = QHBoxLayout()
        self.search_status = _label("No search run yet.", "Muted")
        action_layout.addWidget(self.search_status, 1)
        self.add_queue_button = _button("Add to Queue")
        self.download_now_button = _button("Download Now", primary=True)
        self.add_queue_button.clicked.connect(self.add_selected_to_queue)
        self.download_now_button.clicked.connect(self.download_selected)
        action_layout.addWidget(self.add_queue_button)
        action_layout.addWidget(self.download_now_button)
        layout.addLayout(action_layout)
        return page

    def _build_queue_page(self) -> QWidget:
        page, layout = self._page("Queue", "Review selected items and run downloads in order.")

        self.queue_table = QTableWidget(0, 5)
        self._setup_table(self.queue_table, ["Type", "Title", "Artists", "Quality", "Status"])
        self.queue_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.queue_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.queue_table.setColumnWidth(3, 150)
        self.queue_table.setColumnWidth(4, 120)
        self.queue_table.setSelectionMode(QTableWidget.ExtendedSelection)
        layout.addWidget(self.queue_table, 1)

        action_layout = QHBoxLayout()
        self.queue_status = _label("Queue is empty.", "Muted")
        action_layout.addWidget(self.queue_status, 1)
        self.remove_queue_button = _button("Remove")
        self.clear_queue_button = _button("Clear")
        self.start_queue_button = _button("Start Queue", primary=True)
        self.remove_queue_button.clicked.connect(self.remove_selected_queue_items)
        self.clear_queue_button.clicked.connect(self.clear_queue)
        self.start_queue_button.clicked.connect(self.start_queue_download)
        action_layout.addWidget(self.remove_queue_button)
        action_layout.addWidget(self.clear_queue_button)
        action_layout.addWidget(self.start_queue_button)
        layout.addLayout(action_layout)

        self.download_log = QTextEdit()
        self.download_log.setReadOnly(True)
        self.download_log.setPlaceholderText("Download output")
        layout.addWidget(self.download_log)
        return page

    def _build_settings_page(self) -> QWidget:
        page, layout = self._page("Settings", "Tune output, quality, and library behavior.")

        grid = QGridLayout()
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(12)

        self.download_path = QLineEdit()
        browse = _button("Browse")
        browse.clicked.connect(self.browse_download_path)
        path_layout = QHBoxLayout()
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.addWidget(self.download_path, 1)
        path_layout.addWidget(browse)

        self.audio_quality = QComboBox()
        for item in AudioQuality:
            self.audio_quality.addItem(item.name, item.name)
        self.video_quality = QComboBox()
        for item in VideoQuality:
            self.video_quality.addItem(item.name, item.name)
        self.language = QComboBox()
        for index, name in self.backend.language_choices():
            self.language.addItem(name, index)
        self.api_client = QComboBox()
        for item in self.backend.api_clients():
            status = "OK" if item["valid"] else "old"
            self.api_client.addItem(
                f'{item["index"]} {status} - {item["platform"]} ({item["formats"]})',
                item["index"],
            )

        self.checks = {}
        for key, label in (
            ("checkExist", "Skip existing files"),
            ("showProgress", "Show progress"),
            ("showTrackInfo", "Show track info"),
            ("includeEP", "Include EPs and singles"),
            ("saveCovers", "Save covers"),
            ("lyricFile", "Save lyrics"),
            ("saveAlbumInfo", "Save album info"),
            ("downloadVideos", "Download videos"),
            ("multiThread", "Parallel downloads"),
            ("downloadDelay", "Use request delay"),
            ("usePlaylistFolder", "Use playlist folders"),
        ):
            self.checks[key] = QCheckBox(label)

        self.album_format = QLineEdit()
        self.playlist_format = QLineEdit()
        self.track_format = QLineEdit()
        self.video_format = QLineEdit()

        row = 0
        grid.addWidget(_label("Download path", "SectionTitle"), row, 0)
        grid.addLayout(path_layout, row, 1, 1, 3)
        row += 1
        grid.addWidget(_label("Audio quality", "SectionTitle"), row, 0)
        grid.addWidget(self.audio_quality, row, 1)
        grid.addWidget(_label("Video quality", "SectionTitle"), row, 2)
        grid.addWidget(self.video_quality, row, 3)
        row += 1
        grid.addWidget(_label("Language", "SectionTitle"), row, 0)
        grid.addWidget(self.language, row, 1)
        grid.addWidget(_label("TIDAL client", "SectionTitle"), row, 2)
        grid.addWidget(self.api_client, row, 3)
        row += 1

        for index, key in enumerate(self.checks):
            grid.addWidget(self.checks[key], row + index // 3, index % 3)
        row += 4

        for label, widget in (
            ("Album folder", self.album_format),
            ("Playlist folder", self.playlist_format),
            ("Track file", self.track_format),
            ("Video file", self.video_format),
        ):
            grid.addWidget(_label(label, "SectionTitle"), row, 0)
            grid.addWidget(widget, row, 1, 1, 3)
            row += 1

        layout.addWidget(_panel(grid), 1)

        action_layout = QHBoxLayout()
        self.settings_status = _label("Settings loaded.", "Muted")
        action_layout.addWidget(self.settings_status, 1)
        reset = _button("Reload")
        save = _button("Save Settings", primary=True)
        reset.clicked.connect(self.refresh_settings)
        save.clicked.connect(self.save_settings)
        action_layout.addWidget(reset)
        action_layout.addWidget(save)
        layout.addLayout(action_layout)
        return page

    def _build_account_page(self) -> QWidget:
        page, layout = self._page("Account", "Manage the saved TIDAL session used by the terminal and desktop app.")

        status_layout = QGridLayout()
        status_layout.setContentsMargins(16, 16, 16, 16)
        status_layout.setVerticalSpacing(12)
        self.auth_label = _label("Signed out", "StatusPill")
        self.country_label = _label("Country: unknown", "Muted")
        self.expiry_label = _label("Expires: unknown", "Muted")
        status_layout.addWidget(self.auth_label, 0, 0, 1, 2)
        status_layout.addWidget(self.country_label, 1, 0)
        status_layout.addWidget(self.expiry_label, 1, 1)
        layout.addWidget(_panel(status_layout))

        login_layout = QGridLayout()
        login_layout.setContentsMargins(16, 16, 16, 16)
        login_layout.setVerticalSpacing(12)
        self.login_url = QLineEdit()
        self.login_url.setReadOnly(True)
        self.login_url.setPlaceholderText("Device login URL")
        self.device_login_button = _button("Start Device Login", primary=True)
        self.open_login_button = _button("Open Login")
        self.refresh_login_button = _button("Refresh Saved Login")
        self.logout_button = _button("Log Out", danger=True)
        self.doctor_button = _button("Run Doctor")
        self.device_login_button.clicked.connect(self.start_device_login)
        self.open_login_button.clicked.connect(self.open_login_url)
        self.refresh_login_button.clicked.connect(self.refresh_saved_login)
        self.logout_button.clicked.connect(self.logout)
        self.doctor_button.clicked.connect(self.run_doctor)
        login_layout.addWidget(_label("Device login", "SectionTitle"), 0, 0)
        login_layout.addWidget(self.login_url, 0, 1, 1, 3)
        login_layout.addWidget(self.device_login_button, 1, 0)
        login_layout.addWidget(self.open_login_button, 1, 1)
        login_layout.addWidget(self.refresh_login_button, 1, 2)
        login_layout.addWidget(self.logout_button, 1, 3)
        login_layout.addWidget(self.doctor_button, 2, 0)
        layout.addWidget(_panel(login_layout))

        token_layout = QGridLayout()
        token_layout.setContentsMargins(16, 16, 16, 16)
        token_layout.setVerticalSpacing(12)
        self.access_token = QLineEdit()
        self.access_token.setEchoMode(QLineEdit.Password)
        self.access_token.setPlaceholderText("Access token")
        self.refresh_token = QLineEdit()
        self.refresh_token.setEchoMode(QLineEdit.Password)
        self.refresh_token.setPlaceholderText("Refresh token, optional")
        self.token_login_button = _button("Save Token", primary=True)
        self.token_login_button.clicked.connect(self.login_with_token)
        token_layout.addWidget(_label("Manual token", "SectionTitle"), 0, 0)
        token_layout.addWidget(self.access_token, 0, 1)
        token_layout.addWidget(self.refresh_token, 1, 1)
        token_layout.addWidget(self.token_login_button, 1, 2)
        layout.addWidget(_panel(token_layout))

        self.account_log = QTextEdit()
        self.account_log.setReadOnly(True)
        self.account_log.setPlaceholderText("Account output")
        layout.addWidget(self.account_log, 1)
        return page

    def _setup_table(self, table: QTableWidget, headers: List[str]):
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(False)
        table.setShowGrid(False)
        table.setSortingEnabled(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def show_screen(self, name: str):
        if name not in self.pages:
            return
        self.stack.setCurrentWidget(self.pages[name])
        for key, button in self.nav_buttons.items():
            button.setProperty("active", key == name)
            button.style().unpolish(button)
            button.style().polish(button)

    def run_search(self):
        text = self.search_text.text().strip()
        kind = self.search_type.currentData()
        if not text:
            self.search_status.setText("Enter a search term or TIDAL URL.")
            return
        self.search_button.setEnabled(False)
        self.search_status.setText("Searching...")
        worker = TaskWorker(self.backend.search, text, kind)
        worker.signals.result.connect(self.set_search_results)
        worker.signals.error.connect(self.show_search_error)
        worker.signals.finished.connect(lambda: self.search_button.setEnabled(True))
        self.thread_pool.start(worker)

    def set_search_results(self, items: List[SearchItem]):
        self.results = items
        self.results_table.setSortingEnabled(False)
        self.results_table.setRowCount(len(items))
        for row, item in enumerate(items):
            values = [item.kind.name, item.title, item.artists, item.quality, item.duration, item.identifier]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                if col == 5:
                    cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.results_table.setItem(row, col, cell)
        self.results_table.setSortingEnabled(True)
        self.search_status.setText(f"{len(items)} result{'s' if len(items) != 1 else ''}.")

    def show_search_error(self, message: str):
        self.search_status.setText(message)
        QMessageBox.warning(self, "Search failed", message)

    def selected_result_items(self) -> List[SearchItem]:
        rows = sorted({index.row() for index in self.results_table.selectionModel().selectedRows()})
        return [self.results[row] for row in rows if row < len(self.results)]

    def add_selected_to_queue(self):
        items = self.selected_result_items()
        if not items:
            self.search_status.setText("Select one or more rows first.")
            return
        self.queue.extend(items)
        self.refresh_queue_table()
        self.search_status.setText(f"Added {len(items)} item{'s' if len(items) != 1 else ''} to queue.")

    def browse_direct_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "URL list", self.direct_text.text(), "Text files (*.txt);;All files (*)")
        if path:
            self.direct_text.setText(path)

    def direct_item_from_input(self):
        text = self.direct_text.text().strip()
        if not text:
            self.search_status.setText("Enter a URL, ID, mix ID, or .txt file.")
            return None
        return self.backend.direct_item(text)

    def add_direct_to_queue(self):
        item = self.direct_item_from_input()
        if item is None:
            return
        self.queue.append(item)
        self.refresh_queue_table()
        self.search_status.setText("Direct item added to queue.")

    def download_direct(self):
        item = self.direct_item_from_input()
        if item is None:
            return
        self.queue.append(item)
        self.refresh_queue_table()
        self.show_screen("queue")
        self.start_downloads([item])

    def download_selected(self):
        items = self.selected_result_items()
        if not items:
            self.search_status.setText("Select one or more rows first.")
            return
        self.queue.extend(items)
        self.refresh_queue_table()
        self.show_screen("queue")
        self.start_downloads(items)

    def refresh_queue_table(self):
        self.queue_table.setSortingEnabled(False)
        self.queue_table.setRowCount(len(self.queue))
        for row, item in enumerate(self.queue):
            kind = "Direct" if item.kind == Type.Null else item.kind.name
            values = [kind, item.title, item.artists, item.quality, "Queued"]
            for col, value in enumerate(values):
                self.queue_table.setItem(row, col, QTableWidgetItem(str(value)))
        self.queue_table.setSortingEnabled(True)
        self.queue_status.setText(f"{len(self.queue)} item{'s' if len(self.queue) != 1 else ''} in queue.")

    def remove_selected_queue_items(self):
        rows = sorted({index.row() for index in self.queue_table.selectionModel().selectedRows()}, reverse=True)
        for row in rows:
            if row < len(self.queue):
                self.queue.pop(row)
        self.refresh_queue_table()

    def clear_queue(self):
        self.queue = []
        self.refresh_queue_table()
        self.download_log.clear()

    def start_queue_download(self):
        if not self.queue:
            self.queue_status.setText("Queue is empty.")
            return
        self.start_downloads(list(self.queue))

    def start_downloads(self, items: List[SearchItem]):
        self.start_queue_button.setEnabled(False)
        self.download_log.append("Starting downloads")
        worker = DownloadWorker(self.backend, items)
        worker.signals.log.connect(self.append_download_log)
        worker.signals.result.connect(lambda _: self.queue_status.setText("Downloads finished."))
        worker.signals.error.connect(self.show_download_error)
        worker.signals.finished.connect(lambda: self.start_queue_button.setEnabled(True))
        self.thread_pool.start(worker)

    def append_download_log(self, text: str):
        cursor = self.download_log.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.download_log.setTextCursor(cursor)
        self.download_log.ensureCursorVisible()

    def show_download_error(self, message: str):
        self.queue_status.setText(message)
        QMessageBox.warning(self, "Download failed", message)

    def refresh_settings(self):
        self.download_path.setText(SETTINGS.downloadPath)
        self.audio_quality.setCurrentText(SETTINGS.audioQuality.name)
        self.video_quality.setCurrentText(SETTINGS.videoQuality.name)
        index = self.language.findData(SETTINGS.language)
        self.language.setCurrentIndex(index if index >= 0 else 0)
        client_index = self.api_client.findData(SETTINGS.apiKeyIndex)
        self.api_client.setCurrentIndex(client_index if client_index >= 0 else 0)
        for key, checkbox in self.checks.items():
            checkbox.setChecked(bool(getattr(SETTINGS, key)))
        self.album_format.setText(SETTINGS.albumFolderFormat)
        self.playlist_format.setText(SETTINGS.playlistFolderFormat)
        self.track_format.setText(SETTINGS.trackFileFormat)
        self.video_format.setText(SETTINGS.videoFileFormat)
        self.settings_status.setText("Settings loaded.")

    def browse_download_path(self):
        path = QFileDialog.getExistingDirectory(self, "Download folder", self.download_path.text())
        if path:
            self.download_path.setText(path)

    def save_settings(self):
        values = {
            "downloadPath": self.download_path.text().strip(),
            "audioQuality": self.audio_quality.currentData(),
            "videoQuality": self.video_quality.currentData(),
            "albumFolderFormat": self.album_format.text(),
            "playlistFolderFormat": self.playlist_format.text(),
            "trackFileFormat": self.track_format.text(),
            "videoFileFormat": self.video_format.text(),
            "language": self.language.currentData(),
            "apiKeyIndex": self.api_client.currentData(),
        }
        values.update({key: checkbox.isChecked() for key, checkbox in self.checks.items()})
        self.backend.save_settings(values)
        self.settings_status.setText("Settings saved.")

    def refresh_auth_status(self):
        status = self.backend.auth_status()
        self.auth_label.setText(status.label)
        self.country_label.setText(f"Country: {status.country_code or 'unknown'}")
        self.expiry_label.setText(f"Expires: {status.expires_label}")

    def refresh_saved_login(self):
        self.account_log.append("Refreshing saved login...")
        worker = TaskWorker(self.backend.refresh_saved_login)
        worker.signals.result.connect(lambda status: (self.refresh_auth_status(), self.account_log.append(status.label)))
        worker.signals.error.connect(lambda message: self.account_log.append(message))
        self.thread_pool.start(worker)

    def start_device_login(self):
        self.device_login_button.setEnabled(False)
        self.account_log.append("Requesting device login...")
        worker = TaskWorker(self.backend.start_device_login)
        worker.signals.result.connect(self._device_login_started)
        worker.signals.error.connect(self._device_login_error)
        self.thread_pool.start(worker)

    def _device_login_started(self, challenge):
        self.login_url.setText(challenge.url)
        self.account_log.append(f"Open {challenge.url}")
        self.account_log.append(f"Code: {challenge.user_code}")
        self.login_polling = True
        self.poll_timer.start(max(1, challenge.interval) * 1000)

    def _device_login_error(self, message: str):
        self.device_login_button.setEnabled(True)
        self.account_log.append(message)

    def _poll_device_login(self):
        if not self.login_polling:
            return
        worker = TaskWorker(self.backend.poll_device_login)
        worker.signals.result.connect(self._device_login_polled)
        worker.signals.error.connect(lambda message: self.account_log.append(message))
        self.thread_pool.start(worker)

    def _device_login_polled(self, status):
        self.refresh_auth_status()
        if status.has_token:
            self.poll_timer.stop()
            self.login_polling = False
            self.device_login_button.setEnabled(True)
            self.account_log.append("Login complete.")

    def open_login_url(self):
        if self.login_url.text():
            webbrowser.open(self.login_url.text())

    def logout(self):
        self.backend.logout()
        self.refresh_auth_status()
        self.account_log.append("Logged out.")

    def login_with_token(self):
        self.account_log.append("Saving manual token...")
        worker = TaskWorker(
            self.backend.login_by_access_token,
            self.access_token.text(),
            self.refresh_token.text(),
        )
        worker.signals.result.connect(lambda status: (self.refresh_auth_status(), self.account_log.append(status.label)))
        worker.signals.error.connect(lambda message: self.account_log.append(message))
        self.thread_pool.start(worker)

    def run_doctor(self):
        self.account_log.append("Running doctor...")
        worker = TaskWorker(self.backend.run_doctor)
        worker.signals.result.connect(lambda output: self.account_log.append(output.strip()))
        worker.signals.error.connect(lambda message: self.account_log.append(message))
        self.thread_pool.start(worker)

    def prepare_demo_state(self):
        self.search_text.setText("midnight")
        self.direct_text.setText("https://tidal.com/browse/track/70973230")
        self.set_search_results(self.backend.search("midnight", Type.Track))
        if self.results:
            self.results_table.selectRow(0)
            self.queue = self.results[:28]
            self.refresh_queue_table()
            self.download_log.setPlainText(
                "\n".join(
                    f"Queued {item.title} - waiting for download slot"
                    for item in self.queue
                )
                + "\n"
            )
        self.login_url.setText("https://login.tidal.com/DEMO-CODE")
        self.account_log.setPlainText(
            self.backend.run_doctor()
            + "\n"
            + "\n".join(f"History {index + 1:02d}: token and client checks passed" for index in range(20))
        )


def run_app(backend: TidekeeperBackend):
    app = QApplication.instance() or QApplication([])
    backend.initialize()
    window = MainWindow(backend)
    window.show()
    return app.exec()
