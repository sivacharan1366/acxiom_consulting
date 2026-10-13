
from flask import Flask, request, redirect, session, render_template_string, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3, os, time

app = Flask(__name__)
app.secret_key = os.environ.get("CRM_SECRET_KEY", "local-demo-key-change-before-deployment")
DB = "crm.db"

SCHEMA = {
    "customers": {
        "name": "Customer", "fields": ["name", "email", "phone", "company"],
        "columns": "name TEXT NOT NULL, email TEXT, phone TEXT, company TEXT, owner TEXT"
    },
    "leads": {
        "name": "Lead", "fields": ["name", "email", "source", "status", "value", "owner"],
        "columns": "name TEXT NOT NULL, email TEXT, source TEXT, status TEXT DEFAULT 'New', value REAL DEFAULT 0, owner TEXT"
    },
    "opportunities": {
        "name": "Opportunity", "fields": ["name", "amount", "stage", "probability", "close_date", "owner"],
        "columns": "name TEXT NOT NULL, amount REAL DEFAULT 0, stage TEXT DEFAULT 'Prospecting', probability INTEGER DEFAULT 0, close_date TEXT, status TEXT DEFAULT 'Open', owner TEXT"
    },
    "followups": {
        "name": "Follow-up", "fields": ["lead_id", "due_date", "notes", "status", "owner"],
        "columns": "lead_id INTEGER, due_date TEXT NOT NULL, notes TEXT, status TEXT DEFAULT 'Pending', owner TEXT"
    },
    "activities": {
        "name": "Activity", "fields": ["type", "details", "owner"],
        "columns": "type TEXT NOT NULL, details TEXT, owner TEXT"
    }
}

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def audit(action, details=""):
    con = db()
    con.execute("INSERT INTO audit(username,action,details,created) VALUES(?,?,?,CURRENT_TIMESTAMP)",
                (session.get("user", "system"), action, details))
    con.commit()
    con.close()

def setup():
    con = db()
    con.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT,
        failures INTEGER DEFAULT 0, locked_until REAL DEFAULT 0)""")
    con.execute("""CREATE TABLE IF NOT EXISTS audit(
        id INTEGER PRIMARY KEY, username TEXT, action TEXT, details TEXT, created TEXT)""")
    for table, spec in SCHEMA.items():
        con.execute(f"CREATE TABLE IF NOT EXISTS {table}(id INTEGER PRIMARY KEY, {spec['columns']})")
    for username, password, role in [
        ("admin", "Admin@12345", "Admin"),
        ("manager", "Manager@12345", "Manager"),
        ("sales", "Sales@12345", "SalesExecutive")
    ]:
        con.execute("INSERT OR IGNORE INTO users(username,password,role) VALUES(?,?,?)",
                    (username, generate_password_hash(password), role))
    con.commit()
    con.close()

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            return redirect("/login")
        return fn(*args, **kwargs)
    return wrapped

def roles(*allowed):
    def deco(fn):
        @wraps(fn)
        @login_required
        def wrapped(*args, **kwargs):
            if session.get("role") not in allowed:
                return "Forbidden: insufficient role permissions", 403
            return fn(*args, **kwargs)
        return wrapped
    return deco

BASE = """
<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AcxiomCRM Lite</title><style>
body{font:16px Arial;margin:28px;background:#f2f5fa;color:#182943}
nav,a{margin-right:12px;color:#17549a}main,.card{background:white;padding:18px;border-radius:10px;margin:16px 0}
input,button{padding:9px;margin:5px}table{border-collapse:collapse;width:100%;background:white}
td,th{padding:9px;border-bottom:1px solid #ddd;text-align:left}button{cursor:pointer}
</style></head><body><h1>AcxiomCRM Lite</h1>
{% if user %}<p>{{user}} · {{role}}</p><nav><a href="/">Dashboard</a>
{% for t in tables %}<a href="/{{t}}">{{t.title()}}</a>{% endfor %}
<a href="/reports">Reports</a><a href="/audit">Audit</a><a href="/logout">Logout</a></nav>{% endif %}
{{ body|safe }}</body></html>
{{ body|safe }}
<script>
document.querySelectorAll("input").forEach(input => {
    if (input.name === "email") input.type = "email";

    if (["amount", "value", "probability", "lead_id"].includes(input.name)) {
        input.type = "number";
        input.min = "0";
    }

    if (["due_date", "close_date"].includes(input.name)) {
        input.type = "date";
    }

    if (["amount", "value"].includes(input.name)) input.step = "any";

    if (input.name === "probability") input.max = "100";
});

document.querySelectorAll("form[method='post']").forEach(form => {
    form.addEventListener("submit", function(event) {
        const amount = form.querySelector('[name="amount"]');
        const value = form.querySelector('[name="value"]');
        const probability = form.querySelector('[name="probability"]');
        const email = form.querySelector('[name="email"]');

        if (amount && amount.value !== "" && Number(amount.value) < 0) {
            alert("Amount cannot be negative.");
            event.preventDefault();
            return;
        }

        if (value && value.value !== "" && Number(value.value) < 0) {
            alert("Lead value cannot be negative.");
            event.preventDefault();
            return;
        }

        if (probability && probability.value !== "" &&
            (Number(probability.value) < 0 || Number(probability.value) > 100)) {
            alert("Probability must be between 0 and 100.");
            event.preventDefault();
            return;
        }

        if (email && email.value !== "" && !email.validity.valid) {
            alert("Please enter a valid email address.");
            event.preventDefault();
        }
    });
});
</script>
</body></html>

"""

def page(body, **data):
    return render_template_string(BASE, body=body, user=session.get("user"),
        role=session.get("role"), tables=list(SCHEMA), **data)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        con = db()
        u = con.execute("SELECT * FROM users WHERE username=?", (request.form.get("username","").strip(),)).fetchone()
        if u and u["locked_until"] > time.time():
            error = "Account locked for 5 minutes after repeated failed attempts."
        elif u and check_password_hash(u["password"], request.form.get("password","")):
            con.execute("UPDATE users SET failures=0,locked_until=0 WHERE id=?", (u["id"],))
            con.commit(); con.close()
            session.clear(); session["user"] = u["username"]; session["role"] = u["role"]
            audit("LOGIN")
            return redirect("/")
        else:
            error = "Invalid login"
            if u:
                failures = u["failures"] + 1
                con.execute("UPDATE users SET failures=?,locked_until=? WHERE id=?",
                            (failures, time.time()+300 if failures >= 5 else 0, u["id"]))
            con.commit()
        con.close()
    body = f"""<main><h2>Login</h2><p style='color:red'>{error}</p>
    <form method='post'><input name='username' placeholder='Username' required>
    <input name='password' type='password' placeholder='Password' required>
    <button>Login</button></form><small>Demo: admin / Admin@12345</small></main>"""
    return page(body)

@app.route("/logout")
def logout():
    if session.get("user"): audit("LOGOUT")
    session.clear()
    return redirect("/login")

@app.route("/")
@login_required
def dashboard():
    con = db()
    counts = {}
    for t in SCHEMA:
        if session["role"] == "SalesExecutive" and "owner" in SCHEMA[t]["columns"]:
            counts[t] = con.execute(f"SELECT COUNT(*) FROM {t} WHERE owner=?", (session["user"],)).fetchone()[0]
        else:
            counts[t] = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    pipeline = con.execute("SELECT COALESCE(SUM(amount*probability/100.0),0) FROM opportunities WHERE status='Open'").fetchone()[0]
    con.close()
    cards = "".join(f"<div class='card'><b>{t.title()}</b><h2>{n}</h2></div>" for t,n in counts.items())
    return page(f"<h2>Dashboard</h2>{cards}<div class='card'>Weighted open pipeline: {pipeline:.2f}</div>")

@app.route("/<table>", methods=["GET", "POST"])
@login_required
def records(table):
    if table not in SCHEMA: return "Not found", 404
    spec = SCHEMA[table]; fields = spec["fields"]; con = db()
    if request.method == "POST":
        values = {f: request.form.get(f, "").strip() for f in fields}
        if "name" in fields and not values["name"]:
            con.close(); return "Name is required", 400
        if table == "leads" and values["status"] not in ("New","Contacted","Qualified","Lost","Converted"):
            con.close(); return "Invalid lead status", 400
        if table == "opportunities":
            try:
                amount = float(values["amount"] or 0); prob = int(values["probability"] or 0)
                if amount < 0 or not 0 <= prob <= 100: raise ValueError()
                values["amount"], values["probability"] = amount, prob
            except ValueError:
                con.close(); return "Amount must be non-negative and probability 0–100", 400
        if "value" in fields:
            try:
                values["value"] = float(values["value"] or 0)
                if values["value"] < 0: raise ValueError()
            except ValueError:
                con.close(); return "Lead value must be non-negative", 400
        if "owner" in fields:
            values["owner"] = session["user"] if session["role"] == "SalesExecutive" else (values.get("owner") or session["user"])
        if table == "opportunities":
            values["status"] = "Open"
        sqlfields = list(values)
        con.execute(f"INSERT INTO {table}({','.join(sqlfields)}) VALUES({','.join('?' for _ in sqlfields)})",
                    tuple(values[f] for f in sqlfields))
        con.commit(); con.close(); audit("CREATE", f"{table}: {values}")
        return redirect("/"+table)
    if session["role"] == "SalesExecutive" and "owner" in spec["columns"]:
        rows = con.execute(f"SELECT * FROM {table} WHERE owner=? ORDER BY id DESC", (session["user"],)).fetchall()
    else:
        rows = con.execute(f"SELECT * FROM {table} ORDER BY id DESC").fetchall()
    con.close()
    inputs = "".join(f"<label>{f.replace('_',' ').title()} <input name='{f}' {'required' if f in ('name','due_date','type') else ''}></label>" for f in fields)
    heads = "".join(f"<th>{c}</th>" for c in rows[0].keys()) if rows else "<th>ID</th>"+ "".join(f"<th>{f}</th>" for f in fields)
    bodyrows = ""
    for row in rows:
        cells = "".join(f"<td>{row[k] if row[k] is not None else ''}</td>" for k in row.keys())
        actions = ""
        if table == "leads" and row["status"] == "Qualified":
            actions += f"<form style='display:inline' method='post' action='/convert/{row['id']}'><button>Convert</button></form>"
        if table == "followups" and row["status"] != "Completed":
            actions += f"<form style='display:inline' method='post' action='/complete/{row['id']}'><button>Complete</button></form>"
        actions += f"<form style='display:inline' method='post' action='/delete/{table}/{row['id']}'><button>Delete</button></form>"
        bodyrows += f"<tr>{cells}<td>{actions}</td></tr>"
    body = f"<main><h2>{spec['name']} Management</h2><form method='post'>{inputs}<button>Add</button></form></main><h3>Records</h3><table><tr>{heads}<th>Actions</th></tr>{bodyrows}</table>"
    return page(body)

@app.route("/delete/<table>/<int:rid>", methods=["POST"])
@login_required
def delete(table, rid):
    if table not in SCHEMA: return "Not found", 404
    con = db()
    row = con.execute(f"SELECT * FROM {table} WHERE id=?", (rid,)).fetchone()
    if not row: con.close(); return "Record not found", 404
    if session["role"] == "SalesExecutive" and "owner" in row.keys() and row["owner"] != session["user"]:
        con.close(); return "Forbidden", 403
    con.execute(f"DELETE FROM {table} WHERE id=?", (rid,))
    con.commit(); con.close(); audit("DELETE", f"{table} id={rid}")
    return redirect("/"+table)

@app.route("/convert/<int:rid>", methods=["POST"])
@login_required
def convert(rid):
    con = db()
    lead = con.execute("SELECT * FROM leads WHERE id=?", (rid,)).fetchone()
    if not lead: con.close(); return "Lead not found", 404
    if session["role"] == "SalesExecutive" and lead["owner"] != session["user"]:
        con.close(); return "Forbidden", 403
    if lead["status"] != "Qualified": con.close(); return "Only qualified leads can convert", 400
    con.execute("INSERT INTO customers(name,email,owner) VALUES(?,?,?)",
                (lead["name"],lead["email"],session["user"]))
    con.execute("UPDATE leads SET status='Converted' WHERE id=?", (rid,))
    con.commit(); con.close(); audit("CONVERT_LEAD", str(rid))
    return redirect("/leads")

@app.route("/complete/<int:rid>", methods=["POST"])
@login_required
def complete(rid):
    con = db()
    row = con.execute("SELECT * FROM followups WHERE id=?", (rid,)).fetchone()
    if not row: con.close(); return "Follow-up not found", 404
    if session["role"] == "SalesExecutive" and row["owner"] != session["user"]:
        con.close(); return "Forbidden", 403
    con.execute("UPDATE followups SET status='Completed' WHERE id=?", (rid,))
    con.commit(); con.close(); audit("COMPLETE_FOLLOWUP", str(rid))
    return redirect("/followups")

@app.route("/reports")
@login_required
def reports():
    con = db()
    rows = []
    for t in SCHEMA:
        rows.append(f"<li>{t.title()}: {con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}</li>")
    con.close()
    return page("<main><h2>Basic CRM Report</h2><ul>"+"".join(rows)+"</ul></main>")

@app.route("/audit")
@roles("Admin", "Manager")
def audit_page():
    con = db(); rows = con.execute("SELECT * FROM audit ORDER BY id DESC LIMIT 100").fetchall(); con.close()
    return page("<h2>Audit Log</h2><table><tr><th>User</th><th>Action</th><th>Details</th><th>Time</th></tr>" +
        "".join(f"<tr><td>{r['username']}</td><td>{r['action']}</td><td>{r['details']}</td><td>{r['created']}</td></tr>" for r in rows)+"</table>")

@app.route("/api/<table>")
@login_required
def api(table):
    if table not in SCHEMA: return jsonify(error="Unknown resource"), 404
    con = db()
    if session["role"] == "SalesExecutive" and "owner" in SCHEMA[table]["columns"]:
        rows = con.execute(f"SELECT * FROM {table} WHERE owner=?", (session["user"],)).fetchall()
    else:
        rows = con.execute(f"SELECT * FROM {table}").fetchall()
    con.close()
    return jsonify([dict(r) for r in rows])

if __name__ == "__main__":
    setup()
    app.run(debug=True)
