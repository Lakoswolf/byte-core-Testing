# Test Byte in an Ubuntu dev container

The repository includes an optional Ubuntu 24.04 x86_64 test environment in `.devcontainer/`. It installs Python 3.12 from Ubuntu, Git, Bash, Zsh, and the utilities needed to build and exercise a candidate. Byte still has no supported functional release.

The public checkout is mounted read-only at `/workspaces/byte-core`. Edit source files on the host; the container sees those edits, but cannot write back through this mount. Tests run as the unprivileged `byte-test` account. Generated plans, fictional deployments, profiles, and installed candidates belong in the container's temporary storage, outside the checkout.

## Start from a terminal

You need a running local Docker engine and a checkout of the public repository. Docker installation is outside this recipe. Run the commands below from the checkout root; do not substitute a private deployment repository. The initial build downloads the public Ubuntu image and packages and may take a few minutes:

```sh
docker build --platform linux/amd64 --tag byte-core-dev:ubuntu-24.04 .devcontainer
```

The build context is restricted to `.devcontainer/`; the Dockerfile does not copy the checkout or any host credentials into the image. The Ubuntu tag and package repositories can change, so this is a repeatable setup recipe, not a promise of identical image bytes across rebuilds.

Start a disposable terminal with networking disabled:

```sh
docker run --rm -it --platform linux/amd64 \
  --network none --cap-drop=ALL --security-opt=no-new-privileges:true \
  --mount "type=bind,source=$(pwd -P),target=/workspaces/byte-core,readonly" \
  --workdir /workspaces/byte-core \
  byte-core-dev:ubuntu-24.04 bash
```

You are now inside Ubuntu. Run each command separately and stop on an unexpected failure:

```sh
./bin/byte check
python3 -m unittest discover -s tests
python3 .devcontainer/smoke-test.py
```

Expect `Result: supported`, a passing unit suite, and `PASS` lines for each smoke-test stage. The smoke test builds and packages the actual candidate, runs its extracted launcher, initializes a fictional deployment, installs and verifies Core, exercises replay, applies and removes Bash/Zsh integration, removes Core, and compares the fictional deployment's file hashes. It cleans up its own test tree only after success. The unit suite separately covers local updates, refusal cases, and interruption recovery.

The smoke test can also run on a supported native host, but creates only fresh disposable test roots. It does not bypass `byte check`. Its failures retain the generated tree and print its private local location for inspection. Keep that location and all plans out of public feedback. Inspect failed state before exiting the disposable container, because `--rm` deletes its writable storage on exit.

For an interactive exercise, follow the [terminal first-session walkthrough](getting-started.md#terminal-alternative) inside the container. Use `exit` when finished. This removes that terminal container and its temporary files; the image remains available for the next run and the source checkout remains on the host.

## Open with a Dev Containers editor

In VS Code with the Dev Containers extension and local Docker available, open the public checkout and run **Dev Containers: Reopen in Container**. The repository's `.devcontainer/devcontainer.json` selects the Dockerfile, x86_64 platform, read-only source mount, and non-root account. Other clients can use the same [Dev Container specification](https://containers.dev/overview); VS Code documents [opening a folder in a container](https://code.visualstudio.com/docs/devcontainers/containers).

Creation runs only `./bin/byte check`. Run the unit suite and smoke-test commands above in the container terminal when ready. The editor may download its own server or extensions, and this editor configuration does not disable networking. Use the terminal command with `--network none` for the offline test.

The configuration adds no host home-directory or Docker-socket mounts, credentials, port publishing, or privileged mode. Editor clients may have their own credential-sharing and extension settings; those are outside this repository's configuration. The direct Docker terminal route requires no editor or GitHub/Codex sign-in.

Closing the editor stops its container; it does not promise to delete its storage. Rebuilding creates the environment again and can discard container-local test files. Keep any needed fictional failure state for inspection before rebuilding. Source editing and Git commits happen in the host checkout because the container mount is read-only.

## What this proves

Successful runs provide Ubuntu-container evidence for the CLI, candidate packaging, filesystem lifecycle, and generic shell behavior. Running the built image with `--network none` also exercises those paths without external networking. Image construction and editor installation may use the network beforehand.

Containers share the runtime host's kernel. This does not establish native Kubuntu, macOS, host login-shell, hardware, or live Codex integration behavior. On an arm64 host, the explicit `linux/amd64` platform requires working emulation; an emulated result is not native x86_64 evidence. See Docker's [container and VM explanation](https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-a-container/) and Byte's [support matrix](support-matrix.md).

Neither the unit suite nor this smoke test changes the manual-evidence ledger. The [release checklist](release-checklist.md) and independent fresh-user review still apply. Dev-container files are source-checkout tooling and are excluded from Byte's release candidate.

## Troubleshooting and cleanup

- If Docker cannot connect, confirm your local engine is running and accessible. Do not switch to an unknown remote Docker context for this test.
- If the build cannot download packages, resolve build-time connectivity before attempting the offline run.
- If an editor cannot write a source file, edit it in the host checkout; the read-only mount is intentional.
- If `byte check` reports an unexpected host or Python version, confirm you are inside the image built from this recipe. Do not bypass platform detection.
- To discard the local image after its containers are gone, use `docker image rm byte-core-dev:ubuntu-24.04`. Avoid broad prune commands; other images and containers are unrelated to this setup.
