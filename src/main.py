"""短视频指纹批量修改工具 - Mac 桌面端。"""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from auth import AuthApiError, AuthSession, MineAdminAuthClient, User
from login_window import LoginWindow
from processor import find_ffmpeg, format_file_size, is_video_file, process_videos
from styles import apply_styles


class WorkerThread(QThread):
    progress = pyqtSignal(int, int, float, str)
    finished_ok = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, source_path: str, count: int) -> None:
        super().__init__()
        self.source_path = source_path
        self.count = count
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            outputs = process_videos(
                self.source_path,
                self.count,
                on_progress=lambda idx, total, ratio, msg: self.progress.emit(
                    idx, total, ratio, msg
                ),
                should_cancel=lambda: self._cancelled,
            )
            if self._cancelled:
                self.failed.emit("已取消生成")
            else:
                self.finished_ok.emit(outputs)
        except Exception as exc:  # noqa: BLE001 - surface to UI
            self.failed.emit(str(exc))


class DropZone(QFrame):
    file_dropped = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setObjectName("dropZone")
        self.setMinimumHeight(220)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon_label = QLabel("🎬")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setFont(QFont("", 42))

        self.title_label = QLabel("拖入视频文件到此处")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setFont(QFont("", 16, QFont.Weight.Medium))

        self.hint_label = QLabel("支持 MP4 / MOV / MKV / AVI 等常见格式")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setObjectName("hintLabel")

        self.file_label = QLabel("尚未选择文件")
        self.file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_label.setWordWrap(True)
        self.file_label.setObjectName("fileLabel")

        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.hint_label)
        layout.addSpacing(8)
        layout.addWidget(self.file_label)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setProperty("dragOver", True)
            self.style().unpolish(self)
            self.style().polish(self)

    def dragLeaveEvent(self, event) -> None:  # noqa: ANN001
        self.setProperty("dragOver", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self.setProperty("dragOver", False)
        self.style().unpolish(self)
        self.style().polish(self)

        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                self.set_file(path)
                self.file_dropped.emit(path)
                break
        event.acceptProposedAction()

    def set_file(self, path: str) -> None:
        file_path = Path(path)
        if not file_path.is_file():
            self.file_label.setText("文件无效")
            return
        size_text = format_file_size(file_path.stat().st_size)
        self.file_label.setText(f"{file_path.name}\n{file_path.parent}\n大小：{size_text}")


class MainWindow(QMainWindow):
    def __init__(
        self,
        current_user: User,
        session: AuthSession | None = None,
        login_mode: str = "本地",
    ) -> None:
        super().__init__()
        self.current_user = current_user
        self.current_session = session
        self.login_mode = login_mode
        self.api_client = MineAdminAuthClient.from_config()
        self.source_path: str | None = None
        self.worker: WorkerThread | None = None
        self.setWindowTitle("短视频指纹批量修改工具")
        self.setMinimumSize(560, 520)
        self.resize(640, 580)
        self._build_ui()
        self._check_ffmpeg()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(18)

        header = QLabel("视频指纹批量修改")
        header.setObjectName("header")
        header.setFont(QFont("", 22, QFont.Weight.Bold))

        subtitle = QLabel("拖入一个视频，一键生成多个不同指纹的相同内容视频，输出到原视频目录。")
        subtitle.setWordWrap(True)
        subtitle.setObjectName("subtitle")

        user_row = QHBoxLayout()
        self.user_label = QLabel(f"当前用户：{self.current_user.username}")
        self.user_label.setObjectName("userLabel")
        logout_btn = QPushButton("退出登录")
        logout_btn.clicked.connect(self._logout)
        user_row.addWidget(self.user_label)
        user_row.addStretch()
        user_row.addWidget(logout_btn)

        self.drop_zone = DropZone()
        self.drop_zone.file_dropped.connect(self._on_file_selected)

        browse_btn = QPushButton("选择视频文件")
        browse_btn.clicked.connect(self._browse_file)

        count_row = QHBoxLayout()
        count_label = QLabel("生成数量")
        count_label.setFont(QFont("", 14))

        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 100)
        self.count_spin.setValue(5)
        self.count_spin.setSuffix(" 个")
        self.count_spin.setMinimumWidth(120)

        count_row.addWidget(count_label)
        count_row.addStretch()
        count_row.addWidget(self.count_spin)

        self.generate_btn = QPushButton("生成视频")
        self.generate_btn.setObjectName("primaryButton")
        self.generate_btn.setMinimumHeight(44)
        self.generate_btn.setEnabled(False)
        self.generate_btn.clicked.connect(self._start_generation)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setMinimumHeight(44)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_generation)

        action_row = QHBoxLayout()
        action_row.addWidget(self.cancel_btn)
        action_row.addWidget(self.generate_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)

        self.status_label = QLabel(f"登录方式：{self.login_mode}。请先拖入或选择一个视频文件")
        self.status_label.setWordWrap(True)
        self.status_label.setObjectName("statusLabel")

        root.addWidget(header)
        root.addWidget(subtitle)
        root.addLayout(user_row)
        root.addWidget(self.drop_zone)
        root.addWidget(browse_btn)
        root.addLayout(count_row)
        root.addLayout(action_row)
        root.addWidget(self.progress_bar)
        root.addWidget(self.status_label)

    def _check_ffmpeg(self) -> None:
        if find_ffmpeg():
            return
        QMessageBox.warning(
            self,
            "缺少 FFmpeg",
            "未检测到 FFmpeg。\n\n请在终端运行以下命令安装：\n\nbrew install ffmpeg",
        )
        self.status_label.setText("未安装 FFmpeg，请先运行：brew install ffmpeg")

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频文件",
            str(Path.home()),
            "视频文件 (*.mp4 *.mov *.mkv *.avi *.m4v *.webm *.flv *.wmv);;所有文件 (*)",
        )
        if path:
            self._on_file_selected(path)

    def _on_file_selected(self, path: str) -> None:
        file_path = Path(path)
        if not is_video_file(file_path):
            QMessageBox.warning(self, "格式不支持", "请选择常见视频格式文件。")
            return
        self.source_path = str(file_path.resolve())
        self.drop_zone.set_file(self.source_path)
        self.generate_btn.setEnabled(True)
        self.status_label.setText(f"已选择：{file_path.name}，可开始生成。")

    def _start_generation(self) -> None:
        if not self.source_path:
            return
        if not find_ffmpeg():
            self._check_ffmpeg()
            return

        count = self.count_spin.value()
        self.generate_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.count_spin.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("准备开始…")

        self.worker = WorkerThread(self.source_path, count)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

    def _cancel_generation(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.status_label.setText("正在取消…")

    def _on_progress(self, index: int, total: int, ratio: float, message: str) -> None:
        self.progress_bar.setValue(int(ratio * 100))
        self.status_label.setText(message)

    def _on_finished(self, outputs: list[str]) -> None:
        self._reset_controls()
        self.progress_bar.setValue(100)
        output_dir = Path(outputs[0]).parent if outputs else Path(".")
        self.status_label.setText(f"全部完成！共生成 {len(outputs)} 个视频，保存在：{output_dir}")
        QMessageBox.information(
            self,
            "生成完成",
            f"成功生成 {len(outputs)} 个视频！\n\n保存目录：\n{output_dir}",
        )

    def _on_failed(self, message: str) -> None:
        self._reset_controls()
        self.status_label.setText(message)
        if message != "已取消生成":
            QMessageBox.critical(self, "生成失败", message)

    def _reset_controls(self) -> None:
        self.generate_btn.setEnabled(bool(self.source_path))
        self.cancel_btn.setEnabled(False)
        self.count_spin.setEnabled(True)

    def _logout(self) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "正在处理", "请等待当前任务完成或取消后再退出登录。")
            return
        if self.login_mode == "API" and self.current_session and self.api_client:
            try:
                self.api_client.logout(self.current_session.access_token)
            except AuthApiError as exc:
                QMessageBox.warning(self, "退出提示", f"调用 API 退出失败，将继续本地退出：\n{exc}")
        self.close()
        login = LoginWindow()
        if login.exec() != QDialog.DialogCode.Accepted or login.authenticated_user is None:
            QApplication.instance().quit()
            return
        self.current_user = login.authenticated_user
        self.current_session = login.authenticated_session
        self.login_mode = login.login_mode
        self.user_label.setText(f"当前用户：{self.current_user.username}")
        self.source_path = None
        self.generate_btn.setEnabled(False)
        self.drop_zone.file_label.setText("尚未选择文件")
        self.status_label.setText(f"登录方式：{self.login_mode}。请先拖入或选择一个视频文件")
        QMessageBox.information(self, "登录方式", f"本次登录方式：{self.login_mode}")
        self.show()


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("短视频指纹批量修改工具")
    apply_styles(app)

    login = LoginWindow()
    if login.exec() != QDialog.DialogCode.Accepted or login.authenticated_user is None:
        sys.exit(0)

    QMessageBox.information(None, "登录方式", f"本次登录方式：{login.login_mode}")
    window = MainWindow(
        login.authenticated_user,
        session=login.authenticated_session,
        login_mode=login.login_mode,
    )
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
