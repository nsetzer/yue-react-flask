
from flask import request, jsonify
from flask_cors import cross_origin
from sqlalchemy.exc import IntegrityError

from ..index import app, db
from ..dao.message import Message

import random

@app.route('/api/random', methods=['GET'])
def random_int():
    return jsonify({"value": random.randint(0, 100)})


"""


curl -X POST -H "Content-Type: application/json" \
     -d '{"message":"hello world"}' \
     http://localhost:4200/api/message

curl -X GET http://localhost:4200/api/message

curl -X DELETE http://localhost:4200/api/message/1

"""
@app.route('/api/message', methods=['POST'])
def create_message():
    incoming = request.get_json()

    if not incoming or "message" not in incoming:
        print("message error 1")
        return "", 400

    msg = incoming['message']
    if not isinstance(msg, str):
        print("message error 2")
        print(incoming)
        return jsonify(message="malformed request"), 400

    msg = Message(db)
    msg.add(msg)
    res = msg.get_all_messages()
    return jsonify(messages=res)

@app.route('/api/message', methods=['GET'])
def get_all_messages():
    msg = Message(db)
    res = msg.get_all_messages()
    return jsonify(messages=res)

@app.route('/api/message/<message_id>', methods=['DELETE'])
def delete_message(message_id):
    msg = Message(db)
    msg.remove(message_id)
    res = msg.get_all_messages()
    return jsonify(messages=res)
