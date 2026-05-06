from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/", methods=["GET"])
def welcome():
    return render_template("welcome.html")

@app.route("/login-selection", methods=["GET"])
def login_selection():
    return render_template("login_select.html")

@app.route("/farmer-login", methods=["GET", "POST"])
def farmer_login():
    if request.method == "POST":
        username = request.form.get("username")
        return f"Farmer Login Success: {username}"
    return render_template("farmer_login.html")

@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        return f"Admin Login Success: {username}"
    return render_template("admin_login.html")

@app.route("/expert-login", methods=["GET", "POST"])
def expert_login():
    if request.method == "POST":
        username = request.form.get("username")
        return f"Expert Login Success: {username}"
    return render_template("expert_login.html")

if __name__ == "__main__":
    app.run(debug=True)