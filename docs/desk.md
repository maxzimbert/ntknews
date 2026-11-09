# The desk

The editor's morning page: https://claude.ai/artifact/6ED6FvMYbhFKyq7uWeeWy3 (private).

`scripts/desk.py OUT.html` builds it. A scheduled task on the editor's Mac (`ntk-morning-desk`,
weekdays about 7:40, in the desktop app's Scheduled list) pulls, runs the script, and republishes the
page to that URL. The app has to be open; if it is closed, the run happens at next launch.

What it reads, all read-only and none of it paid:

- `scripts/rot.sh`: STALE tickets (with why), READY ones, manual checks
- `scripts/prepublish.py` on the live edition: blockers and warnings
- `scripts/voice_review.py`: staging's composed Backstory drafts when they are newer than the last
  publish, otherwise the live edition. Counts only; the reading pass is the `voice-review` skill.
- `gh run list` for the bots, `gh pr list` for open PRs (older than 14 days is flagged)
- `editorial/object-links-health.json` (flagged when older than 7 days)

GitHub delays this repo's scheduled runs by hours (pulse-scan, set to every 20 minutes, ran five
hours apart on 2026-11-09), so a bot is flagged only after 8 hours without a run, or on a failure.

The page carries no judgment the scripts did not make. To change what it shows, change the script.
