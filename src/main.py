"""短视频指纹批量修改工具 - Mac 桌面端。"""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication,
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

from processor import find_ffmpeg, format_file_size, is_video_file, process_videos


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
    def __init__(self) -> None:
        super().__init__()
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

        self.status_label = QLabel("请先拖入或选择一个视频文件")
        self.status_label.setWordWrap(True)
        self.status_label.setObjectName("statusLabel")

        root.addWidget(header)
        root.addWidget(subtitle)
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


def apply_styles(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(
        """
        QMainWindow, QWidget {
            background: #111318;
            color: #eef0f4;
        }
        #header {
            color: #ffffff;
        }
        #subtitle, #hintLabel, #statusLabel {
            color: #9aa3b2;
        }
        #fileLabel {
            color: #c8d0dc;
            font-size: 13px;
        }
        #dropZone {
            border: 2px dashed #3a4252;
            border-radius: 16px;
            background: #171b22;
        }
        #dropZone[dragOver="true"] {
            border-color: #5b8cff;
            background: #1a2233;
        }
        QPushButton {
            background: #252b36;
            color: #eef0f4;
            border: 1px solid #3a4252;
            border-radius: 10px;
            padding: 10px 16px;
            font-size: 14px;
        }
        QPushButton:hover {
            background: #2d3440;
        }
        QPushButton:disabled {
            color: #667085;
            background: #1b2028;
        }
        #primaryButton {
            background: #4f7cff;
            border-color: #4f7cff;
            color: white;
            font-weight: 600;
        }
        #primaryButton:hover {
            background: #628cff;
        }
        QSpinBox {
            background: #171b22;
            border: 1px solid #3a4252;
            border-radius: 8px;
            padding: 6px 10px;
            color: #eef0f4;
        }
        QProgressBar {
            border: 1px solid #3a4252;
            border-radius: 8px;
            background: #171b22;
            text-align: center;
            color: #eef0f4;
            height: 22px;
        }
        QProgressBar::chunk {
            border-radius: 7px;
            background: #4f7cff;
        }
        """
    )


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("短视频指纹批量修改工具")
    apply_styles(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
