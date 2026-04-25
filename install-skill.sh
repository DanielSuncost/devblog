#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
mkdir -p "$HERMES_HOME/skills/software-development/devblog"
cp "$ROOT/registries/SKILL.md" "$HERMES_HOME/skills/software-development/devblog/SKILL.md"
echo "Installed Hermes skill to $HERMES_HOME/skills/software-development/devblog/SKILL.md"
