#!/bin/bash
set -euo pipefail

ENV_FILE="${1:-/opt/parser-site-rag/.env}"

set_var() {
    local key="$1"
    local val="$2"
    if grep -q "^${key}=" "$ENV_FILE"; then
        sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
    else
        echo "${key}=${val}" >> "$ENV_FILE"
    fi
}

set_var S3_SECRET_KEY "${S3_SECRET_KEY:-17e761b1659d43aa85edbc3bad2a7785}"
set_var CAPTCHA_API_KEY "${CAPTCHA_API_KEY:-c95532f35467ecf9c46bfddcb7e40db7}"
set_var CAPTCHA_SERVICE "2captcha"
set_var PROXY_ENABLED "${PROXY_ENABLED:-true}"
set_var PROXY_LIST "${PROXY_LIST:-}"

echo "Secrets updated in $ENV_FILE"
