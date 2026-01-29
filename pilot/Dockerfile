FROM golang:1.24-alpine AS builder

RUN apk add --no-cache gcc musl-dev

WORKDIR /src
COPY pilot-src/ .
RUN go mod download
RUN CGO_ENABLED=1 go build -o /pilot ./cmd/pilot

FROM alpine:3.20

# Install system dependencies
RUN apk add --no-cache \
    ca-certificates \
    python3 \
    nodejs \
    npm \
    git \
    github-cli \
    bash \
    openssh-client \
    shadow \
    su-exec

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Create non-root user for Claude Code execution
RUN addgroup -g 1000 pilot && \
    adduser -D -u 1000 -G pilot pilot

# Copy pilot binary and config
COPY --from=builder /pilot /usr/local/bin/pilot
COPY --from=builder /src/orchestrator /usr/local/lib/pilot/orchestrator

# Setup directories with correct permissions
RUN mkdir -p /home/pilot/.pilot /home/pilot/.claude && \
    chown -R pilot:pilot /home/pilot

COPY config.yaml /home/pilot/.pilot/config.yaml
RUN chown pilot:pilot /home/pilot/.pilot/config.yaml

# Git config for pilot user
RUN su-exec pilot git config --global user.name "Pilot AI" && \
    su-exec pilot git config --global user.email "pilot@localhost" && \
    su-exec pilot git config --global --add safe.directory /workspace

EXPOSE 9090

# Run as non-root user
USER pilot
WORKDIR /home/pilot
CMD ["pilot", "start"]
