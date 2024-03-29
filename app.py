import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, abort, jsonify, session, redirect, url_for
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VideoGrant, ChatGrant
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import requests
import json
import folium
import map_marker
import random
from string import ascii_uppercase
from flask_socketio import join_room, leave_room, send, SocketIO

load_dotenv()
twilio_account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
twilio_api_key_sid = os.environ.get('TWILIO_API_KEY_SID')
twilio_api_key_secret = os.environ.get('TWILIO_API_KEY_SECRET')
twilio_client = Client(twilio_api_key_sid, twilio_api_key_secret,
                       twilio_account_sid)

app = Flask(__name__)
app.config["SECRET_KEY"] = "hjhjsdahhds"
socketio = SocketIO(app)

rooms = {}

def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        
        if code not in rooms:
            break
    
    return code


def get_chatroom(name):
    for conversation in twilio_client.conversations.v1.conversations.stream():
        if conversation.friendly_name == name:
            return conversation

    # a conversation with the given name does not exist ==> create a new one
    return twilio_client.conversations.v1.conversations.create(
        friendly_name=name)
    
@app.route("/")
def start():
    return render_template("start.html")

@app.route("/home")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/blog-details")
def blog_details():
    return render_template("blog-details.html")

@app.route("/blog")
def blog():
    return render_template("blog.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/updates")
def updates():
    return render_template("updates.html")

@app.route("/records")
def records():
    return render_template("records.html")

@app.route("/patient_login")
def patient_login():
    return render_template("patient_login.html")

@app.route("/patient_signup")
def patient_signup():
    return render_template("patient_signup.html")

@app.route("/doctor_login")
def doctor_login():
    return render_template("doctor_login.html")

@app.route("/doctor_signup")
def doctor_signup():
    return render_template("doctor_signup.html")

@app.route('/generate_map', methods=['POST'])
def generate_map():
    data = request.json
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    map_marker.gen_map(latitude, longitude)

    # Your existing code to generate the map
    map_filename = "static/medical_places_map.html"
    return jsonify({"filename": map_filename})


@app.route("/code")
def code():
    return render_template("code.html")

@app.route("/book")
def book():
    return render_template("book.html")

@app.route("/manual")
def manual():
    return render_template("manual.html")

@app.route("/doc_index")
def doc_index():
    return render_template("doc_index.html")

@app.route("/doc_rec")
def doc_rec():
    return render_template("doc_rec.html")

@app.route("/doc_app")
def doc_app():
    return render_template("doc_app.html")

@app.route("/payments")
def payments():
    return render_template("payments.html")



@app.route('/room_video')
def room_video():
    return render_template('room_video.html')


@app.route('/login', methods=['POST'])
def login():
    username = request.get_json(force=True).get('username')
    if not username:
        abort(401)

    conversation = get_chatroom('My Room')
    try:
        conversation.participants.create(identity=username)
    except TwilioRestException as exc:
        # do not error if the user is already in the conversation
        if exc.status != 409:
            raise

    token = AccessToken(twilio_account_sid, twilio_api_key_sid,
                        twilio_api_key_secret, identity=username)
    token.add_grant(VideoGrant(room='My Room'))
    token.add_grant(ChatGrant(service_sid=conversation.chat_service_sid))

    return {'token': token.to_jwt(),
            'conversation_sid': conversation.sid}

@app.route("/room_chat", methods=["POST", "GET"])
def room_chat():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template("home_chat.html", error="Please enter a name.", code=code, name=name)

        if join != False and not code:
            return render_template("home_chat.html", error="Please enter a room code.", code=code, name=name)
        
        room = code
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template("home_chat.html", error="Room does not exist.", code=code, name=name)
        
        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))

    return render_template("home_chat.html")

@app.route("/room")
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))

    return render_template("room.html", code=room, messages=rooms[room]["messages"])

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

# if __name__ == '__main__':
#     app.run(host='0.0.0.0')

@app.route("/index")
def index():
    return render_template('/index.html')

@app.route("/doc_blog")
def doc_blog():
    return render_template('/doc_blog.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True)