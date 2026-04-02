#!/usr/bin/env python3

from __future__ import annotations

# from logging import info
import shlex

from datetime import datetime
from typing import Callable

# Textual and Rich Imports
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, RichLog, Static, Input
from rich.table import Table, Column

from textual.screen import ModalScreen
from textual.widgets import OptionList, Button, Label
from textual.widgets.option_list import Option

# from ibx_sdk.logger.ibx_logger import init_logger, increase_log_level
from ibx_sdk.nios.exceptions import WapiRequestException
from ibx_sdk.nios.gift import Gift

# TODO: read file for username and password


class Pane(Static):
    """Box with Label"""


class Output(RichLog):
    """Show Command Output"""


class FilePicker(ModalScreen[dict | None]):
    DEFAULT_CSS = """
    FilePicker { align: center middle; }
    #dialog { width: 80%; height: 80%; border: thick $primary; padding: 1; background: $surface; }
    #choices { height: 1fr; }
    """

    def __init__(self, files: list[dict]):
        super().__init__()
        self.files = files

    def compose(self) -> ComposeResult:
        # Store the index as the option id so we can map back to the dict
        yield OptionList(
            *(
                Option(f"{name}", id=str(ref))
                for d in self.files
                for name, ref in d.items()
            ),
            id="choices",
        )

    def on_mount(self) -> None:
        self.query_one("#choices", OptionList).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        ref = event.option_id
        if ref is None:
            self.dismiss(None)
            return
        selected = next((f for f in self.files if f.get("_ref") == ref), None)
        self.dismiss(selected)


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
            yield Output(name="Files", id="files")

            with Vertical(id="Manager"):
                yield Pane("Grid Information", id="gridinfo")
                yield Output(name="Command", id="command")
                with Static():
                    yield Input(placeholder="Try: help> ", id="cmd")
        yield Footer()

    def on_mount(self) -> None:
        self.wapi: Gift = Gift()
        self.files_cache: list[dict] = []
        self.query_one("#cmd", Input).focus()

    # Commands for input
    def cmd_help(self, args: list[str]) -> None:
        self._set_logs(
            "Commands:\n"
            "- help\n"
            "- connect grid user password\n"
            "- list - show current files on NIOS grid\n"
            "- download - download file to local system"
        )

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

        self.wapi.grid_mgr = grid_mgr
        self.wapi.wapi_ver = "2.13"

        try:
            self.wapi.connect(username=username, password=password)
            self._set_logs(f"Connected to {self.wapi.grid_mgr} as {username}")
        except WapiRequestException as err:
            self._set_logs(f"Connect failed: {err}")
            self._set_grid_info(("Not Connected"))
            self.wapi = Gift()
            return
        self.grid_info()

    def cmd_list(self, args: list[str]) -> None:
        table = Table(
            Column(header="Name", justify="center", style="green"),
            Column(header="Type", justify="center", style="white"),
            Column(header="Modified Time", justify="center", style="white"),
            show_header=True,
            header_style="bold",
            row_styles=["dim", ""],
        )
        current_files = self.wapi.get(
            "tftpfiledir",
            params={
                "directory": "/",
                "_return_fields": ["name", "type", "last_modify"],
            },
        )
        if current_files.status_code != 200:
            self._set_files(
                f"{current_files.status_code} {current_files.json()[0].get("text")}"
            )
        else:
            for f in current_files.json():
                modify_date = datetime.fromtimestamp(f["last_modify"])
                table.add_row(f["name"], f["type"], str(modify_date))
                if f["type"] == "FILE":
                    self.files_cache.append({f["name"]: f["_ref"]})
        self._set_files(table)

    def cmd_download(self, args: list[str]) -> None:
        if not getattr(self, "files_cache", None):
            self._set_logs("No files loaded yet. Run your list command first.")
            return

        def _on_picked(self, selected: dict | None) -> None:
            if selected is None:
                self._set_logs("[yellow]Cancelled[/yellow]")
                return

            self._set_logs(
                f"Selected: [blue]{selected.get('name')}[/blue] ref={selected.get('_ref')}"
            )

        # TODO: call your real download function here
        # self.download_file(selected)

        self.push_screen(FilePicker(self.files_cache), _on_picked)

    def grid_info(self) -> None:
        if self.wapi is None:
            self._set_grid_info("Not Connected")
            return
        infoblox_name = self.wapi.get(
            "grid", params={"_return_fields": ["name", "service_status"]}
        )
        if infoblox_name.status_code != 200:
            self._set_grid_info(
                f"{infoblox_name.status_code} {infoblox_name.json()[0].get('code')} {infoblox_name.json()[0].get('text')}"
            )
        else:
            self._set_grid_info(
                f"Infoblox Grid: {infoblox_name.json()[0].get('name')}\nGrid Master: {self.wapi.grid_mgr}\nService Status: {infoblox_name.json()[0].get('service_status')}\n"
            )

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
            "list": self.cmd_list,
            "download": self.cmd_download,
        }
        fn = commands.get(cmd.lower())
        if fn is None:
            self._set_logs(f"Unknown command: {cmd!r} (try: help)")
            return
        fn(args)

    def _set_logs(self, text: str) -> None:
        self.query_one("#command", RichLog).write(text)

    def _set_grid_info(self, text: str) -> None:
        self.query_one("#gridinfo", Static).update(text)

    def _set_files(self, text) -> None:
        self.query_one("#files", RichLog).write(text)

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )


if __name__ == "__main__":
    app = NiosfileManager()
    app.run()
