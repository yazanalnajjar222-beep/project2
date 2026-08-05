import os
from flask import Flask, render_template, request, redirect, url_for, session
from app.main import (
    check_if_exist,
    insert_user,
    insert_category,
    get_categories_by_user,
    get_category_summary,
    insert_expense,
    get_expenses_by_user,
    get_expense_by_id,
    update_expense,
    delete_expense,
    search_expenses,
    delete_category,
    get_budget_summary
    
)

BASE_DIR = os.path.abspath(os.path.dirname(__file__)) 
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

app = Flask(__name__,
    template_folder=os.path.join(FRONTEND_DIR, "templates"),
    static_folder=os.path.join(FRONTEND_DIR, "static"))

app.secret_key = "dev-secret-change-me"


# Helper function to check auth
def is_logged_in():
    return "user_id" in session



@app.route("/")
def base():
    if is_logged_in():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = check_if_exist(email, password)
        print(f"Login attempt for {email}: {'Success' if user else 'Failure'}")
        
        if user:
            session["user_id"] = str(user["id"])
            session["email"] = user["email"]
            session["name"] = user["name"]
            print(f"Logged in user: {session['name']} ({session['email']})")
            return redirect(url_for("dashboard"))
        
        else:
            return render_template("login.html", error="Invalid email or password")

    return render_template('login.html')


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        #confirm_password = request.form.get("confirm-password")
        print(f"{name}, {email}, {password}")
        

        user_id = insert_user(name, password, email)
        if user_id:
            session["user_id"] = user_id
            session["email"] = email
            session["name"] = name
            return redirect(url_for("dashboard"))
        else:
            return render_template("register.html", error="Registration failed. Email may already exist.")

    return render_template("register.html")


@app.route("/auth/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))



@app.route("/dashboard", methods=["GET","POST"])
def dashboard():
    if not is_logged_in():
        return redirect(url_for("login"))

    user_id = session["user_id"]
    if request.method == "POST":
        expense_id = request.form.get("expense_id")
        print(f"Received POST request to delete expense {expense_id} for user {user_id}")
        if expense_id:
            delete_expense(expense_id, user_id)
            print(f"Deleted expense {expense_id} for user {user_id}")
        return redirect(url_for("dashboard"))
    # Filter arguments
    category_id = request.args.get("category")
    min_amount = request.args.get("min_amount")
    max_amount = request.args.get("max_amount")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if any([category_id, min_amount, max_amount, start_date, end_date]):
        expense_list = search_expenses(
            user_id=user_id,
            category_id=category_id,
            min_amount=min_amount,
            max_amount=max_amount,
            start_date=start_date,
            end_date=end_date,
        )
    else:
        expense_list = get_expenses_by_user(user_id)

    user_categories = get_categories_by_user(user_id)
    summary = get_category_summary(user_id)
    budget_summary = get_budget_summary(user_id)   
    return render_template(
        "dashboard.html",
        expenses=expense_list,
        categories=user_categories,
        summary=summary,
        filters=request.args,
        budget_summary=budget_summary
        
    )



@app.route("/categories", methods=["GET", "POST"])
def manage_categories():
    if not is_logged_in():
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # Handle Form Submission (POST)
    if request.method == "POST":
        name = request.form.get("name")
        monthly_budget = request.form.get("monthly_budget")

        if name and monthly_budget:
            insert_category(user_id, name, float(monthly_budget))
        
        return redirect(url_for("manage_categories"))

    # Render Page (GET)
    user_categories = get_categories_by_user(user_id)
    return render_template("categories.html", categories=user_categories)

@app.route("/categories/delete/<category_id>", methods=["POST"])
def remove_category(category_id):
    if not is_logged_in():
        return redirect(url_for("login"))

    user_id = session["user_id"]
    delete_category(category_id, user_id)
    
    return redirect(url_for("manage_categories"))




@app.route("/expense/add", methods=["GET", "POST"])
def expense_form():
    if not is_logged_in():
        return redirect(url_for("login"))

    user_id = session["user_id"]

    if request.method == "POST":
        category_id = request.form.get("category_id")
        amount = float(request.form.get("amount"))
        description = request.form.get("description")
        expense_date = request.form.get("expense_date")

        insert_expense(user_id, category_id, amount, description, expense_date)
        return redirect(url_for("dashboard"))

    user_categories = get_categories_by_user(user_id)
    print("CATEGORIES FOR USER:", user_categories)
    return render_template("expense_form.html", categories=user_categories, expense=None)


@app.route("/expense/edit/<expense_id>", methods=["GET", "POST"])
def edit_expense(expense_id):
    if not is_logged_in():
        return redirect(url_for("login"))

    user_id = session["user_id"]
    expense = get_expense_by_id(expense_id)

    # Ownership check
    if not expense or str(expense["user_id"]) != user_id:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        action = request.form.get("action")

        if action == "delete":
            delete_expense(expense_id, user_id)
        else:
            category_id = request.form.get("category_id")
            amount = float(request.form.get("amount"))
            description = request.form.get("description")
            expense_date = request.form.get("expense_date")

            update_expense(expense_id, user_id, category_id, amount, description, expense_date)

        return redirect(url_for("dashboard"))

    user_categories = get_categories_by_user(user_id)
    return render_template("expense_form.html", categories=user_categories, expense=expense)


if __name__ == "__main__":
    app.run(debug=True)
