from __future__ import annotations
import asyncio
from datetime import datetime
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, RichLog
from textual.worker import Worker, WorkerState


class PubSubWidget(Vertical):
    """Real-time Pub/Sub viewer.

    Allows the user to subscribe to a Redis channel and watch messages
    arrive in real time.  A background worker handles the blocking
    pubsub loop; the worker is cancelled on unsubscribe or when the
    widget is unmounted.
    """

    DEFAULT_CSS = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, id="pubsub-widget", **kwargs)
        self._worker: Worker | None = None
        self._channel: str | None = None

    def compose(self) -> ComposeResult:
        with Horizontal(id="pubsub-controls"):
            yield Input(
                placeholder="Channel name (e.g. news, events:*)",
                id="pubsub-channel-input",
            )
            yield Button("Subscribe", id="btn-subscribe", variant="primary")
            yield Button("Unsubscribe", id="btn-unsubscribe", variant="default")
        yield RichLog(id="pubsub-log", highlight=True, markup=True, wrap=True)

    # ------------------------------------------------------------------
    # Button handling
    # ------------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "btn-subscribe":
            self._do_subscribe()
        elif event.button.id == "btn-unsubscribe":
            self._do_unsubscribe()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "pubsub-channel-input":
            event.stop()
            self._do_subscribe()

    # ------------------------------------------------------------------
    # Subscribe / Unsubscribe
    # ------------------------------------------------------------------

    def _do_subscribe(self) -> None:
        channel = self.query_one("#pubsub-channel-input", Input).value.strip()
        if not channel:
            self._log_system("Please enter a channel name.")
            return

        # Cancel existing subscription first
        self._do_unsubscribe()

        self._channel = channel
        self._log_system(f"Subscribing to [bold cyan]{channel}[/bold cyan] ...")
        self._worker = self.run_worker(
            self._listen(channel),
            exclusive=True,
            name=f"pubsub-{channel}",
        )

    def _do_unsubscribe(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self._worker = None
        if self._channel:
            self._log_system(
                f"Unsubscribed from [bold cyan]{self._channel}[/bold cyan]."
            )
            self._channel = None

    # ------------------------------------------------------------------
    # Background listener
    # ------------------------------------------------------------------

    async def _listen(self, channel: str) -> None:
        """Background coroutine that receives messages from Redis pub/sub."""
        redis_client = self.app._manager.get_client()  # type: ignore[attr-defined]
        pubsub = redis_client.pubsub()
        try:
            await pubsub.subscribe(channel)
            self._log_system(
                f"Subscribed to [bold cyan]{channel}[/bold cyan]. Waiting for messages..."
            )
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=0.1,
                )
                if message is not None:
                    self._handle_message(message)
                # Yield control briefly so the UI stays responsive
                await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            self._log_system(f"[red]Error: {exc}[/red]")
        finally:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _handle_message(self, message: dict) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        ch = message.get("channel", b"")
        if isinstance(ch, bytes):
            ch = ch.decode("utf-8", errors="replace")
        data = message.get("data", b"")
        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="replace")
        log = self.query_one("#pubsub-log", RichLog)
        log.write(f"[dim]{ts}[/dim] [cyan]{ch}[/cyan]: {data}")

    def _log_system(self, text: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        log = self.query_one("#pubsub-log", RichLog)
        log.write(f"[dim]{ts}[/dim] [yellow]{text}[/yellow]")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_unmount(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self._worker = None
