---
id: T-0005
title: The Haiku model string differs between pipeline stages
status: DECIDED
tags: [pipeline, chore]
anchor: ntk-pulse/triage.py:27
---

## What

`triage.py:27` pins `claude-haiku-4-5-20251001`. `build_digest.py:53` uses
`claude-haiku-4-5`. Both resolve today.

## Why

Small, and worth closing precisely because it is small: it is the cheapest
possible demonstration that a check catches a claim going false. The day an
alias moves, or a dated snapshot is retired, the two stages diverge in
behaviour while both still "work" — which is this project's characteristic
failure shape at a smaller scale.

Pin or float, but do it in one place. A shared constant is the obvious move and
nobody has made it.

## Check

```sh
n=$(grep -rhoE 'claude-haiku-[0-9a-zA-Z.-]+' ntk-pulse/*.py | sort -u | wc -l | tr -d ' ')
if [ "$n" -ne 1 ]; then
  echo "$n distinct Haiku model strings:"
  grep -rnE 'claude-haiku-[0-9a-zA-Z.-]+' ntk-pulse/*.py
  exit 1
fi
```
