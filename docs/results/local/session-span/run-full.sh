#!/bin/zsh
# the full 80-frame local run; re-issue after a pause (finished calls come from the run's cache)
S=/private/tmp/claude-501/-Users-harrisonogle-src-harrisonogle-agentic-escort/00000000-0000-0000-0000-000000000000/scratchpad/local3
cd /Users/harrisonogle/src/harrisonogle/agentic-escort/.claude/worktrees/local3
date >> $S/run-full.wrap.log
uv run scry eval run $S/local3-full.toml >> $S/run-full.log 2>&1
echo "exit=$? $(date)" >> $S/run-full.log
date >> $S/run-full.wrap.log
