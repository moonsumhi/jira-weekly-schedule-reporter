FROM golang:1.23-alpine AS builder

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
    openssh-client

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Copy pilot binary and config
COPY --from=builder /pilot /usr/local/bin/pilot
COPY --from=builder /src/orchestrator /usr/local/lib/pilot/orchestrator
COPY config.yaml /root/.pilot/config.yaml

# Git config (will be overridden by environment if needed)
RUN git config --global user.name "Pilot AI" && \
    git config --global user.email "pilot@localhost"

EXPOSE 9090
CMD ["pilot", "start"]
