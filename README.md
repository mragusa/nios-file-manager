# nios-file-manager

A small **Textual** TUI for interacting with an **Infoblox NIOS** grid via **WAPI**, using the `ibx-sdk` `Gift` client.

The app provides a split-pane terminal UI with a command input at the bottom. Current focus is on establishing a WAPI session and showing grid/status + command output.

## What it looks like

Layout (current):
- **Left pane**: “NIOS Files” (intended for file listings / results)
- **Right pane**:
  - **Grid Information** (status)
  - **Command Output** (logs/results)
  - **Command input** (single-line input at the bottom)

Keyboard:
- `d` — toggle dark mode

## Requirements

- Python 3.10+ (works on newer versions as well)
- Network reachability to your NIOS Grid Manager (HTTPS/WAPI)
- Packages:
  - `textual`
  - `ibx-sdk`

## Install

```bash
python -m venv venv
source venv/bin/activate
pip install -U pip
pip install textual ibx-sdk
```

## Run

```bash
python ./nios-file-manager.py
```

## Usage

Type commands into the input at the bottom and press **Enter**.

### Commands

- `help`  
  Shows available commands.

- `connect <grid_mgr> <username> <password>`  
  Connects to the specified Grid Manager (IP/hostname). The app sets `wapi_ver` to `2.13`.

  Example:
  ```text
  connect 192.168.50.150 admin infoblox
  ```

After a successful connect, the app attempts to query the grid name and display it in the **Grid Information** pane.

> Note: Passing passwords on the command line is convenient but not ideal for security (shell history, screen recording, etc.). A future improvement is prompting securely or loading from config/env vars.

## Development notes

- The UI is built with `Horizontal` + `Vertical` containers and uses:
  - `Static`-style panes for labels/panels
  - `RichLog` for output panes (supports Rich markup like `[blue]text[/blue]`)
- Some WAPI endpoints may return JSON payloads as a **list** of objects (even for single results). Code should handle both list/dict shapes when parsing responses.

## Roadmap ideas

- File listing pane backed by `RichLog` or `DataTable`
- Modal selection popups for itemized actions (Textual `ModalScreen` + `OptionList`/`SelectionList`)
- Config/credential handling (env vars, config file, secure prompts)
- Workers for non-blocking WAPI calls (avoid UI freezes on slow requests)

## License

Add your preferred license (e.g., MIT) in `LICENSE`.
