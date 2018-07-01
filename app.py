from datetime import datetime
import os
import re
import signal
import sys

from flask import Flask, json, request, jsonify
from slackclient import SlackClient


if 'SLACK_TOKEN' not in os.environ:
    print('SLACK_TOKEN must be set when running this program')
    sys.exit(1)

app = Flask(__name__)

# globals, please ignore
client = SlackClient(os.environ['SLACK_TOKEN'])
incr_regexes = [r'<@(?P<user_name>[a-zA-Z0-9 ]+)> \+\+', r'<@(?P<user_name>[a-zA-Z0-9 ]+)>\+\+']
decr_regexes = [r'<@(?P<user_name>[a-zA-Z0-9 ]+)> --', r'<@(?P<user_name>[a-zA-Z0-9 ]+)>--']
last_timestamp = datetime.now()


# load scores file
scores = {}
try:
    with open('.scores.json') as scores_file:
        scores = json.load(scores_file)
except:
    pass


# handle server shutdown gracefully
def handle_sigint(signal, frame):
    print('\nsaving scores')
    with open('.scores.json', mode='w') as scores_file:
        json.dump(scores, scores_file, indent=2, sort_keys=True)
        scores_file.write('\n')
    print('exiting')
    sys.exit(0)

signal.signal(signal.SIGINT, handle_sigint)


@app.route('/events', methods=['POST'])
def respond():
    data = json.loads(request.data)
    print(json.dumps(data, indent=2, sort_keys=True))

    # to let slack verify our connection
    if 'challenge' in data:
        return data['challenge']

    # do bot stuff here
    event = data.get('event', {})
    if 'type' in event:
        if event['type'] == 'message':
            handle_message(event)
        elif event['type'] == 'app_mention':
            handle_mention(event)

    return ''

def handle_message(event):
    global last_timestamp
    global scores

    text = event.get('text')
    channel = event.get('channel')
    if text is None or channel is None:
        return

    # ignore duplicate events
    event_timestamp = datetime.fromtimestamp(float(event.get('ts')))
    if event_timestamp < last_timestamp:
        return
    last_timestamp = event_timestamp

    pluses = get_matches(text, incr_regexes)
    minuses = get_matches(text, decr_regexes)
 
    for name in pluses:
        if name not in scores:
            scores[name] = 0
        scores[name] += 1

    for name in minuses:
        if name not in scores:
            scores[name] = 0
        scores[name] -= 1

    send_message(channel, create_message(set(pluses + minuses)))


def handle_mention(event):
    global last_timestamp

    text = event.get('text')
    channel = event.get('channel')
    if text is None or channel is None:
        return

    # ignore duplicate events
    event_timestamp = datetime.fromtimestamp(float(event.get('ts')))
    if event_timestamp < last_timestamp:
        return
    last_timestamp = event_timestamp

    command = text.split()[1]
    if command == 'leaderboard':
        send_message(channel, create_message(scores.keys()))
    else:
        send_message(channel, "Sorry, pp doesn't know that command")


def get_matches(text, regexes):
    users = []
    for regex in regexes:
        matches = re.findall(regex, text)
        for match in matches:
            real_name = get_real_name_for_user(match)
            if real_name is not None:
                users.append(real_name)
    return users


def get_real_name_for_user(user_name):
    try:
        response = client.api_call('users.info', user=user_name)
        if not response.get('ok'):
            return None
        return response['user']['profile']['real_name']
    except Exception as e:
        print(e)
    return None


def create_message(names):
    texts = ["{}'s score is {}".format(name, scores[name]) for name in names]
    return '\n'.join(texts)


def send_message(channel, text):
    global client

    try:
        client.api_call('chat.postMessage', channel=channel, text=text)
    except Exception as e:
        print(e)


