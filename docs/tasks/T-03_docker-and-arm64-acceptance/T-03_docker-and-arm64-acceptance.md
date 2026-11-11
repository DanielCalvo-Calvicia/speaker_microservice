# T-03 — Docker and arm64 acceptance

| | |
|---|---|
| Status | done |
| Kind | epic |
| Depends on | T-01, T-02 |
| Blocks | — |

## Goal

Prove, by running it on this PC (amd64, Docker Desktop, F15), that the speaker image builds, runs and answers every endpoint, survives a restart and a recreate, holds no secret and no dev tools, and stops cleanly with `docker stop`: **only on `null`**, because Docker on a Windows host cannot reach the sound card. The real device is proven natively on Windows (T-01.7); a container with `/dev/snd` and arm64 are postponed (T-03.5).

## Rules for the whole epic

- Never deploy from the working folders and never touch `deployment/config/local`. Copy the working tree of the speaker (without `windows/`, `.git`, `.env*`, caches) into a scratch folder, `git init` and commit it there, write a scratch config folder (the catalogue with absolute library paths, `services/`, a one-machine layout, `robot.toml`, `machines/robot.toml` with a scratch workdir, `local/speaker.toml` with `git = "<scratch repo>"` and `SPEAKER_BACKEND = "null"`) and run `oblivion.py <command> --host robot --config <scratch config>`; stt's [T-03.1](../../../../stt_microservice/docs/tasks/T-03_docker-and-arm64-acceptance/T-03.1_amd64-build.md) describes it. If the tool refuses Docker for an audio service on Windows and T-02.3 did not change that, use the manual route.
- Always `docker --context desktop-linux ...`; `MSYS_NO_PATHCONV=1` in Git Bash; remove only what this run created; delete the scratch folders at the end. Ports 7998 to 8005 free before and after.
- Each task is `manual`: say what it does and costs, wait for "go". **No sound is played in this epic** (the null sink discards the audio).

## Subtasks

| Order | Task | Kind | State |
|---|---|---|---|
| 1 | [T-03.1 Build the image on amd64](T-03.1_amd64-build.md) | manual | blocked |
| 2 | [T-03.2 Run the container on `null` and call every endpoint](T-03.2_run-and-call.md) | manual | blocked |
| 3 | [T-03.3 Restart, recreate and `docker stop`](T-03.3_restart-recreate-stop.md) | manual | blocked |
| 4 | [T-03.4 Image contents and secrets](T-03.4_image-contents-and-secrets.md) | manual | blocked |
| 5 | [T-03.5 Docker with `/dev/snd`, and on arm64](T-03.5_docker-with-dev-snd-and-arm64.md) | manual | postponed |
| 6 | [T-03.6 Record what was verified](T-03.6_record-the-results.md) | docs | blocked |

## Exit criteria

T-03.1 to T-03.4 and T-03.6 are done with numbers; the documents say which routes were proven (Docker on `null`, amd64) and which were not (`/dev/snd`, arm64, a real device in a container).
