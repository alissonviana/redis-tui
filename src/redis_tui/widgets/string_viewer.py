from __future__ import annotations
import json
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Button, TextArea, TabbedContent, TabPane, Label
from textual.message import Message


class StringViewer(Vertical):
    """Viewer and editor for Redis String values."""

    class SaveRequested(Message):
        def __init__(self, new_value: str) -> None:
            super().__init__()
            self.new_value = new_value

    def __init__(self, value: str, *args, **kwargs):
        super().__init__(*args, id="string-viewer", **kwargs)
        self._raw_value = value or ""
        self._modified = False

    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("Text", id="tab-text"):
                yield TextArea(
                    self._raw_value,
                    id="value-textarea",
                    language=None,
                )
            with TabPane("JSON", id="tab-json"):
                json_text = self._try_format_json(self._raw_value)
                yield TextArea(
                    json_text,
                    id="value-textarea-json",
                    language="json",
                    read_only=True,
                )
            with TabPane("HEX", id="tab-hex"):
                hex_text = self._to_hex(self._raw_value)
                yield TextArea(
                    hex_text,
                    id="value-textarea-hex",
                    read_only=True,
                )
        with Horizontal(id="string-actions"):
            yield Label("", id="save-status")
            yield Button("Save", id="btn-save", variant="primary")

    def _try_format_json(self, value: str) -> str:
        try:
            parsed = json.loads(value)
            return json.dumps(parsed, indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            return f"// Not valid JSON\n{value}"

    def _to_hex(self, value: str) -> str:
        try:
            encoded = value.encode("utf-8")
            hex_pairs = [f"{b:02x}" for b in encoded]
            # Format as 16 bytes per line
            lines = []
            for i in range(0, len(hex_pairs), 16):
                chunk = hex_pairs[i:i+16]
                hex_part = " ".join(chunk)
                ascii_part = "".join(
                    chr(int(h, 16)) if 32 <= int(h, 16) < 127 else "."
                    for h in chunk
                )
                lines.append(f"{i:08x}  {hex_part:<47}  |{ascii_part}|")
            return "\n".join(lines) if lines else "(empty)"
        except Exception:
            return "(binary data)"

    def update_value(self, value: str) -> None:
        self._raw_value = value or ""
        try:
            self.query_one("#value-textarea", TextArea).load_text(self._raw_value)
            self.query_one("#value-textarea-json", TextArea).load_text(
                self._try_format_json(self._raw_value)
            )
            self.query_one("#value-textarea-hex", TextArea).load_text(
                self._to_hex(self._raw_value)
            )
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            event.stop()
            textarea = self.query_one("#value-textarea", TextArea)
            self.post_message(self.SaveRequested(textarea.text))
            status = self.query_one("#save-status", Label)
            status.update("Saved!")
