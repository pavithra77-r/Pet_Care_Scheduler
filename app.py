from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__, template_folder="templates")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///pawcare.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
CORS(app)


# -----------------------------
# DATABASE MODELS
# -----------------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")
    specialization = db.Column(db.String(120), nullable=True)

    pets = db.relationship("Pet", backref="owner", lazy=True, cascade="all, delete")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "specialization": self.specialization or ""
        }


class Pet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    name = db.Column(db.String(120), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    breed = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer, nullable=False)

    feeding_schedule = db.Column(db.String(255), nullable=True)
    medicine_reminder = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.String(50), nullable=False)

    vet_visits = db.relationship("VetVisit", backref="pet", lazy=True, cascade="all, delete")

    def to_dict(self):
        return {
            "id": self.id,
            "ownerId": self.owner_id,
            "name": self.name,
            "type": self.type,
            "breed": self.breed,
            "age": self.age,
            "feedingSchedule": self.feeding_schedule or "",
            "medicineReminder": self.medicine_reminder or "",
            "createdAt": self.created_at
        }


class VetVisit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pet_id = db.Column(db.Integer, db.ForeignKey("pet.id"), nullable=False)

    logged_by = db.Column(db.Integer, nullable=False)
    logged_by_name = db.Column(db.String(120), nullable=False)

    date = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    diagnosis = db.Column(db.String(255), nullable=True)
    treatment = db.Column(db.String(255), nullable=True)
    remarks = db.Column(db.Text, nullable=True)
    doctor = db.Column(db.String(120), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "petId": self.pet_id,
            "loggedBy": self.logged_by,
            "loggedByName": self.logged_by_name,
            "date": self.date,
            "reason": self.reason,
            "diagnosis": self.diagnosis or "",
            "treatment": self.treatment or "",
            "remarks": self.remarks or "",
            "doctor": self.doctor or ""
        }


# -----------------------------
# HELPER FUNCTION
# -----------------------------

def get_dashboard_data():
    users = [u.to_dict() for u in User.query.all()]
    pets = [p.to_dict() for p in Pet.query.all()]
    vet_visits = [v.to_dict() for v in VetVisit.query.all()]
    return {
        "users": users,
        "pets": pets,
        "vetVisits": vet_visits
    }


# -----------------------------
# FRONTEND ROUTE
# -----------------------------

@app.route("/")
def home():
    return render_template("index.html")


# -----------------------------
# AUTH ROUTES
# -----------------------------

@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = (data.get("role") or "user").strip()
    specialization = (data.get("specialization") or "").strip()

    if not name or not email or not password:
        return jsonify({"error": "Name, email and password are required"}), 400

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"error": "Email already registered"}), 409

    new_user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password),
        role=role,
        specialization=specialization
    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify({
        "message": "Registration successful",
        "user": new_user.to_dict()
    }), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid email or password"}), 401

    return jsonify({
        "message": "Login successful",
        "user": user.to_dict()
    })


# -----------------------------
# DASHBOARD DATA
# -----------------------------

@app.route("/api/dashboard-data", methods=["GET"])
def dashboard_data():
    return jsonify(get_dashboard_data())


# -----------------------------
# PET ROUTES
# -----------------------------

@app.route("/api/pets", methods=["POST"])
def add_pet():
    data = request.get_json()

    try:
        owner_id = int(data.get("ownerId"))
        age = int(data.get("age"))
    except (TypeError, ValueError):
        return jsonify({"error": "ownerId and age must be valid numbers"}), 400

    name = (data.get("name") or "").strip()
    pet_type = (data.get("type") or "").strip()
    breed = (data.get("breed") or "").strip()
    feeding_schedule = (data.get("feedingSchedule") or "").strip()
    medicine_reminder = (data.get("medicineReminder") or "").strip()

    if not name or not pet_type or not breed:
        return jsonify({"error": "Name, type and breed are required"}), 400

    owner = User.query.get(owner_id)
    if not owner:
        return jsonify({"error": "Owner not found"}), 404

    pet = Pet(
        owner_id=owner_id,
        name=name,
        type=pet_type,
        breed=breed,
        age=age,
        feeding_schedule=feeding_schedule,
        medicine_reminder=medicine_reminder,
        created_at=datetime.utcnow().isoformat()
    )

    db.session.add(pet)
    db.session.commit()

    return jsonify({
        "message": "Pet added successfully",
        "pet": pet.to_dict()
    }), 201


@app.route("/api/pets/<int:pet_id>", methods=["DELETE"])
def delete_pet(pet_id):
    pet = Pet.query.get(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404

    db.session.delete(pet)
    db.session.commit()

    return jsonify({"message": "Pet deleted successfully"})


# -----------------------------
# VET VISIT ROUTES
# -----------------------------

@app.route("/api/vet-visits", methods=["POST"])
def add_vet_visit():
    data = request.get_json()

    try:
        pet_id = int(data.get("petId"))
        logged_by = int(data.get("loggedBy"))
    except (TypeError, ValueError):
        return jsonify({"error": "petId and loggedBy must be valid numbers"}), 400

    reason = (data.get("reason") or "").strip()
    if not reason:
        return jsonify({"error": "Reason for visit is required"}), 400

    pet = Pet.query.get(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404

    visit = VetVisit(
        pet_id=pet_id,
        logged_by=logged_by,
        logged_by_name=(data.get("loggedByName") or "").strip(),
        date=(data.get("date") or datetime.utcnow().strftime("%Y-%m-%d")).strip(),
        reason=reason,
        diagnosis=(data.get("diagnosis") or "").strip(),
        treatment=(data.get("treatment") or "").strip(),
        remarks=(data.get("remarks") or "").strip(),
        doctor=(data.get("doctor") or "").strip()
    )

    db.session.add(visit)
    db.session.commit()

    return jsonify({
        "message": "Vet visit added successfully",
        "vetVisit": visit.to_dict()
    }), 201


@app.route("/api/vet-visits/<int:visit_id>", methods=["DELETE"])
def delete_vet_visit(visit_id):
    visit = VetVisit.query.get(visit_id)
    if not visit:
        return jsonify({"error": "Vet visit not found"}), 404

    db.session.delete(visit)
    db.session.commit()

    return jsonify({"message": "Vet visit deleted successfully"})


# -----------------------------
# TEST ROUTE
# -----------------------------

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


# -----------------------------
# MAIN
# -----------------------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)