from flask import Flask, request, jsonify
import os
import uuid
import tempfile
from config import Config
from models import db, UserProfile
import cv2
import numpy as np
from insightface.app import FaceAnalysis
from PIL import Image

app = Flask(__name__)
app.config.from_object(Config)

# Initialize the database
db.init_app(app)
with app.app_context():
    db.create_all()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_IMAGE_FOLDER = os.path.join(BASE_DIR, "profile_images")

if not os.path.exists(LOCAL_IMAGE_FOLDER):
    os.makedirs(LOCAL_IMAGE_FOLDER)

# MODEL_DIR = os.path.join(BASE_DIR, "models")
MODEL_DIR = BASE_DIR

face_app = FaceAnalysis(
    name="buffalo_l",
    root=MODEL_DIR
)
face_app.prepare(ctx_id=-1)

# Function to generate unique file name
def generate_filename():
    unique_id = str(uuid.uuid4())
    new_filename = f"{unique_id}.jpg"
    return new_filename

# Compress the image and save locally
def compress_and_save_image(file, local_folder):
    img = Image.open(file)
    img = img.convert("RGB")
    local_filename = generate_filename()
    # local_filepath = os.path.join(LOCAL_IMAGE_FOLDER, local_filename)
    local_filepath = os.path.join(local_folder, local_filename)
    # extension = os.path.splitext(file.filename)[1]
    img.save(local_filepath, "JPEG", quality=80)

    return local_filepath, local_filename

# Create Profile
@app.route('/create-profile', methods=['POST'])
def create_profile():
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']

    if 'image' not in request.files:
        return jsonify({"message": "No image provided", "status": 400}), 400

    image = request.files['image']

    if image.filename == '':
        return jsonify({"message": "No file selected", "status": 400}), 400

    local_filepath, local_filename = compress_and_save_image(
        image,
        LOCAL_IMAGE_FOLDER
    )

    img = cv2.imread(local_filepath)
    faces = face_app.get(img)

    if len(faces) != 1:
        os.remove(local_filepath)
        return jsonify({
            "message": "Exactly one face required",
            "status": 400
        }), 400

    embedding = faces[0].embedding.astype(np.float32)
    embedding_bytes = embedding.tobytes()

    try:
        user_profile = UserProfile(
            name=name,
            email=email,
            phone=phone,
            image_name=local_filename,
            image_path=local_filepath,
            embedding=embedding_bytes
        )

        db.session.add(user_profile)
        db.session.commit()

    except Exception as e:
        return jsonify({
            "message": str(e),
            "status": 500
        }), 500

    return jsonify({
        "message": "Profile created successfully",
        "image_name": local_filename,
        "status": 200
    }), 200

# Check from Single Image
@app.route('/find-image', methods=['POST'])
def find_image():
    if 'image' not in request.files:
        return jsonify({"message": "No image provided", "status": 400}), 400

    image = request.files['image']

    temp_path = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    image.save(temp_path.name)

    img = cv2.imread(temp_path.name)
    faces = face_app.get(img)

    os.remove(temp_path.name)

    if len(faces) != 1:
        return jsonify({
            "message": "Exactly one face required",
            "status": 400
        }), 400

    uploaded_embedding = faces[0].embedding.astype(np.float32)

    users = UserProfile.query.all()

    best_match = None
    best_score = -1

    for user in users:
        stored_embedding = np.frombuffer(user.embedding, dtype=np.float32)

        similarity = np.dot(uploaded_embedding, stored_embedding) / (np.linalg.norm(uploaded_embedding) * np.linalg.norm(stored_embedding))

        if similarity > best_score:
            best_score = similarity
            best_match = user

    if best_score >= 0.6:
        return jsonify({
            "message": "Profile image matched",
            "matched_image": best_match.image_name,
            "status": 200
        }), 200

    return jsonify({
        "message": "Profile image not found",
        "status": 400
    }), 400

# Check from Group Image
@app.route('/find-group-image', methods=['POST'])
def find_group_image():
    if 'image' not in request.files:
        return jsonify({"message": "No image provided", "status": 400}), 400

    image = request.files['image']

    temp_path = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    image.save(temp_path.name)

    img = cv2.imread(temp_path.name)
    faces = face_app.get(img)

    os.remove(temp_path.name)

    if len(faces) == 0:
        return jsonify({
            "message": "No faces found",
            "status": 400
        }), 400

    users = UserProfile.query.all()
    matched_users = []

    for face in faces:
        uploaded_embedding = face.embedding.astype(np.float32)

        for user in users:
            stored_embedding = np.frombuffer(user.embedding, dtype=np.float32)

            similarity = np.dot(uploaded_embedding, stored_embedding) / (np.linalg.norm(uploaded_embedding) * np.linalg.norm(stored_embedding))

            if similarity >= 0.6:
                matched_users.append({
                    "name": user.name,
                    "email": user.email,
                    "image_name": user.image_name
                })

    return jsonify({
        "matches": matched_users,
        "status": 200
    }), 200

# Get Profile by Image Name
@app.route('/get-profile', methods=['POST'])
def get_profile():
    try:
        image_name = request.form.get('image_name')
        if not image_name:
            return jsonify({"message": "Image name not provided", "status": 400}), 400
        
        user_profile = UserProfile.query.filter_by(image_name=image_name).first()
        if not user_profile:
            return jsonify({"message": "User not found", "status": 400}), 400
        
        return jsonify({
            "name": user_profile.name,
            "email": user_profile.email,
            "phone": user_profile.phone,
            "status": 200
        }), 200
    except Exception as e:
        return jsonify({"message": str(e), "status": 500}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)