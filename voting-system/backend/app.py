import os
import random
import json
from flask import Flask, request, jsonify, session, send_from_directory, Response
from flask_cors import CORS
from models import db, bcrypt, User, Candidate, Vote
from face_utils import save_face_from_base64, verify_face
from telegram_bot import send_telegram_code, verify_telegram_code

# إعداد التطبيق
app = Flask(__name__, static_folder="../frontend/static", template_folder="../frontend/templates")
app.secret_key = "secure-voting-egypt-2026-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///voting.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# تأمين الجلسة (Session)
app.config.update(
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=True,
    PERMANENT_SESSION_LIFETIME=3600
)

CORS(app, supports_credentials=True)
db.init_app(app)
bcrypt.init_app(app)

# --- منع التخزين المؤقت (Cache Control) لضمان أمان المسارات ---
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# --- مسارات الصفحات (Frontend Routes) ---
@app.route("/")
@app.route("/<page>")
def serve_page(page="login"):
    if page.startswith("api"): return jsonify({"success": False}), 404
    
    # الصفحات المسموح بالوصول إليها
    valid_pages = ["login", "signup", "home", "verify", "vote", "success", "results", "admin"]
    clean_name = page.replace(".html", "")
    
    if clean_name in valid_pages:
        return send_from_directory("../frontend/templates", f"{clean_name}.html")
    return send_from_directory("../frontend/templates", "login.html")

# --- العمليات البرمجية (API Backend) ---
@app.route("/api/session", methods=["GET"])
def get_session():
    # بنشوف هل فيه مستخدم مسجل دخول فعلي (بعد الـ OTP)
    user_id = session.get("user_id")
    
    if not user_id:
        # لو مفيش، بنرد بـ logged_in: False عشان الـ JS يفهم
        return jsonify({"logged_in": False}), 200
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({"logged_in": False}), 200
        
    return jsonify({
        "logged_in": True,
        "is_admin": user.is_admin,
        "user": {
            "name": user.name,
            "national_id": user.national_id
        }
    })

@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.json
    try:
        # حفظ صورة الوجه
        face_path = save_face_from_base64(data['national_id'], data['face_image'])
        
        # إنشاء مستخدم جديد
        user = User(
            name=data['name'], 
            national_id=data['national_id'], 
            phone_number=data['phone_number'], 
            face_encoding_path=face_path
        )
        user.set_password(data['password'])
        db.session.add(user)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(national_id=data.get('national_id')).first()
    
    if user and user.check_password(data.get('password')):
        session.permanent = True
        session["pending_user_id"] = user.id
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "الرقم القومي أو كلمة المرور خطأ"}), 401

@app.route("/api/verify-face", methods=["POST"])
def verify_face_route():
    user_id = session.get("pending_user_id")
    if not user_id:
        return jsonify({"success": False, "message": "انتهت صلاحية الجلسة، سجل دخول مجدداً"}), 401

    user = User.query.get(user_id)
    face_b64 = request.json.get("face_image")

    # التحقق من تطابق الوجه
    result = verify_face(user.national_id, face_b64)

    # استثناء للأدمن أو في حالة نجاح التحقق للمستخدم العادي
    if result["verified"] or user.is_admin:
        if user.is_admin:
            session['user_id'] = user.id
            session['is_admin'] = True
            return jsonify({"success": True, "message": "مرحباً أيها المسؤول", "otp_sent": False, "is_admin": True})
            
        # إرسال الكود للمستخدم العادي عبر تليجرام
        telegram_res = send_telegram_code(user.phone_number)
        if telegram_res.get("success"):
            session["phone_code_hash"] = telegram_res["phoneCodeHash"]
            session["user_phone"] = user.phone_number
            return jsonify({"success": True, "message": "تم إرسال الكود بنجاح"})
        else:
            # لو تليجرام فيه مشكلة (زي الحظر اللي عندك)، هيرجع الخطأ هنا
            return jsonify({"success": False, "message": f"خطأ تليجرام: {telegram_res.get('error')}"}), 400

    return jsonify({"success": False, "message": "لم يتم التعرف على الوجه، حاول مرة أخرى"}), 400

@app.route("/api/verify-otp", methods=["POST"])
def verify_otp():
    data = request.json
    otp_input = data.get("otp", "").strip()
    phone_hash = session.get("phone_code_hash")
    phone_number = session.get("user_phone")

    if not all([otp_input, phone_hash, phone_number]):
        return jsonify({"success": False, "message": "بيانات التحقق مفقودة"}), 400

    # التحقق من الكود (SignIn) الرسمي عبر Telegram API
    res = verify_telegram_code(phone_number, otp_input, phone_hash)

    if res.get("success"):
        # تم التحقق بنجاح، السماح بالدخول الكامل
        session["user_id"] = session.get("pending_user_id")
        return jsonify({"success": True})
    
    return jsonify({"success": False, "message": "كود التحقق غير صحيح أو انتهت صلاحيته"}), 400
@app.route("/api/candidates", methods=["GET"])
def get_candidates():
    candidates = Candidate.query.all()
    res = []
    for c in candidates:
        res.append({
            "id": c.id,
            "name": c.name,
            "party": c.party,
            "bio": c.bio,
            "photo": c.photo_path,
            "votes": c.vote_count # بنبعت الرقم اللي بيزيد في الداتابيز فعلاً
        })
    import json
    return Response(json.dumps(res, ensure_ascii=False), mimetype='application/json')

@app.route("/api/vote", methods=["POST"])
def cast_vote():
    uid = session.get("user_id")
    if not uid: return jsonify({"success": False}), 401
    
    user = User.query.get(uid)
    if user.has_voted:
        return jsonify({"success": False, "message": "لقد قمت بالتصويت بالفعل"}), 403
    
    candidate_id = request.json.get("candidate_id")
    candidate = Candidate.query.get(candidate_id)
    
    if not candidate:
        return jsonify({"success": False, "message": "مرشح غير موجود"}), 404
        
    # تسجيل الصوت
    new_vote = Vote(user_id=user.id, candidate_id=candidate.id)
    candidate.vote_count += 1
    user.has_voted = True
    
    db.session.commit()
    return jsonify({"success": True})

@app.route("/api/results", methods=["GET"])
def get_results():
    candidates = Candidate.query.order_by(Candidate.vote_count.desc()).all()
    total_votes = sum(c.vote_count for c in candidates) or 1
    
    results_list = []
    for c in candidates:
        results_list.append({
            "name": c.name,
            "party": c.party,
            "votes": c.vote_count,
            "percentage": round((c.vote_count / total_votes) * 100, 1),
            "photo": c.photo_path
        })
    
    # التعديل هنا: بنبعت البيانات مباشرة في لستة (Array) زي ما المتصفح عاوز
    import json
    return Response(json.dumps(results_list, ensure_ascii=False), mimetype='application/json')

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})

# --- إدخال بيانات تجريبية (Seeding) ---
def seed_data():
    if not User.query.filter_by(national_id="admin").first():
        admin = User(
            name="المشرف العام", 
            national_id="admin", 
            phone_number="+201000000000", 
            is_admin=True, 
            face_encoding_path=""
        )
        admin.set_password("Admin@2026")
        db.session.add(admin)
        
    if Candidate.query.count() == 0:
        cands = [
            Candidate(name="أحمد محمد علي", party="حزب المستقبل", bio="خبير اقتصادي", photo_path="/static/images/c1.jpg"),
            Candidate(name="سارة إبراهيم حسن", party="حزب التقدم", bio="أستاذة قانون دولي", photo_path="/static/images/c2.jpg"),
            Candidate(name="محمود المصري", party="مستقل", bio="مهندس برمجيات", photo_path="/static/images/c3.jpg"),
            # المرشح الرابع اللي ضفناه
            Candidate(name="نور الدين خالد", party="حزب الإصلاح", bio="أكاديمي وباحث سياسي", photo_path="/static/images/c4.jpg")
        ]
        db.session.add_all(cands)
    db.session.commit()
    
@app.route("/api/admin/stats")
def admin_stats():
    total_users = User.query.filter_by(is_admin=False).count()
    voted_count = User.query.filter_by(has_voted=True, is_admin=False).count()
    
    # بنجمع الأصوات من عمود vote_count اللي عند كل مرشح
    total_votes = 0
    candidates = Candidate.query.all()
    for cand in candidates:
        total_votes += cand.vote_count

    data = {
        "total_users": total_users,
        "voted_count": voted_count,
        "not_voted_count": total_users - voted_count,
        "total_votes": total_votes,
        "success": True
    }
    return jsonify(data)

@app.route("/api/admin/users")
def admin_users():
    users = User.query.filter_by(is_admin=False).all()
    users_list = []
    for u in users:
        users_list.append({
            "national_id": u.national_id,
            "name": u.name,          # جرب نبعتها باسم name
            "full_name": u.name,     # ونبعتها برضه باسم full_name احتياطي عشان الـ JS يشوفها
            "has_voted": "نعم" if u.has_voted else "لا"
        })
    return jsonify(users_list)
# --- تشغيل التطبيق ---
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_data()
    # تنبيه: threaded=False ضروري جداً لعمل مكتبة Telethon باستقرار داخل Flask
    app.run(debug=True, port=5000, threaded=False)