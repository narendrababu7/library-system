from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "library123"
DB_NAME = "library.db"

# ---------- Initialize DB ----------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    # Users table
    cur.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )""")
    # Books table
    cur.execute("""CREATE TABLE IF NOT EXISTS books(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        author TEXT,
        quantity INTEGER
    )""")
    # Members table
    cur.execute("""CREATE TABLE IF NOT EXISTS members(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT
    )""")
    # Transactions (Issue/Return) table
    cur.execute("""CREATE TABLE IF NOT EXISTS transactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_name TEXT,
        book_title TEXT,
        status TEXT DEFAULT 'borrowed'
    )""")
    conn.commit()
    conn.close()

init_db()

# ---------- Shared Navbar ----------
TOP_NAV = '''
<div style="position:fixed;top:0;left:0;width:100%;height:60px;background:#1e272e;color:white;display:flex;align-items:center;justify-content:space-between;padding:0 20px;box-shadow:0 2px 5px rgba(0,0,0,0.2);z-index:100;">
  <div style="font-size:22px;font-weight:bold;">BookHive</div>
  <div style="display:flex;gap:20px;align-items:center;">
    <a href="/dashboard" style="color:white;text-decoration:none;">Dashboard</a>
    <a href="/books" style="color:white;text-decoration:none;">Books</a>
    <a href="/members" style="color:white;text-decoration:none;">Members</a>
    <a href="/issue_return" style="color:white;text-decoration:none;">Issue/Return</a>
    <a href="/reports" style="color:white;text-decoration:none;">Reports</a>
    <a href="/logout" style="color:white;background:#ff4757;padding:6px 12px;border-radius:4px;text-decoration:none;margin-right:40px;">Logout</a>
  </div>
</div>
'''

FOOTER = '''
<div style="margin-top:40px;padding:20px;text-align:center;background:#1e272e;color:white;">
  <p>BookHive Library &copy; 2025</p>
</div>
'''

# ---------- Login & Signup ----------
@app.route("/", methods=["GET", "POST"])
def login():
    msg = ""
    if request.method == "POST":
        u, p = request.form["username"], request.form["password"]
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT role FROM users WHERE username=? AND password=?", (u, p))
        row = cur.fetchone()
        conn.close()
        if row:
            session["user"] = u
            session["role"] = row[0]
            return redirect("/dashboard")
        else:
            msg = "Invalid credentials!"
    return render_template("login.html", msg=msg)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    msg = ""
    if request.method == "POST":
        u, p, role = request.form["username"], request.form["password"], request.form["role"]
        try:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)", (u, p, role))
            conn.commit()
            conn.close()
            return redirect("/")
        except:
            msg = "Username already exists!"
    return render_template("signup.html", msg=msg)

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")
    if session["role"] == "admin":
        return render_template("dashboard_admin.html", user=session["user"], topnav=TOP_NAV, footer=FOOTER)
    else:
        return render_template("dashboard_user.html", user=session["user"], topnav=TOP_NAV, footer=FOOTER)

# ---------- Books ----------
@app.route("/books", methods=["GET", "POST"])
def books():
    if "user" not in session: return redirect("/")
    search = request.args.get("search", "")
    msg = ""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # Admin actions
    if request.method == "POST" and session["role"] == "admin":
        if "add" in request.form:
            cur.execute("INSERT INTO books(title,author,quantity) VALUES(?,?,?)",
                        (request.form["title"], request.form["author"], request.form["quantity"]))
            conn.commit()
            msg = "Book added!"
        elif "delete" in request.form:
            cur.execute("DELETE FROM books WHERE id=?", (request.form["delete"],))
            conn.commit()
            msg = "Book deleted!"

    # User Borrow/Cancel
    if request.method == "POST" and session["role"] != "admin":
        if "borrow" in request.form:
            cur.execute("UPDATE books SET quantity = quantity-1 WHERE id=? AND quantity>0", (request.form["borrow"],))
            if cur.rowcount > 0:
                msg = "Book borrowed!"
            else:
                msg = "Not available!"
            conn.commit()
        elif "cancel" in request.form:
            cur.execute("UPDATE books SET quantity = quantity+1 WHERE id=?", (request.form["cancel"],))
            conn.commit()
            msg = "Borrow cancelled!"

    # Auto-populate with 20 books if DB is empty
    cur.execute("SELECT COUNT(*) FROM books")
    count = cur.fetchone()[0]
    if count < 20:
        books_list = [
            ("To Kill a Mockingbird", "Harper Lee", 8),
            ("1984", "George Orwell", 10),
            ("Pride and Prejudice", "Jane Austen", 7),
            ("The Great Gatsby", "F. Scott Fitzgerald", 5),
            ("Moby-Dick", "Herman Melville", 6),
            ("The Catcher in the Rye", "J.D. Salinger", 9),
            ("War and Peace", "Leo Tolstoy", 4),
            ("Crime and Punishment", "Fyodor Dostoevsky", 6),
            ("The Odyssey", "Homer", 5),
            ("Brave New World", "Aldous Huxley", 7),
            ("The Hobbit", "J.R.R. Tolkien", 12),
            ("Fahrenheit 451", "Ray Bradbury", 5),
            ("Animal Farm", "George Orwell", 15),
            ("Jane Eyre", "Charlotte Brontë", 6),
            ("Wuthering Heights", "Emily Brontë", 5),
            ("The Alchemist", "Paulo Coelho", 11),
            ("The Book Thief", "Markus Zusak", 8),
            ("Lord of the Flies", "William Golding", 6),
            ("The Shining", "Stephen King", 4),
            ("The Da Vinci Code", "Dan Brown", 10)
        ]
        for i in range(count, 20):
            cur.execute("INSERT INTO books(title,author,quantity) VALUES(?,?,?)", books_list[i])
        conn.commit()

    # Fetch filtered books
    cur.execute("SELECT * FROM books WHERE title LIKE ?", ('%' + search + '%',))
    books = cur.fetchall()
    conn.close()

    template = "books_admin.html" if session["role"] == "admin" else "books_user.html"
    return render_template(template, books=books, msg=msg, search=search, topnav=TOP_NAV, footer=FOOTER)

# ---------- Edit Book ----------
@app.route("/edit_book/<int:book_id>", methods=["GET", "POST"])
def edit_book(book_id):
    if "user" not in session or session["role"] != "admin":
        return redirect("/")
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    if request.method == "POST":
        cur.execute("UPDATE books SET title=?, author=?, quantity=? WHERE id=?",
                    (request.form["title"], request.form["author"], request.form["quantity"], book_id))
        conn.commit()
        conn.close()
        return redirect("/books")
    cur.execute("SELECT * FROM books WHERE id=?", (book_id,))
    book = cur.fetchone()
    conn.close()
    return render_template("edit_book.html", book=book, topnav=TOP_NAV, footer=FOOTER)

# ---------- Members ----------
@app.route("/members", methods=["GET", "POST"])
def members():
    if "user" not in session:
        return redirect("/")
    search = request.args.get("search", "")
    msg = ""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    if request.method == "POST" and session["role"] == "admin":
        if "add" in request.form:
            cur.execute("INSERT INTO members(name,email) VALUES(?,?)", (request.form["name"], request.form["email"]))
            conn.commit()
            msg = "Member added!"
        elif "delete" in request.form:
            cur.execute("DELETE FROM members WHERE id=?", (request.form["delete"],))
            conn.commit()
            msg = "Member deleted!"

    cur.execute("SELECT * FROM members WHERE name LIKE ?", ('%' + search + '%',))
    members = cur.fetchall()
    conn.close()
    template = "members_admin.html" if session["role"] == "admin" else "members_user.html"
    return render_template(template, members=members, msg=msg, search=search, topnav=TOP_NAV, footer=FOOTER)

# ---------- Issue / Return ----------
@app.route("/issue_return", methods=["GET", "POST"])
def issue_return():
    if "user" not in session:
        return redirect("/")
    msg = ""
    search = request.args.get("search", "")
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # Issue
    if request.method == "POST" and "issue" in request.form:
        member, book = request.form["member"], request.form["book"]
        cur.execute("INSERT INTO transactions(member_name, book_title, status) VALUES(?,?,?)",
                    (member, book, "borrowed"))
        cur.execute("UPDATE books SET quantity=quantity-1 WHERE title=? AND quantity>0", (book,))
        conn.commit()
        msg = f"Book '{book}' issued to {member}."

    # Return
    if request.method == "POST" and "return" in request.form:
        tid = request.form["return"]
        cur.execute("UPDATE transactions SET status='returned' WHERE id=?", (tid,))
        cur.execute("UPDATE books SET quantity=quantity+1 WHERE title=(SELECT book_title FROM transactions WHERE id=?)", (tid,))
        conn.commit()
        msg = "Book marked as returned."

    if search:
        cur.execute("""SELECT * FROM transactions 
                       WHERE member_name LIKE ? OR book_title LIKE ? 
                       ORDER BY id DESC""", (f"%{search}%", f"%{search}%"))
    else:
        cur.execute("SELECT * FROM transactions ORDER BY id DESC")
    transactions = cur.fetchall()
    conn.close()

    return render_template("issue_return.html", transactions=transactions, msg=msg,
                           search=search, topnav=TOP_NAV, footer=FOOTER)

# ---------- Reports ----------
@app.route("/reports")
def reports():
    if "user" not in session:
        return redirect("/")
    return render_template("reports.html", topnav=TOP_NAV, footer=FOOTER)

# ---------- Logout ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
