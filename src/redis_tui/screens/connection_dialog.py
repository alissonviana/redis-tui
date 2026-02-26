from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button, Input, Label, Select, Switch, TabbedContent, TabPane
)
from redis_tui.models.connection import ConnectionConfig, ConnectionMode
from redis_tui.services.connection_manager import ConnectionManager


class ConnectionDialog(ModalScreen[ConnectionConfig | None]):
    """Modal for creating or editing a connection."""

    def __init__(self, config: ConnectionConfig | None = None, *args, **kwargs):
        super().__init__(*args, id="connection-dialog", **kwargs)
        self._config = config or ConnectionConfig(name="New Connection")
        self._editing = config is not None

    def compose(self) -> ComposeResult:
        cfg = self._config
        with VerticalScroll(id="connection-form"):
            yield Label(
                "Edit Connection" if self._editing else "New Connection",
                classes="form-title",
            )
            with TabbedContent():
                with TabPane("General"):
                    yield Label("Connection Name")
                    yield Input(cfg.name, id="inp-name", placeholder="My Redis")
                    yield Label("Host")
                    yield Input(cfg.host, id="inp-host", placeholder="localhost")
                    yield Label("Port")
                    yield Input(str(cfg.port), id="inp-port", placeholder="6379")
                    yield Label("Password")
                    yield Input(cfg.password or "", id="inp-password", password=True, placeholder="(optional)")
                    yield Label("Username (ACL)")
                    yield Input(cfg.username or "", id="inp-username", placeholder="(optional)")
                    yield Label("Database")
                    yield Input(str(cfg.db), id="inp-db", placeholder="0")
                    yield Label("Read-only mode")
                    yield Switch(cfg.readonly, id="sw-readonly")

                with TabPane("SSH Tunnel"):
                    yield Label("SSH Host")
                    yield Input(cfg.ssh_host or "", id="inp-ssh-host", placeholder="(optional)")
                    yield Label("SSH Port")
                    yield Input(str(cfg.ssh_port), id="inp-ssh-port", placeholder="22")
                    yield Label("SSH Username")
                    yield Input(cfg.ssh_username or "", id="inp-ssh-user", placeholder="")
                    yield Label("SSH Password")
                    yield Input(cfg.ssh_password or "", id="inp-ssh-pass", password=True, placeholder="(optional)")
                    yield Label("SSH Key File")
                    yield Input(cfg.ssh_key_file or "", id="inp-ssh-key", placeholder="~/.ssh/id_rsa")

                with TabPane("SSL/TLS"):
                    yield Label("Enable SSL")
                    yield Switch(cfg.ssl, id="sw-ssl")
                    yield Label("CA Certificate File")
                    yield Input(cfg.ssl_ca_cert or "", id="inp-ssl-ca", placeholder="(optional)")
                    yield Label("Client Certificate File")
                    yield Input(cfg.ssl_certfile or "", id="inp-ssl-cert", placeholder="(optional)")
                    yield Label("Client Key File")
                    yield Input(cfg.ssl_keyfile or "", id="inp-ssl-key", placeholder="(optional)")

                with TabPane("Advanced"):
                    yield Label("Mode")
                    yield Select(
                        [
                            ("Standalone", ConnectionMode.STANDALONE),
                            ("Cluster", ConnectionMode.CLUSTER),
                            ("Sentinel", ConnectionMode.SENTINEL),
                        ],
                        value=cfg.mode,
                        id="sel-mode",
                    )
                    yield Label("Sentinel Master Name")
                    yield Input(cfg.sentinel_master or "", id="inp-sentinel-master", placeholder="mymaster")

            yield Label("", id="test-result")
            with Horizontal(id="dialog-actions"):
                yield Button("Test", id="btn-test", variant="default")
                yield Button("Cancel", id="btn-cancel", variant="default")
                yield Button("Save", id="btn-save", variant="primary")

    def _collect_config(self) -> ConnectionConfig:
        def val(id_: str) -> str:
            try:
                widget = self.query_one(f"#{id_}", Input)
                return widget.value.strip()
            except Exception:
                return ""

        def sw(id_: str) -> bool:
            try:
                return self.query_one(f"#{id_}", Switch).value
            except Exception:
                return False

        try:
            port = int(val("inp-port") or "6379")
        except ValueError:
            port = 6379
        try:
            db = int(val("inp-db") or "0")
        except ValueError:
            db = 0
        try:
            ssh_port = int(val("inp-ssh-port") or "22")
        except ValueError:
            ssh_port = 22

        try:
            mode_select = self.query_one("#sel-mode", Select)
            mode = mode_select.value or ConnectionMode.STANDALONE
        except Exception:
            mode = ConnectionMode.STANDALONE

        return ConnectionConfig(
            id=self._config.id,
            name=val("inp-name") or "New Connection",
            host=val("inp-host") or "localhost",
            port=port,
            password=val("inp-password") or None,
            username=val("inp-username") or None,
            db=db,
            mode=mode,
            ssl=sw("sw-ssl"),
            ssl_ca_cert=val("inp-ssl-ca") or None,
            ssl_certfile=val("inp-ssl-cert") or None,
            ssl_keyfile=val("inp-ssl-key") or None,
            readonly=sw("sw-readonly"),
            color=self._config.color,
            ssh_host=val("inp-ssh-host") or None,
            ssh_port=ssh_port,
            ssh_username=val("inp-ssh-user") or None,
            ssh_password=val("inp-ssh-pass") or None,
            ssh_key_file=val("inp-ssh-key") or None,
            sentinel_master=val("inp-sentinel-master") or None,
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        result_label = self.query_one("#test-result", Label)

        if event.button.id == "btn-cancel":
            self.dismiss(None)

        elif event.button.id == "btn-test":
            config = self._collect_config()
            result_label.update("Testing connection...")
            success, message = await ConnectionManager.test_connection(config)
            if success:
                result_label.update(f"[green]Connected: {message}[/green]")
            else:
                result_label.update(f"[red]Failed: {message}[/red]")

        elif event.button.id == "btn-save":
            config = self._collect_config()
            if not config.name:
                result_label.update("[red]Connection name is required[/red]")
                return
            self.dismiss(config)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
