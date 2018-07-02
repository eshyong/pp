#!/bin/bash

export SLACK_TOKEN="$(cat .slack-token.txt)"
source venv/bin/activate
flask run --host="0.0.0.0" --port="80"
