"""登录窗口。"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
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
    SavedLogin,
    SavedLoginStore,
    User,
    UserStore,
    is_admin_user,
)


class LoginWindow(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.authenticated_user: User | None = None
        self.authenticated_session: AuthSession | None = None
        self.login_mode = "本地"
        self.store = UserStore()
        self.saved_login_store = SavedLoginStore()
        self.saved_login = self.saved_login_store.load()
        self.api_client = MineAdminAuthClient.from_config()
        self.setWindowTitle("登录 - 短视频指纹工具")
        self.setFixedSize(420, 390)
        self._build_ui()
        self._apply_saved_login()

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

        self.remember_checkbox = QCheckBox(
            "记住账号（下次自动登录）" if self.api_client else "记住账号"
        )
        self.remember_checkbox.setObjectName("loginHint")

        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setWordWrap(True)

        self.login_btn = QPushButton("登录")
        self.login_btn.setObjectName("primaryButton")
        self.login_btn.setMinimumHeight(42)
        self.login_btn.clicked.connect(self._try_login)

        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addSpacing(8)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_input)
        layout.addWidget(self.remember_checkbox)
        layout.addWidget(self.error_label)
        layout.addWidget(self.login_btn)
        layout.addStretch()

        if not self.api_client:
            default_hint = QLabel(
                f"首次使用默认账户：{DEFAULT_ADMIN_USER} / {DEFAULT_ADMIN_PASSWORD}\n"
                "登录后请尽快修改密码"
            )
            default_hint.setObjectName("loginHint")
            default_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            default_hint.setWordWrap(True)
            layout.addWidget(default_hint)

        self.username_input.setFocus()

    def _apply_saved_login(self) -> None:
        if not self.saved_login:
            return
        if self.saved_login.username:
            self.username_input.setText(self.saved_login.username)
        if self.saved_login.remember_username or self.saved_login.remember_session:
            self.remember_checkbox.setChecked(True)

    def _persist_login(self, username: str, session: AuthSession | None, login_mode: str) -> None:
        remember = self.remember_checkbox.isChecked()
        if not remember:
            self.saved_login_store.clear()
            return

        saved = SavedLogin(
            username=username,
            remember_username=True,
            remember_session=login_mode == "API" and session is not None,
            login_mode=login_mode,
            refresh_token=session.refresh_token if session else "",
        )
        self.saved_login_store.save(saved)

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
            self._persist_login(username, session, self.login_mode)
            self.accept()
            return

        user = self.store.authenticate(username, password)
        if user:
            self.authenticated_user = user
            self.authenticated_session = AuthSession(
                user=user,
                access_token="",
                refresh_token="",
                expire_at=0,
                is_admin=is_admin_user(user.username),
            )
            self.login_mode = "本地"
            self._persist_login(username, None, self.login_mode)
            self.accept()
            return

        self.error_label.setText("账户名或密码错误，请重试")
        self.password_input.clear()
        self.password_input.setFocus()

    def closeEvent(self, event) -> None:  # noqa: ANN001
        if self.authenticated_user is None:
            self.reject()
        super().closeEvent(event)
