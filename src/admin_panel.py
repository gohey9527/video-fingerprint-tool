"""管理员使用统计面板。"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from auth import AuthSession, MineAdminAuthClient
from usage import UsageRecord, UsageReporter


EVENT_LABELS = {
    "login": "登录",
    "logout": "退出",
    "generate_video": "生成视频",
}


class AdminUsageWindow(QDialog):
    def __init__(
        self,
        *,
        access_token: str | None = None,
        api_client: MineAdminAuthClient | None = None,
        parent=None,  # noqa: ANN001
    ) -> None:
        super().__init__(parent)
        self.access_token = access_token
        self.reporter = UsageReporter(api_client=api_client)
        self.setWindowTitle("客户端使用统计")
        self.resize(920, 560)
        self._build_ui()
        self._reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("客户端使用统计")
        title.setObjectName("header")
        title.setFont(QFont("", 20, QFont.Weight.Bold))

        subtitle = QLabel(
            "查看各用户通过哪个客户端（Windows / macOS）使用了本应用。"
            "若服务端已接入统计接口，将显示全部用户的记录；否则仅显示本机记录。"
        )
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)

        self.notice_label = QLabel("")
        self.notice_label.setObjectName("loginHint")
        self.notice_label.setWordWrap(True)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["时间", "用户名", "客户端", "平台", "事件", "详情"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)

        action_row = QHBoxLayout()
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self._reload)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        action_row.addStretch()
        action_row.addWidget(refresh_btn)
        action_row.addWidget(close_btn)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.notice_label)
        layout.addWidget(self.table)
        layout.addLayout(action_row)

    def _format_time(self, raw: str) -> str:
        if not raw:
            return ""
        return raw.replace("T", " ").replace("+00:00", " UTC")[:19]

    def _populate_table(self, records: list[UsageRecord]) -> None:
        self.table.setRowCount(len(records))
        for row_index, record in enumerate(records):
            values = [
                self._format_time(record.created_at),
                record.username,
                record.client_id,
                record.client_platform,
                EVENT_LABELS.get(record.event_type, record.event_type),
                record.event_detail,
            ]
            for col_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col_index == 0:
                    item.setTextAlignment(
                        int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                    )
                self.table.setItem(row_index, col_index, item)
        self.table.resizeColumnsToContents()

    def _reload(self) -> None:
        records, notice = self.reporter.list_for_admin(self.access_token)
        self._populate_table(records)
        if notice:
            self.notice_label.setText(notice)
        elif not records:
            self.notice_label.setText("暂无使用记录。")
        else:
            self.notice_label.setText(f"共 {len(records)} 条记录。")
