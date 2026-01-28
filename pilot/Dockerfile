FROM golang:1.23-alpine AS builder

RUN apk add --no-cache gcc musl-dev

WORKDIR /src
COPY pilot-src/ .
RUN go mod download
RUN CGO_ENABLED=1 go build -o /pilot ./cmd/pilot

FROM alpine:3.20
RUN apk add --no-cache ca-certificates python3
COPY --from=builder /pilot /usr/local/bin/pilot
COPY --from=builder /src/orchestrator /usr/local/lib/pilot/orchestrator
COPY config.yaml /root/.pilot/config.yaml

EXPOSE 9090
CMD ["pilot", "start"]
