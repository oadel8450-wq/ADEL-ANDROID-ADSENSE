# ADEL ANDROID ADSENSE
# Flask | PythonAnywhere | Python 3.10
# Developer: Adel Omar Abdel Aziz
# AL ADL GROUP

import os, sqlite3, secrets, math
from functools import wraps
from contextlib import contextmanager
from urllib.parse import quote
from flask import Flask, request, redirect, url_for, session, render_template_string, send_from_directory, abort
from werkzeug.utils import secure_filename
from markupsafe import escape, Markup

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ADEL-ANDROID-SECRET-2026")
app.config.update(
    MAX_CONTENT_LENGTH=50*1024*1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=True
)

BASE = os.path.dirname(os.path.abspath(__file__))
UPLOAD = os.path.join(BASE, "apps")
IMAGES = os.path.join(BASE, "images")
RECEIPTS = os.path.join(BASE, "receipts")
DB = os.path.join(BASE, "apps.db")

for folder in (UPLOAD, IMAGES, RECEIPTS):
    os.makedirs(folder, exist_ok=True)

SITE_NAME = "ADEL ANDROID ADSENSE"
WALLET = "01067119916"
ADMIN_PASSWORD = "23"


@contextmanager
def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def initialize():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS applications(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, description TEXT DEFAULT '',
        filename TEXT NOT NULL, image TEXT DEFAULT '',
        price REAL DEFAULT 10, downloads INTEGER DEFAULT 0)""")

        con.execute("""CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        app_id INTEGER, customer TEXT, phone TEXT,
        transaction_id TEXT, receipt TEXT,
        status TEXT DEFAULT 'pending', token TEXT,
        created TEXT DEFAULT CURRENT_TIMESTAMP)""")

        con.execute("""CREATE TABLE IF NOT EXISTS settings(
        key TEXT PRIMARY KEY, value TEXT DEFAULT '')""")


initialize()


def setting(key, default=""):
    with db() as con:
        row = con.execute(
            "SELECT value FROM settings WHERE key=?", (key,)
        ).fetchone()
    return row["value"] if row else default


def set_setting(key, value):
    with db() as con:
        con.execute(
            "INSERT OR REPLACE INTO settings VALUES(?,?)",
            (key, value)
        )


def csrf_token():
    session.setdefault("csrf", secrets.token_hex(32))
    return session["csrf"]


@app.before_request
def protect_forms():
    if request.method == "POST":
        if request.form.get("csrf_token") != session.get("csrf"):
            abort(400)


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def safe(value):
    return str(escape(value or ""))


def money(value):
    return f"{float(value):g}"


def save_upload(file, folder, extensions):
    if not file or not file.filename:
        return None

    ext = os.path.splitext(
        secure_filename(file.filename)
    )[1].lower()

    if ext not in extensions:
        return None

    name = secrets.token_hex(16) + ext
    file.save(os.path.join(folder, name))
    return name


STYLE = """
<style>
*{box-sizing:border-box}
body{margin:0;font-family:Arial,Tahoma,sans-serif;
direction:rtl;background:#f1f4fa;color:#172b4d}
header{background:linear-gradient(135deg,#071a35,#153d70,#087e65);
color:white;text-align:center;padding:38px 15px}
header h1{font-size:30px;margin:5px}
header p{color:#d9e6f5}
nav{background:#102b50;padding:16px 8px;text-align:center;
position:sticky;top:0;z-index:10}
nav a{color:white;text-decoration:none;margin:8px;
font-weight:bold;font-size:14px}
.container{max-width:1100px;margin:30px auto;padding:15px;
min-height:350px}
.hero{background:linear-gradient(120deg,#102b50,#087e65);
color:white;border-radius:20px;padding:30px 20px;
text-align:center;margin-bottom:25px}
.card{background:white;padding:22px;margin:16px 0;
border-radius:15px;box-shadow:0 5px 20px #dce2ed}
.grid,.stats{display:grid;
grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px}
.product{background:white;border-radius:16px;overflow:hidden;
box-shadow:0 5px 18px #dce2ed}
.product img{width:100%;height:180px;object-fit:contain;
background:#fff}
.product-info{padding:18px}
.price{color:#07835b;font-size:21px;font-weight:bold}
button,.btn{display:inline-block;border:0;border-radius:8px;
padding:12px 17px;background:#07835b;color:white;
text-decoration:none;cursor:pointer;font-weight:bold;margin:5px}
button:hover,.btn:hover{background:#075d45}
.red{background:#c0392b}
input,textarea,select{display:block;width:100%;padding:13px;
margin:10px 0;border:1px solid #d4dbe6;border-radius:8px;
font-size:15px}
.stat{background:linear-gradient(135deg,#102b50,#087e65);
color:white;padding:22px;border-radius:13px;text-align:center}
footer{background:#071a35;color:white;text-align:center;
padding:28px 10px;margin-top:50px;line-height:2}
@media(max-width:600px){
header h1{font-size:23px}
nav a{display:inline-block;margin:6px}
}
</style>
"""


def share_buttons(link):
    encoded = quote(link, safe="")
    return (
        f'<a class="btn" target="_blank" rel="noopener" '
        f'href="https://wa.me/?text={encoded}">مشاركة WhatsApp</a>'
        f'<a class="btn" target="_blank" rel="noopener" '
        f'href="https://www.facebook.com/sharer/sharer.php?u={encoded}">'
        f'مشاركة Facebook</a>'
    )


def page(body, title=SITE_NAME):
    pub, slot = setting("adsense_id"), setting("adsense_slot")
    valid = pub.startswith("ca-pub-") and pub[7:].isdigit()

    script = (
        f'<script async src="https://pagead2.googlesyndication.com/'
        f'pagead/js/adsbygoogle.js?client={pub}" '
        f'crossorigin="anonymous"></script>' if valid else ""
    )

    ads = (
        f'<ins class="adsbygoogle" style="display:block" '
        f'data-ad-client="{pub}" data-ad-slot="{slot}" '
        f'data-ad-format="auto" data-full-width-responsive="true"></ins>'
        f'<script>(adsbygoogle=window.adsbygoogle||[]).push({{}});</script>'
        if valid and slot.isdigit() else ""
    )

    return render_template_string("""
    <!doctype html>
    <html lang="ar">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <meta name="description" content="ADEL ANDROID ADSENSE">
    <title>{{title}}</title>
    {{style|safe}}{{script|safe}}
    </head>
    <body>
    <header>
    <h1>ADEL ANDROID ADSENSE</h1>
    <p>Your Apps. Your Digital World.</p>
    <span>منصة عادل لتطبيقات Android</span>
    </header>
    <nav>
    <a href="/">الرئيسية</a>
    <a href="/about">من نحن</a>
    <a href="/contact">اتصل بنا</a>
    <a href="/privacy">الخصوصية</a>
    <a href="/admin/login">الإدارة</a>
    </nav>
    <main class="container">
    <div>{{ads|safe}}</div>
    {{body|safe}}
    </main>
    <footer>
    ADEL ANDROID ADSENSE<br>
    Developed by Adel Omar Abdel Aziz<br>
    AL ADL GROUP<br>
    Your Digital World
    </footer>
    </body>
    </html>
    """, title=title, body=Markup(body),
    style=Markup(STYLE), ads=Markup(ads), script=Markup(script))


# HOME

@app.route("/")
def home():
    with db() as con:
        apps = con.execute(
            "SELECT * FROM applications ORDER BY id DESC"
        ).fetchall()

    body = """
    <section class="hero">
    <h2>مرحباً بك في ADEL ANDROID ADSENSE</h2>
    <p>اكتشف أفضل تطبيقات Android في مكان واحد</p>
    <p>Your Apps. Your Digital World.</p>
    </section>
    <div class="card">
    <h2>تطبيقاتنا</h2>
    <p>اختر التطبيق المناسب لك.</p>
    </div>
    <div class="grid">
    """

    if not apps:
        body += '<div class="card">لا توجد تطبيقات حالياً</div>'

    for x in apps:
        price = "مجاني" if x["price"] == 0 else money(x["price"])+" جنيه"

        img = (
            f'<img src="{url_for("application_image", filename=x["image"])}" '
            f'alt="{safe(x["name"])}">'
            if x["image"] else
            '<div style="height:180px;text-align:center;padding:70px">'
            'لا توجد صورة</div>'
        )

        link = url_for("buy", app_id=x["id"], _external=True)

        body += f"""
        <div class="product">
        {img}
        <div class="product-info">
        <h3>{safe(x["name"])}</h3>
        <p>{safe(x["description"])}</p>
        <p class="price">{price}</p>
        <p>التحميلات: {x["downloads"]}</p>
        <a class="btn" href="/buy/{x["id"]}">عرض التطبيق</a>
        {share_buttons(link)}
        </div>
        </div>
        """

    return page(body+"</div>")


# APPLICATION IMAGES

@app.route("/image/<filename>")
def application_image(filename):
    return send_from_directory(IMAGES, filename)


# APPLICATION DETAILS

@app.route("/buy/<int:app_id>")
def buy(app_id):
    with db() as con:
        item = con.execute(
            "SELECT * FROM applications WHERE id=?", (app_id,)
        ).fetchone()

    if not item:
        abort(404)

    if item["price"] == 0:
        return redirect(url_for("download_free", app_id=app_id))

    img = (
        f'<img style="width:100%;max-height:250px;'
        f'object-fit:contain" src="/image/{safe(item["image"])}">'
        if item["image"] else ""
    )

    body = f"""
    <div class="card">
    {img}
    <h2>{safe(item["name"])}</h2>
    <p>{safe(item["description"])}</p>
    <h2 class="price">السعر: {money(item["price"])} جنيه</h2>

    <div class="hero">
    <h3>الدفع عبر Vodafone Cash</h3>
    <h2 dir="ltr">{WALLET}</h2>
    <p>حوّل قيمة التطبيق ثم أرسل الإيصال.</p>
    </div>

    <form method="POST" action="/order/{app_id}"
    enctype="multipart/form-data">
    <input type="hidden" name="csrf_token"
    value="{csrf_token()}">

    <input name="customer" placeholder="اسم العميل"
    required maxlength="100">

    <input name="phone" placeholder="رقم هاتف العميل"
    required maxlength="30">

    <input name="transaction_id"
    placeholder="رقم عملية التحويل"
    required maxlength="100">

    <label>صورة إيصال التحويل</label>
    <input type="file" name="receipt"
    accept=".jpg,.jpeg,.png,.webp" required>

    <button>إرسال طلب الشراء</button>
    </form>
    {share_buttons(request.url)}
    </div>
    """

    return page(body)


# CUSTOMER ORDER

@app.route("/order/<int:app_id>", methods=["POST"])
def order(app_id):
    with db() as con:
        item = con.execute(
            "SELECT * FROM applications WHERE id=?", (app_id,)
        ).fetchone()

        if not item or item["price"] <= 0:
            abort(404)

        customer = request.form.get("customer", "").strip()
        phone = request.form.get("phone", "").strip()
        transaction = request.form.get("transaction_id", "").strip()

        receipt = save_upload(
            request.files.get("receipt"), RECEIPTS,
            {".jpg", ".jpeg", ".png", ".webp"}
        )

        if not customer or not phone or not transaction or not receipt:
            return "يرجى استكمال البيانات واختيار صورة إيصال صحيحة", 400

        con.execute("""
        INSERT INTO orders(app_id,customer,phone,transaction_id,receipt)
        VALUES(?,?,?,?,?)
        """, (app_id, customer[:100], phone[:30],
              transaction[:100], receipt))

    return page("""
    <div class="card">
    <h2>تم إرسال طلب الشراء بنجاح</h2>
    <p>طلبك قيد مراجعة الإدارة.</p>
    <a class="btn" href="/">الرئيسية</a>
    </div>
    """)


# DIRECT APK DOWNLOAD

def apk_download(filename):
    if not filename or not filename.lower().endswith(".apk"):
        abort(404)

    path = os.path.join(UPLOAD, filename)

    if not os.path.isfile(path):
        abort(404)

    return send_from_directory(
        UPLOAD,
        filename,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.android.package-archive",
        max_age=0
    )


# FREE DOWNLOAD

@app.route("/free/<int:app_id>")
def download_free(app_id):
    with db() as con:
        item = con.execute(
            "SELECT * FROM applications WHERE id=? AND price=0",
            (app_id,)
        ).fetchone()

        if not item:
            abort(404)

        con.execute(
            "UPDATE applications SET downloads=downloads+1 WHERE id=?",
            (app_id,)
        )

        filename = item["filename"]

    return apk_download(filename)


# PAID DOWNLOAD

@app.route("/paid/<token>")
def paid_download(token):
    with db() as con:
        order = con.execute(
            "SELECT * FROM orders WHERE token=? AND status='paid'",
            (token,)
        ).fetchone()

        if not order:
            abort(403)

        item = con.execute(
            "SELECT * FROM applications WHERE id=?",
            (order["app_id"],)
        ).fetchone()

        if not item:
            abort(404)

        con.execute(
            "UPDATE applications SET downloads=downloads+1 WHERE id=?",
            (item["id"],)
        )

        filename = item["filename"]

    return apk_download(filename)


# ADMIN LOGIN

@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session.clear()
            session["admin"] = True
            session["csrf"] = secrets.token_hex(32)
            return redirect("/admin")

        return page(
            '<div class="card"><h2>كلمة المرور غير صحيحة</h2></div>'
        )

    return page(f"""
    <div class="card">
    <h2>دخول المدير</h2>
    <form method="POST">
    <input type="hidden" name="csrf_token" value="{csrf_token()}">
    <input type="password" name="password"
    placeholder="كلمة مرور الإدارة" required>
    <button>تسجيل الدخول</button>
    </form>
    </div>
    """)


# ADMIN DASHBOARD

@app.route("/admin")
@admin_required
def admin():
    with db() as con:
        apps = con.execute(
            "SELECT * FROM applications ORDER BY id DESC"
        ).fetchall()

        orders = con.execute("""
        SELECT orders.*,applications.name
        FROM orders LEFT JOIN applications
        ON orders.app_id=applications.id
        ORDER BY orders.id DESC
        """).fetchall()

    pending = sum(o["status"] == "pending" for o in orders)

    body = f"""
    <div class="hero">
    <h2>لوحة تحكم ADEL ANDROID ADSENSE</h2>
    <p>مرحباً بك في لوحة الإدارة</p>
    </div>

    <div class="stats">
    <div class="stat"><h2>{len(apps)}</h2>التطبيقات</div>
    <div class="stat"><h2>{sum(x["downloads"] for x in apps)}</h2>التحميلات</div>
    <div class="stat"><h2>{pending}</h2>طلبات الانتظار</div>
    </div>

    <div class="card">
    <h2>إضافة تطبيق جديد</h2>
    <form method="POST" action="/admin/add"
    enctype="multipart/form-data">

    <input type="hidden" name="csrf_token"
    value="{csrf_token()}">

    <input name="name" placeholder="اسم التطبيق" required>

    <textarea name="description"
    placeholder="وصف التطبيق"></textarea>

    <label>السعر بالجنيه (0 = مجاني)</label>
    <input type="number" step="0.01"
    name="price" value="10" min="0" required>

    <label>ملف التطبيق APK</label>
    <input type="file" name="apk"
    accept=".apk" required>

    <label>صورة غلاف التطبيق (اختيارية)</label>
    <input type="file" name="image"
    accept=".jpg,.jpeg,.png,.webp">

    <button>إضافة التطبيق</button>
    </form>
    </div>
    """

    body += f"""
    <div class="card">
    <h2>إعدادات Google AdSense</h2>
    <form method="POST" action="/admin/settings">
    <input type="hidden" name="csrf_token"
    value="{csrf_token()}">

    <label>Publisher ID</label>
    <input name="adsense_id"
    value="{safe(setting('adsense_id'))}"
    placeholder="ca-pub-xxxxxxxx">

    <label>Ad Slot ID</label>
    <input name="adsense_slot"
    value="{safe(setting('adsense_slot'))}"
    placeholder="رقم الوحدة الإعلانية">

    <button>حفظ إعدادات الإعلانات</button>
    </form>
    <p>ملف الإعلانات: /ads.txt</p>
    </div>

    <div class="card">
    <h2>إدارة التطبيقات</h2>
    """

    for x in apps:
        img = (
            f'<img style="width:100px;height:80px;object-fit:contain" '
            f'src="/image/{safe(x["image"])}">'
            if x["image"] else ""
        )

        body += f"""
        <hr>
        {img}
        <h3>{safe(x["name"])}</h3>
        <p>السعر: {money(x["price"])} جنيه |
        التحميلات: {x["downloads"]}</p>

        <a class="btn" href="/admin/edit/{x["id"]}">
        تعديل التطبيق والصورة</a>

        <form method="POST" action="/admin/delete/{x["id"]}">
        <input type="hidden" name="csrf_token"
        value="{csrf_token()}">
        <button class="red">حذف التطبيق</button>
        </form>
        """

    body += '</div><div class="card"><h2>طلبات الشراء</h2>'

    for o in orders:
        body += f"""
        <hr>
        <h3>طلب رقم {o["id"]}</h3>
        <p>التطبيق: {safe(o["name"])} |
        العميل: {safe(o["customer"])} |
        الهاتف: {safe(o["phone"])}</p>

        <p>رقم التحويل: {safe(o["transaction_id"])} |
        الحالة: {safe(o["status"])}</p>

        <a class="btn" href="/admin/receipt/{o["id"]}">
        عرض الإيصال</a>

        <form method="POST" action="/admin/confirm/{o["id"]}">
        <input type="hidden" name="csrf_token"
        value="{csrf_token()}">
        <button>تأكيد الدفع</button>
        </form>

        <form method="POST" action="/admin/reject/{o["id"]}">
        <input type="hidden" name="csrf_token"
        value="{csrf_token()}">
        <button class="red">رفض الطلب</button>
        </form>
        """

    body += """
    </div>
    <div class="card">
    <a class="btn red" href="/admin/logout">تسجيل الخروج</a>
    </div>
    """

    return page(body)


# ADSENSE SETTINGS

@app.route("/admin/settings", methods=["POST"])
@admin_required
def admin_settings():
    pub = request.form.get("adsense_id", "").strip()
    slot = request.form.get("adsense_slot", "").strip()

    if pub and (not pub.startswith("ca-pub-") or not pub[7:].isdigit()):
        return "Publisher ID غير صحيح", 400

    if slot and not slot.isdigit():
        return "Ad Slot ID غير صحيح", 400

    set_setting("adsense_id", pub)
    set_setting("adsense_slot", slot)

    return redirect("/admin")


# ADD APPLICATION

@app.route("/admin/add", methods=["POST"])
@admin_required
def add():
    name = request.form.get("name", "").strip()
    desc = request.form.get("description", "").strip()

    try:
        price = float(request.form.get("price", 10))
        if not math.isfinite(price):
            raise ValueError()
    except ValueError:
        return "السعر غير صحيح", 400

    if not name or price < 0:
        return "بيانات غير صحيحة", 400

    apk = save_upload(
        request.files.get("apk"), UPLOAD, {".apk"}
    )

    image = save_upload(
        request.files.get("image"), IMAGES,
        {".jpg", ".jpeg", ".png", ".webp"}
    )

    if not apk:
        return "يرجى اختيار ملف APK صحيح", 400

    with db() as con:
        con.execute("""
        INSERT INTO applications
        (name,description,filename,image,price)
        VALUES(?,?,?,?,?)
        """, (name, desc, apk, image or "", price))

    return redirect("/admin")


# EDIT APPLICATION AND COVER IMAGE

@app.route("/admin/edit/<int:app_id>", methods=["GET", "POST"])
@admin_required
def edit(app_id):
    with db() as con:
        item = con.execute(
            "SELECT * FROM applications WHERE id=?",
            (app_id,)
        ).fetchone()

        if not item:
            abort(404)

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            desc = request.form.get("description", "").strip()

            try:
                price = float(request.form.get("price", 10))
                if not math.isfinite(price):
                    raise ValueError()
            except ValueError:
                return "السعر غير صحيح", 400

            if not name or price < 0:
                return "بيانات غير صحيحة", 400

            apk = save_upload(
                request.files.get("apk"), UPLOAD, {".apk"}
            )

            image = save_upload(
                request.files.get("image"), IMAGES,
                {".jpg", ".jpeg", ".png", ".webp"}
            )

            con.execute("""
            UPDATE applications
            SET name=?,description=?,price=?,filename=?,image=?
            WHERE id=?
            """, (
                name, desc, price,
                apk or item["filename"],
                image or item["image"],
                app_id
            ))

            return redirect("/admin")

    preview = (
        f'<img style="width:100%;max-height:220px;'
        f'object-fit:contain" src="/image/{safe(item["image"])}">'
        if item["image"] else ""
    )

    body = f"""
    <div class="card">
    <h2>تعديل التطبيق وصورة الغلاف</h2>
    {preview}

    <form method="POST" enctype="multipart/form-data">
    <input type="hidden" name="csrf_token"
    value="{csrf_token()}">

    <label>اسم التطبيق</label>
    <input name="name" value="{safe(item["name"])}" required>

    <label>الوصف</label>
    <textarea name="description">{safe(item["description"])}</textarea>

    <label>السعر</label>
    <input type="number" step="0.01"
    name="price" value="{item["price"]}" min="0">

    <label>تغيير ملف APK (اختياري)</label>
    <input type="file" name="apk" accept=".apk">

    <label>تغيير صورة الغلاف (اختياري)</label>
    <input type="file" name="image"
    accept=".jpg,.jpeg,.png,.webp">

    <button>حفظ التعديلات</button>
    </form>
    </div>
    """

    return page(body)


# DELETE APPLICATION

@app.route("/admin/delete/<int:app_id>", methods=["POST"])
@admin_required
def delete(app_id):
    with db() as con:
        con.execute(
            "DELETE FROM applications WHERE id=?", (app_id,)
        )
    return redirect("/admin")


# PAYMENT RECEIPT

@app.route("/admin/receipt/<int:order_id>")
@admin_required
def receipt(order_id):
    with db() as con:
        item = con.execute(
            "SELECT receipt FROM orders WHERE id=?", (order_id,)
        ).fetchone()

    if not item or not item["receipt"]:
        abort(404)

    return send_from_directory(RECEIPTS, item["receipt"])


# CONFIRM PAYMENT

@app.route("/admin/confirm/<int:order_id>", methods=["POST"])
@admin_required
def confirm(order_id):
    token = secrets.token_urlsafe(32)

    with db() as con:
        order = con.execute(
            "SELECT * FROM orders WHERE id=?", (order_id,)
        ).fetchone()

        if not order:
            abort(404)

        if order["status"] != "pending":
            return "تمت معالجة الطلب مسبقاً", 400

        con.execute(
            "UPDATE orders SET status='paid',token=? WHERE id=?",
            (token, order_id)
        )

    link = url_for(
        "paid_download", token=token, _external=True
    )

    return page(f"""
    <div class="card">
    <h2>تم تأكيد الدفع بنجاح</h2>
    <p>رابط تحميل التطبيق:</p>
    <a class="btn" href="{safe(link)}">تحميل التطبيق</a>
    <input readonly value="{safe(link)}">
    <a class="btn" href="/admin">العودة للإدارة</a>
    </div>
    """)


# REJECT PAYMENT

@app.route("/admin/reject/<int:order_id>", methods=["POST"])
@admin_required
def reject(order_id):
    with db() as con:
        con.execute("""
        UPDATE orders SET status='rejected',token=NULL
        WHERE id=? AND status='pending'
        """, (order_id,))

    return redirect("/admin")


# ABOUT

@app.route("/about")
def about():
    return page("""
    <div class="card">
    <h2>من نحن</h2>
    <h3>ADEL ANDROID ADSENSE</h3>
    <p>منصة متخصصة في عرض تطبيقات Android.</p>
    <p>Developed by Adel Omar Abdel Aziz</p>
    <p>AL ADL GROUP</p>
    </div>
    """)


# CONTACT

@app.route("/contact")
def contact():
    return page(f"""
    <div class="card">
    <h2>اتصل بنا</h2>
    <p>Vodafone Cash: {WALLET}</p>
    <a class="btn" target="_blank"
    href="https://wa.me/201067119916">
    تواصل عبر WhatsApp</a>
    <a class="btn" target="_blank"
    href="https://www.facebook.com/">
    صفحتنا على Facebook</a>
    </div>
    """)


# PRIVACY

@app.route("/privacy")
def privacy():
    return page("""
    <div class="card">
    <h2>سياسة الخصوصية</h2>
    <p>نحترم خصوصية زوار الموقع.</p>
    <p>تستخدم بيانات العملاء لمعالجة طلبات الشراء.</p>
    <p>قد تستخدم Google AdSense ملفات تعريف الارتباط
    وفق سياسات Google.</p>
    </div>
    """)


# ADS.TXT

@app.route("/ads.txt")
def ads_txt():
    pub = setting("adsense_id")

    if pub.startswith("ca-pub-") and pub[7:].isdigit():
        return (
            f"google.com, {pub}, DIRECT, "
            "f08c47fec0942fa0"
        )

    return "AdSense publisher information not configured", 404


# LOGOUT

@app.route("/admin/logout")
@admin_required
def logout():
    session.clear()
    return redirect("/")


# ERROR PAGES

@app.errorhandler(404)
def not_found(error):
    return page("""
    <div class="card">
    <h2>الصفحة غير موجودة</h2>
    <a class="btn" href="/">الرئيسية</a>
    </div>
    """), 404


@app.errorhandler(400)
def bad_request(error):
    return page("""
    <div class="card">
    <h2>طلب غير صالح</h2>
    <p>أعد تحميل الصفحة وحاول مرة أخرى.</p>
    </div>
    """), 400


@app.errorhandler(413)
def too_large(error):
    return page("""
    <div class="card">
    <h2>حجم الملف أكبر من المسموح (50 MB)</h2>
    </div>
    """), 413


if __name__ == "__main__":
    app.run(debug=False)
