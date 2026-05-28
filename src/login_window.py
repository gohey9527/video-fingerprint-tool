"""登录窗口。"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from auth import (
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_ADMIN_USER,
    AuthApiError,
    AuthSession,
    MineAdminAuthClient,
    User,
    UserStore,
)


class LoginWindow(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.authenticated_user: User | None = None
        self.authenticated_session: AuthSession | None = None
        self.login_mode = "本地"
        self.store = UserStore()
        self.api_client = MineAdminAuthClient.from_config()
        self.setWindowTitle("登录 - 短视频指纹工具")
        self.setFixedSize(420, 360)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(14)

        title = QLabel("账户登录")
        title.setObjectName("header")
        title.setFont(QFont("", 22, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hint_text = "请输入账户名和密码后使用工具"
        if self.api_client:
            hint_text = "当前已启用 MineAdmin API 登录"
        hint = QLabel(hint_text)
        hint.setObjectName("loginHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("账户名")
        self.username_input.returnPressed.connect(self._try_login)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("密码")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.returnPressed.connect(self._try_login)

        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setWordWrap(True)

        self.login_btn = QPushButton("登录")
        self.login_btn.setObjectName("primaryButton")
        self.login_btn.setMinimumHeight(42)
        self.login_btn.clicked.connect(self._try_login)

        default_hint = QLabel(
            f"首次使用默认账户：{DEFAULT_ADMIN_USER} / {DEFAULT_ADMIN_PASSWORD}\n"
            "登录后请尽快修改密码"
        )
        default_hint.setObjectName("loginHint")
        default_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        default_hint.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addSpacing(8)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_input)
        layout.addWidget(self.error_label)
        layout.addWidget(self.login_btn)
        layout.addStretch()
        layout.addWidget(default_hint)

        self.username_input.setFocus()

    def _try_login(self) -> None:
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if self.api_client:
            try:
                session = self.api_client.login(username, password)
            except AuthApiError as exc:
                self.error_label.setText(str(exc))
                self.password_input.clear()
                self.password_input.setFocus()
                return
            self.authenticated_session = session
            self.authenticated_user = session.user
            self.login_mode = "API"
            self.accept()
            return

        user = self.store.authenticate(username, password)
        if user:
            self.authenticated_user = user
            self.login_mode = "本地"
            self.accept()
            return

        self.error_label.setText("账户名或密码错误，请重试")
        self.password_input.clear()
        self.password_input.setFocus()

    def closeEvent(self, event) -> None:  # noqa: ANN001
        if self.authenticated_user is None:
            self.reject()
        super().closeEvent(event)
