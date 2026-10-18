FROM ubuntu:24.04

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        bash ca-certificates coreutils git gzip libstdc++6 procps python3 tar zsh \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --home-dir /opt/byte-test --uid 10001 --shell /bin/bash byte-test

ENV PYTHONDONTWRITEBYTECODE=1

USER byte-test
RUN git config --global --add safe.directory /workspaces/byte-core
WORKDIR /workspaces/byte-core
CMD ["sleep", "infinity"]
