# syntax=docker/dockerfile:1

FROM docker.io/bellsoft/alpaquita-linux-base:stream-glibc AS build
WORKDIR /src

RUN apk add --no-cache go

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 go build -o /bin/server ./src

FROM docker.io/bellsoft/alpaquita-linux-base:stream-glibc AS final

RUN apk add --no-cache ca-certificates tzdata

ARG UID=10001
RUN adduser -u ${UID} -D -s /sbin/nologin appuser
USER appuser

COPY --from=build /bin/server /bin/

EXPOSE 8081

ENTRYPOINT [ "/bin/server" ]
