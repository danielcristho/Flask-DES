from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_socketio import join_room, leave_room, send, SocketIO, emit
from string import ascii_uppercase
from des import Decrypt, Encrypt
from dotenv import load_dotenv
import random
import threading
import os

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
socketio = SocketIO(app)

rooms = {}

def generate_unique_code(length):
    """
    its required for unique codes for create a room
    """
    while True:
        code = ""
        for i in range(length):
            code += random.choice(ascii_uppercase)

        if code not in rooms: # For unique room codes.
            break

    return code

@app.route("/", methods=["POST", "GET"])
def index():
    session.clear() # Session must be clear when user get request to '/' endpoint.
    if request.method == "POST":
        name = request.form.get("name") # users name
        code = request.form.get("code") # room code
        join = request.form.get("join", False) # join button => if not submit this variable will be False
        create = request.form.get("create", False) # create button => if not submit this variable will be False

        if not name:
            flash("Please choose a username before continuing.")
            return render_template("index.html", code=code, name=name)

        if join != False and not code: # If user submit join button but field is empty.
            flash("Please enter a room code.")
            return render_template("index.html", code=code, name=name)

        room = code
        if create != False: # If user sucmit create button
            room = generate_unique_code(4) # Generate unique code
            rooms[room] = {"members": 0, "messages": []} # create room in session
        elif code not in rooms:
            flash("Room doesn't exist.")
            return render_template("index.html", code=code, name=name)

        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))

    return render_template("index.html")

@app.route("/room") # room endpoint
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms: # room control
        return redirect(url_for("index"))

    return render_template("room.html", code=room, messages=rooms[room]["messages"]) # Send messages of the room we have in the session to room.html

@app.route("/encrypt", methods=["POST"])
def encrypt():
    if request.method == "POST":
        main_key = request.form.get("key")
        plain_text = request.form.get("message")
        cipher_text = Encrypt(main_key, plain_text, plain_text)
        return jsonify({"result": cipher_text})

@app.route("/decrypt", methods=["POST"])
def decrypt():
    if request.method == "POST":
        message = request.form.get("message")
        key = request.form.get("key")
        decrypted = Decrypt(message, key)
        return decrypted

@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return

    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")

@socketio.on("leave_room")
def leave_room_event():
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return

    leave_room(room)
    send({"name": name, "message": "has left the room"}, to=room)
    rooms[room]["members"] -= 1
    print(f"{name} left room {room}")

@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return

    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]

    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")

@app.route("/leave") # leave endpoint
def leave():
    room = session.get("room")
    name = session.get("name")
    if room is None or name is None or room not in rooms:
        return redirect(url_for("index"))

    leave_room(room)
    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")

    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    socketio.run(app, debug=True)