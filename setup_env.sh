#!/bin/bash

USER_NAME=$(whoami)
USER_UID=$(id -u)
USER_GID=$(id -g)

echo "USER_NAME=${USER_NAME}
USER_UID=${USER_UID}
USER_GID=${USER_GID}" > .env