from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
load_dotenv()
app = Flask(__name__)
app.secret_key = "super-secret-key-change-this"

# ✅ SQLite locally, Supabase on Render
# ✅ FORCE SUPABASE ONLY (NO SQLITE FALLBACK)
DATABASE_URL = os.environ.get("DATABASE_URL")


if not DATABASE_URL:
    raise RuntimeError("❌ DATABASE_URL environment variable is NOT set!")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

print("✅ DATABASE IN USE:", DATABASE_URL)


db = SQLAlchemy(app)

# =======================
# MODELS
# =======================

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)


class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    category = db.Column(db.String(50))
    note = db.Column(db.Text)   # ✅ NEW
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship("User", backref=db.backref("expenses", lazy=True))


# =======================
# AUTH HELPERS
# =======================

def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


def login_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash("Please login first", "warning")
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper


# =======================
# ROUTES
# =======================

@app.route("/")
def index():
    return redirect(url_for("login"))


# -------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        existing = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing:
            flash("User already exists", "danger")
            return redirect(url_for("register"))

        hashed = generate_password_hash(password)

        user = User(
            username=username,
            email=email,
            password_hash=hashed
        )

        db.session.add(user)
        db.session.commit()

        flash("Registration successful!", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# -------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash("Invalid login", "danger")
            return redirect(url_for("login"))

        session["user_id"] = user.id
        return redirect(url_for("dashboard"))

    return render_template("login.html")


# -------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# -------- DASHBOARD ----------
@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    expenses = Expense.query.filter_by(user_id=user.id).all()
    total = sum(float(e.amount) for e in expenses)

    return render_template(
        "dashboard.html",
        user=user,
        expenses=expenses,
        total=total
    )



# -------- ADD EXPENSE ----------
@app.route("/add", methods=["GET", "POST"])
@login_required
def add_expense():
    if request.method == "POST":
        title = request.form["title"]
        amount = request.form["amount"]
        category = request.form["category"]
        note = request.form["note"]

        exp = Expense(
            user_id=current_user().id,
            title=title,
            amount=amount,
            category=category,
            note=note
        )

        db.session.add(exp)
        db.session.commit()
        return redirect(url_for("dashboard"))

    return render_template("add_expense.html")


# -------- DELETE EXPENSE ----------
@app.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete_expense(id):
    exp = Expense.query.get(id)
    db.session.delete(exp)
    db.session.commit()
    return redirect(url_for("dashboard"))


# =======================
# RUN
# =======================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()   # ✅ Auto create DB
    app.run(debug=True)
