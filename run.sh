#!/bin/bash

export SLACK_TOKEN="$(cat .slack-token.txt)"
source venv/bin/activate
flask run
