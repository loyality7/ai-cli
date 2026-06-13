# ai-cli

```text
   █▀▀█  ▀       █▀▀█ █    ▀ 
   █▄▄█ ▀█▀      █    █   ▀█▀
   █  █ ▀▀▀      █▄▄█ ▀▀▀ ▀▀▀
```

Lightweight AI partner living inside your terminal.
Type naturally. It understands. It fixes. It executes.

## Install

You can install the CLI globally using any of the following methods:

### Recommended (pipx)
Installs the tool in an isolated environment and makes the `ai` command available globally:
```bash
pipx install aicli-x
```

### Ultra-fast (uv)
Installs the tool in milliseconds using the Rust-based package manager:
```bash
uv tool install aicli-x
```

### Standard (pip)
```bash
pip install aicli-x
```

### Local Development
```bash
git clone https://github.com/loyality7/ai-cli.git
cd ai-cli
pip install -e .
```

## Usage

```
ai                      # opens REPL
ai "fix this"           # one-shot
ai --shell "list files" # command-only mode
ai --setup              # re-configure
ai doctor               # run environment & security diagnostics
ai dashboard            # display telemetry & session dashboard
```
