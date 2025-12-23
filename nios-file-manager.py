#!/usr/bin/env python3

import shlex
import sys
from typing import Callable

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, RichLog, Static, Input

# from ibx_sdk.logger.ibx_logger import init_logger, increase_log_level
from ibx_sdk.nios.exceptions import WapiRequestException
from ibx_sdk.nios.gift import Gift

# TODO: read file for username and password
wapi = Gift()


class Pane(Static):
    """Box with Label"""


class Output(RichLog):
    """Show Command Output"""


class NiosfileManager(App):
    """A Textual app to manage files on NIOS Grids."""

    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]
    # TODO: Seperate into seperate file
    CSS = """
    /* Horizontal already expands to fill the screen (1fr x 1fr). */
    Horizontal {
        height: 1fr;
    }

    Pane {
        border: solid green;
        content-align: center middle;
    }
    Output {
        border: solid green;
        content-align: center middle;
    }

    /* Left column */
    #files {
        width: 3fr;   /* make it narrower/wider by changing the ratio */
    }

    /* Right column container */
    #Manager {
        width: 2fr;   /* right column twice as wide as left */
    }

    /* Split the right column into top/bottom */
    #gridinfo {
        height: 1fr;
    }

    #command {
        border: solid green;
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Horizontal():
            yield Pane("NIOS Files", id="files")

            with Vertical(id="Manager"):
                yield Pane("Grid Information", id="gridinfo")
                yield Output(name="Command", id="command")
                with Static():
                    yield Input(placeholder="Try: help> ", id="cmd")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#cmd", Input).focus()

    # Commands for input
    def cmd_help(self, args: list[str]) -> None:
        self._set_logs("Commands:\n" "- help\n" "- connect grid user password\n")

    def cmd_connect(self, args: list[str]) -> None:
        # Expected: connect <grid_mgr> <username> <password>
        if len(args) != 3:
            self._set_logs("Usage: connect <grid_mgr> <username> <password>")
            return

        grid_mgr, username, password = args

        # Optional: extra validation
        if not grid_mgr.strip():
            self._set_logs("grid_mgr cannot be empty")
            return
        if not username.strip() or not password:
            self._set_logs("Username/password cannot be empty")
            return

        wapi.grid_mgr = grid_mgr
        wapi.wapi_ver = "2.13"

        try:
            wapi.connect(username=username, password=password)
        except WapiRequestException as err:
            self._set_logs(f"Connect failed: {err}")
            self.wapi = None
            return

        self.wapi = wapi
        self._set_logs(f"Connected to {wapi.grid_mgr} as {username}")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip()
        event.input.value = ""

        if not raw:
            return

        try:
            parts = shlex.split(raw)
        except ValueError as e:
            self._set_logs(f"Parse error: {e}")
            return

        cmd, *args = parts
        commands: dict[str, Callable[[list[str]], None]] = {
            "help": self.cmd_help,
            "connect": self.cmd_connect,
        }
        fn = commands.get(cmd.lower())
        if fn is None:
            self._set_logs(f"Unknown command: {cmd!r} (try: help)")
            return

        fn(args)

    def _set_logs(self, text: str) -> None:
        self.query_one("#command", RichLog).write(text)

    def _set_grid_info(self, text: str) -> None:
        self.query_one("#gridinfo", RichLog).write(text)

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )


if __name__ == "__main__":
    app = NiosfileManager()
    app.run()
