"""应用全局样式。"""

from PyQt6.QtWidgets import QApplication


def apply_styles(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(
        """
        QMainWindow, QDialog, QWidget {
            background: #111318;
            color: #eef0f4;
        }
        #header {
            color: #ffffff;
        }
        #subtitle, #hintLabel, #statusLabel, #loginHint {
            color: #9aa3b2;
        }
        #fileLabel, #userLabel {
            color: #c8d0dc;
            font-size: 13px;
        }
        #errorLabel {
            color: #ff6b6b;
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
        QLineEdit {
            background: #171b22;
            border: 1px solid #3a4252;
            border-radius: 8px;
            padding: 10px 12px;
            color: #eef0f4;
            font-size: 14px;
        }
        QLineEdit:focus {
            border-color: #5b8cff;
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
