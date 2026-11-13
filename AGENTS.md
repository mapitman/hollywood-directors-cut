# AGENTS.md

Guidance for AI agents that work on this repository.

## What this repository is

A Docker image that runs Hollywood (a tmux "hacker movie" launcher) with extra and replaced widgets. The repository
holds the Dockerfile, the widget scripts, and the guard and layout scripts. Hollywood itself comes from a pinned
upstream commit and is not stored here.

## Commands

- `just build` builds the image `mapitman/hollywood-directors-cut`. The build is the main check, because there are no
  unit tests.
- `just run` builds the image, then runs it.
- To test one widget, override the entrypoint. The image entrypoint is `hollywood-entrypoint`, so any argument after the
  image name goes to Hollywood and not to the widget.

  ```sh
  docker run -it --rm --entrypoint /opt/hollywood/lib/hollywood/<widget> mapitman/hollywood-directors-cut
  ```

- To test a widget without a terminal, run it under `script`. Set the size first with
  `script -qec "stty rows 30 cols 100; docker run -t ..." /dev/null`. Without it, the terminal size is 0 x 0, and
  widgets such as `nms` draw nothing.

## How widgets work

- Each widget is an executable script. The Dockerfile copies it to `/usr/lib/hollywood/<name>`.
- Near the end of the Dockerfile, the real widgets move to `/opt/hollywood/lib/hollywood`. A symlink to
  `widget-guard.sh` replaces each one in `/usr/lib/hollywood`. Therefore each new widget needs its `COPY` line before
  that step.
- The real widgets keep a `lib/hollywood/` path on purpose. They stop each other with `pkill -f lib/hollywood/` on
  ctrl-c.
- The guard starts a widget only if the pane fits it. The minimum sizes are in the `MIN_COLS` and `MIN_ROWS` tables and
  the `min_rows` function in `widget-guard.sh`. A widget with no entry runs in any pane.
- Each widget script follows the same pattern:
  - Exit with status 1 if its tool is missing (`command -v ... || exit 1`).
  - Trap TERM and HUP, stop the child, and restore the terminal (alternate screen, cursor, colors). The guard stops
    widgets with TERM, and most tools do not clean up.
  - Keep the terminal as stdin with `<&0`, because bash gives a background job `/dev/null`. Do not add `<&0` to a
    command that reads from a pipe, because it replaces the pipe.

## Adding or removing a widget

1. Add or delete the script and its `COPY` or `rm` line in the Dockerfile. Add the package to the `apt-get install` list.
   If Debian has no package, build from a pinned upstream commit and remove the build tools, as the `nms` step does.
2. Add the minimum size to `widget-guard.sh` if the widget needs one.
3. Update `README.md`: the widget table, the minimum-size table, the environment variables table, a section for the
   widget, and the widget count (it appears in three places).
4. Update `THIRD-PARTY.md` with the widget, its package and its license.
5. Run `just build`, then run the widget with the `--entrypoint` command above.

## Pinned upstream sources

- Hollywood comes from a pinned commit (tag 1.25). `launcher.patch` applies with `--fuzz=0`, so the build fails if the
  upstream code around a change differs.
- `no-more-secrets` (the `nms` widget) comes from a pinned commit (tag v1.0.1).
- When you update a pin, rebuild and check that the patch still applies.

## Workflow

- Check `git status` and the current branch first. Never commit to `main`. Use a branch with a type prefix, such as
  `feature/` or `chore/`.
- Write commit subjects in the imperative mood, with a capital letter and no trailing period. Put issue numbers in the
  body, never in the subject.
- Build the image before you commit.
