import os
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps
from getpass import getpass

import mysql.connector
from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from mysql.connector import Error
from werkzeug.security import check_password_hash

load_dotenv()

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("FLASK_SECRET_KEY") or os.environ.get("SECRET_KEY"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_COOKIE_SECURE") == "1",
)


def get_db_connection():
    password = os.environ.get("MYSQL_PASSWORD")
    if not password:
        raise RuntimeError("Set the MYSQL_PASSWORD environment variable before starting the app.")

    return mysql.connector.connect(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        user=os.environ.get("MYSQL_USER", "root"),
        password=password,
        database=os.environ.get("MYSQL_DATABASE", "nasa_food_inventory"),
    )


def role_required(*allowed_roles):
    def decorator(view):
        @wraps(view)
        def decorated_view(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if session.get("user_role") not in allowed_roles:
                abort(403)
            return view(*args, **kwargs)

        return decorated_view

    return decorator


login_required = role_required("Admin", "Manager", "Staff")
staff_or_above = role_required("Admin", "Manager", "Staff")
manager_required = role_required("Admin", "Manager")
admin_required = role_required("Admin")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("home"))

    email = ""
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        if not email or len(email) > 254 or not password:
            error = "Invalid email or password."
        else:
            connection = None
            cursor = None
            try:
                connection = get_db_connection()
                cursor = connection.cursor()
                cursor.execute(
                    """
                    SELECT user_id, name, role, password
                    FROM users
                    WHERE email = %s
                    FOR UPDATE
                    """,
                    (email,),
                )
                user = cursor.fetchone()
                if user is not None:
                    user_id, name, role, stored_password = user
                    try:
                        valid_password = check_password_hash(stored_password, password)
                    except (TypeError, ValueError):
                        valid_password = False

                    if valid_password:
                        session.clear()
                        session["user_id"] = user_id
                        session["user_name"] = name
                        session["user_role"] = role
                        flash(f"Welcome, {name}.", "success")
                        return redirect(url_for("home"))

                error = "Invalid email or password."
            except (Error, RuntimeError):
                if connection is not None:
                    connection.rollback()
                app.logger.exception("Could not authenticate user.")
                return (
                    "Could not sign in right now. Check the database connection "
                    "and try again.",
                    503,
                )
            finally:
                if cursor is not None:
                    cursor.close()
                if connection is not None and connection.is_connected():
                    connection.close()

        if error:
            flash(error, "error")

    return render_template("login.html", email=email)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/")
@login_required
def home():
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT COUNT(*) FROM food_items")
        total_food = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM inventory WHERE quantity <= reorder_level"
        )
        low_stock = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM food_items WHERE expiry_date < CURDATE()"
        )
        expired_food = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM missions WHERE status = %s", ("Active",))
        active_missions = cursor.fetchone()[0]
        cursor.execute("SELECT COALESCE(SUM(quantity), 0) FROM inventory")
        total_inventory_quantity = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM astronauts")
        total_astronauts = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM food_allocation")
        total_allocations = cursor.fetchone()[0]
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM food_items
            WHERE expiry_date BETWEEN CURDATE()
                AND DATE_ADD(CURDATE(), INTERVAL 30 DAY)
            """
        )
        expiring_soon = cursor.fetchone()[0]
        cursor.execute(
            """
            SELECT f.food_name, st.transaction_type, st.quantity,
                   st.transaction_date
            FROM stock_transactions st
            JOIN food_items f ON f.food_id = st.food_id
            ORDER BY st.transaction_date DESC, st.transaction_id DESC
            LIMIT 5
            """
        )
        recent_transactions = cursor.fetchall()
        cursor.execute(
            """
            SELECT food_name, expiry_date
            FROM food_items
            WHERE expiry_date BETWEEN CURDATE()
                AND DATE_ADD(CURDATE(), INTERVAL 30 DAY)
            ORDER BY expiry_date, food_name
            LIMIT 5
            """
        )
        upcoming_expiry = cursor.fetchall()
    except (Error, RuntimeError):
        app.logger.exception("Could not load dashboard data from MySQL.")
        return (
            "Could not connect to the database. Check the MySQL service and "
            "database settings, including MYSQL_PASSWORD.",
            503,
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    return render_template(
        "index.html",
        total_food=total_food,
        low_stock=low_stock,
        expired_food=expired_food,
        active_missions=active_missions,
        total_inventory_quantity=total_inventory_quantity,
        expiring_soon=expiring_soon,
        total_astronauts=total_astronauts,
        total_allocations=total_allocations,
        recent_transactions=recent_transactions,
        upcoming_expiry=upcoming_expiry,
    )


@app.route("/food")
@staff_or_above
def food():
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT f.food_id, f.food_name, f.calories, f.protein, f.carbs,
                   f.fat, f.unit, c.category_name, s.supplier_name, f.expiry_date
            FROM food_items f
            JOIN food_categories c ON c.category_id = f.category_id
            JOIN suppliers s ON s.supplier_id = f.supplier_id
            ORDER BY f.food_id
            """
        )
        foods = cursor.fetchall()
    except (Error, RuntimeError):
        app.logger.exception("Could not load food items from MySQL.")
        return (
            "Could not connect to the database. Check the MySQL service and "
            "database settings, including MYSQL_PASSWORD.",
            503,
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    return render_template(
        "food.html",
        foods=foods,
        categories=sorted({row[7] for row in foods}),
        suppliers=sorted({row[8] for row in foods}),
        added=request.args.get("added") == "1",
        updated=request.args.get("updated") == "1",
        deleted=request.args.get("deleted") == "1",
        delete_error=request.args.get("delete_error"),
        delete_inventory_count=request.args.get("inventory_count", "0"),
        delete_allocation_count=request.args.get("allocation_count", "0"),
        delete_transaction_count=request.args.get("transaction_count", "0"),
    )


@app.route("/edit-food/<int:food_id>", methods=["GET", "POST"])
@manager_required
def edit_food(food_id):
    connection = None
    cursor = None
    errors = []
    form_data = request.form.to_dict() if request.method == "POST" else None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT category_id, category_name FROM food_categories ORDER BY category_name"
        )
        categories = cursor.fetchall()
        cursor.execute(
            "SELECT supplier_id, supplier_name FROM suppliers ORDER BY supplier_name"
        )
        suppliers = cursor.fetchall()
        cursor.execute(
            """
            SELECT food_name, category_id, supplier_id, calories, protein,
                   carbs, fat, unit, expiry_date
            FROM food_items
            WHERE food_id = %s
            """,
            (food_id,),
        )
        food = cursor.fetchone()
        if food is None:
            return "Food item not found.", 404

        if request.method == "POST":
            food_name = form_data.get("food_name", "").strip()
            unit = form_data.get("unit", "").strip()
            if not food_name or len(food_name) > 150:
                errors.append("Food name is required and must be 150 characters or fewer.")
            if not unit or len(unit) > 50:
                errors.append("Unit is required and must be 50 characters or fewer.")

            try:
                category_id = int(form_data.get("category_id", ""))
                if category_id not in {row[0] for row in categories}:
                    raise ValueError
            except ValueError:
                errors.append("Select a valid food category.")
                category_id = 0

            try:
                supplier_id = int(form_data.get("supplier_id", ""))
                if supplier_id not in {row[0] for row in suppliers}:
                    raise ValueError
            except ValueError:
                errors.append("Select a valid supplier.")
                supplier_id = 0

            nutrition_values = []
            for field, label in (
                ("calories", "Calories"),
                ("protein", "Protein"),
                ("carbs", "Carbs"),
                ("fat", "Fat"),
            ):
                try:
                    value = Decimal(form_data.get(field, "").strip())
                    if not value.is_finite() or value < 0 or value > Decimal("999999.99"):
                        raise InvalidOperation
                    nutrition_values.append(value)
                except (InvalidOperation, ValueError):
                    errors.append(f"{label} must be a number from 0 to 999999.99.")

            try:
                expiry_date = date.fromisoformat(form_data.get("expiry_date", ""))
            except ValueError:
                errors.append("Enter a valid expiry date.")
                expiry_date = None

            if not errors:
                cursor.execute(
                    """
                    UPDATE food_items
                    SET food_name = %s,
                        category_id = %s,
                        supplier_id = %s,
                        calories = %s,
                        protein = %s,
                        carbs = %s,
                        fat = %s,
                        unit = %s,
                        expiry_date = %s
                    WHERE food_id = %s
                    """,
                    (
                        food_name,
                        category_id,
                        supplier_id,
                        *nutrition_values,
                        unit,
                        expiry_date,
                        food_id,
                    ),
                )
                connection.commit()
                flash("Food item updated successfully.", "success")
                return redirect(url_for("food"))
    except (Error, RuntimeError):
        if connection is not None:
            connection.rollback()
        app.logger.exception("Could not load or update food item %s.", food_id)
        return (
            "Could not update the food item. Check the database connection and try again.",
            503,
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    if form_data is None:
        form_data = {
            "food_name": food[0],
            "category_id": str(food[1]),
            "supplier_id": str(food[2]),
            "calories": str(food[3]) if food[3] is not None else "",
            "protein": str(food[4]) if food[4] is not None else "",
            "carbs": str(food[5]) if food[5] is not None else "",
            "fat": str(food[6]) if food[6] is not None else "",
            "unit": food[7] or "",
            "expiry_date": food[8].isoformat() if food[8] else "",
        }

    return (
        render_template(
            "edit_food.html",
            food=food,
            categories=categories,
            suppliers=suppliers,
            form_data=form_data,
            errors=errors,
        ),
        400 if errors else 200,
    )


@app.route("/delete-food/<int:food_id>", methods=["POST"])
@admin_required
def delete_food(food_id):
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM inventory WHERE food_id = %s),
                (SELECT COUNT(*) FROM food_allocation WHERE food_id = %s),
                (SELECT COUNT(*) FROM stock_transactions WHERE food_id = %s)
            """,
            (food_id, food_id, food_id),
        )
        inventory_count, allocation_count, transaction_count = cursor.fetchone()
        if inventory_count or allocation_count or transaction_count:
            return redirect(
                url_for(
                    "food",
                    delete_error="referenced",
                    inventory_count=inventory_count,
                    allocation_count=allocation_count,
                    transaction_count=transaction_count,
                )
            )

        cursor.execute(
            "DELETE FROM food_items WHERE food_id = %s",
            (food_id,),
        )
        if cursor.rowcount == 0:
            connection.rollback()
            return redirect(url_for("food", delete_error="not_found"))

        connection.commit()
        flash("Food item deleted successfully.", "success")
        return redirect(url_for("food"))
    except (Error, RuntimeError):
        if connection is not None:
            connection.rollback()
        app.logger.exception("Could not delete food item %s.", food_id)
        return redirect(url_for("food", delete_error="failed"))
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/add-food", methods=["GET", "POST"])
@manager_required
def add_food():
    connection = None
    cursor = None
    form_data = request.form.to_dict() if request.method == "POST" else {}
    errors = []

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT category_id, category_name FROM food_categories ORDER BY category_name"
        )
        categories = cursor.fetchall()
        cursor.execute(
            "SELECT supplier_id, supplier_name FROM suppliers ORDER BY supplier_name"
        )
        suppliers = cursor.fetchall()

        if request.method == "POST":
            food_name = form_data.get("food_name", "").strip()
            unit = form_data.get("unit", "").strip()
            if not food_name or len(food_name) > 150:
                errors.append("Food name is required and must be 150 characters or fewer.")
            if not unit or len(unit) > 50:
                errors.append("Unit is required and must be 50 characters or fewer.")

            try:
                category_id = int(form_data.get("category_id", ""))
                if category_id not in {row[0] for row in categories}:
                    raise ValueError
            except ValueError:
                errors.append("Select a valid food category.")
                category_id = 0

            try:
                supplier_id = int(form_data.get("supplier_id", ""))
                if supplier_id not in {row[0] for row in suppliers}:
                    raise ValueError
            except ValueError:
                errors.append("Select a valid supplier.")
                supplier_id = 0

            nutrition_values = []
            for field, label in (
                ("calories", "Calories"),
                ("protein", "Protein"),
                ("carbs", "Carbs"),
                ("fat", "Fat"),
            ):
                try:
                    value = Decimal(form_data.get(field, "").strip())
                    if not value.is_finite() or value < 0 or value > Decimal("999999.99"):
                        raise InvalidOperation
                    nutrition_values.append(value)
                except (InvalidOperation, ValueError):
                    errors.append(f"{label} must be a number from 0 to 999999.99.")

            try:
                expiry_date = date.fromisoformat(form_data.get("expiry_date", ""))
            except ValueError:
                errors.append("Enter a valid expiry date.")
                expiry_date = None

            if not errors:
                cursor.execute(
                    """
                    INSERT INTO food_items
                        (food_name, category_id, supplier_id, calories, protein,
                         carbs, fat, unit, expiry_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        food_name,
                        category_id,
                        supplier_id,
                        *nutrition_values,
                        unit,
                        expiry_date,
                    ),
                )
                food_id = cursor.lastrowid
                cursor.execute(
                    """
                    INSERT INTO inventory
                        (food_id, quantity, reorder_level, storage_location)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (food_id, 0, 10, "ISRO Food Storage - A"),
                )
                connection.commit()
                flash("Food item added successfully.", "success")
                return redirect(url_for("food"))
    except (Error, RuntimeError):
        if connection is not None:
            connection.rollback()
        app.logger.exception("Could not load or save a food item.")
        return (
            "Could not save the food item. Check the database connection and try again.",
            503,
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    return (
        render_template(
            "add_food.html",
            categories=categories,
            suppliers=suppliers,
            form_data=form_data,
            errors=errors,
        ),
        400 if errors else 200,
    )

@app.route("/inventory")
@staff_or_above
def inventory():
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                f.food_id,
                f.food_name,
                i.quantity,
                i.reorder_level,
                i.storage_location,
                f.expiry_date
            FROM inventory i
            JOIN food_items f ON i.food_id = f.food_id
            ORDER BY f.food_name
            """
        )
        inventory_data = cursor.fetchall()
        cursor.execute(
            """
            SELECT
                COUNT(*),
                COALESCE(SUM(quantity), 0),
                COALESCE(SUM(CASE WHEN quantity <= reorder_level THEN 1 ELSE 0 END), 0)
            FROM inventory
            """
        )
        total_items, total_quantity, low_stock = cursor.fetchone()
        cursor.execute("SELECT COUNT(*) FROM food_items WHERE expiry_date < CURDATE()")
        expired_items = cursor.fetchone()[0]
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM food_items
            WHERE expiry_date BETWEEN CURDATE()
                AND DATE_ADD(CURDATE(), INTERVAL 30 DAY)
            """
        )
        expiring_items = cursor.fetchone()[0]
    except (Error, RuntimeError):
        app.logger.exception("Could not load inventory data from MySQL.")
        return (
            "Could not connect to the database. Check the MySQL service and "
            "database settings, including MYSQL_PASSWORD.",
            503,
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    return render_template(
        "inventory.html",
        inventory_data=inventory_data,
        total_items=total_items,
        total_quantity=total_quantity,
        low_stock=low_stock,
        expired_items=expired_items,
        expiring_items=expiring_items,
        today=date.today(),
        warning_date=date.today() + timedelta(days=30),
        updated=request.args.get("updated") == "1",
    )


@app.route("/edit-inventory/<int:food_id>", methods=["GET", "POST"])
@manager_required
def edit_inventory(food_id):
    connection = None
    cursor = None
    errors = []
    form_data = request.form.to_dict() if request.method == "POST" else None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT f.food_name, i.quantity, i.reorder_level, i.storage_location
            FROM inventory i
            JOIN food_items f ON i.food_id = f.food_id
            WHERE f.food_id = %s
            """,
            (food_id,),
        )
        inventory_record = cursor.fetchone()
        if inventory_record is None:
            return "Inventory record not found.", 404

        if request.method == "POST":
            try:
                quantity = int(form_data.get("quantity", ""))
                if quantity < 0 or quantity > 2147483647:
                    raise ValueError
            except ValueError:
                errors.append("Quantity must be a whole number between 0 and 2147483647.")
                quantity = 0

            try:
                reorder_level = int(form_data.get("reorder_level", ""))
                if reorder_level < 0 or reorder_level > 2147483647:
                    raise ValueError
            except ValueError:
                errors.append("Reorder level must be a whole number between 0 and 2147483647.")
                reorder_level = 0

            storage_location = form_data.get("storage_location", "").strip()
            if not storage_location:
                errors.append("Storage location is required.")
            elif len(storage_location) > 100:
                errors.append("Storage location must be 100 characters or fewer.")

            if not errors:
                cursor.execute(
                    """
                    UPDATE inventory
                    SET quantity = %s,
                        reorder_level = %s,
                        storage_location = %s
                    WHERE food_id = %s
                    """,
                    (quantity, reorder_level, storage_location, food_id),
                )
                connection.commit()
                flash("Inventory updated successfully.", "success")
                return redirect(url_for("inventory"))
    except (Error, RuntimeError):
        if connection is not None:
            connection.rollback()
        app.logger.exception("Could not load or update inventory for food item %s.", food_id)
        return (
            "Could not update inventory. Check the database connection and try again.",
            503,
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    if form_data is None:
        form_data = {
            "quantity": str(inventory_record[1]),
            "reorder_level": str(inventory_record[2]),
            "storage_location": inventory_record[3] or "",
        }

    return (
        render_template(
            "edit_inventory.html",
            food_name=inventory_record[0],
            form_data=form_data,
            errors=errors,
        ),
        400 if errors else 200,
    )


@app.route("/missions")
@staff_or_above
def missions():
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                mission_id,
                mission_name,
                mission_type,
                launch_date,
                duration_days,
                crew_size,
                status
            FROM missions
            ORDER BY launch_date
            """
        )
        missions_data = cursor.fetchall()
        cursor.execute(
            """
            SELECT
                COUNT(*),
                COALESCE(SUM(CASE WHEN status = %s THEN 1 ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN status = %s THEN 1 ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN status = %s THEN 1 ELSE 0 END), 0),
                COALESCE(SUM(crew_size), 0)
            FROM missions
            """,
            ("Active", "Planned", "Completed"),
        )
        (
            total_missions,
            active_missions,
            planned_missions,
            completed_missions,
            total_crew,
        ) = cursor.fetchone()
    except (Error, RuntimeError):
        app.logger.exception("Could not load missions from MySQL.")
        return (
            "Could not connect to the database. Check the MySQL service and "
            "database settings, including MYSQL_PASSWORD.",
            503,
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    return render_template(
        "missions.html",
        missions_data=missions_data,
        total_missions=total_missions,
        active_missions=active_missions,
        planned_missions=planned_missions,
        completed_missions=completed_missions,
        total_crew=total_crew,
        mission_types=sorted({row[2] for row in missions_data if row[2]}),
        added=request.args.get("added") == "1",
        updated=request.args.get("updated") == "1",
        deleted=request.args.get("deleted") == "1",
        delete_error=request.args.get("delete_error"),
        delete_astronaut_count=request.args.get("astronaut_count", "0"),
        delete_allocation_count=request.args.get("allocation_count", "0"),
    )


@app.route("/add-mission", methods=["GET", "POST"])
@manager_required
def add_mission():
    form_data = request.form.to_dict() if request.method == "POST" else {}
    errors = []

    if request.method == "POST":
        mission_name = form_data.get("mission_name", "").strip()
        mission_type = form_data.get("mission_type", "").strip()
        status = form_data.get("status", "")
        if not mission_name or len(mission_name) > 150:
            errors.append("Mission name is required and must be 150 characters or fewer.")
        if not mission_type or len(mission_type) > 100:
            errors.append("Mission type is required and must be 100 characters or fewer.")
        if status not in {"Planned", "Active", "Completed", "Cancelled"}:
            errors.append("Select a valid mission status.")

        try:
            launch_date = date.fromisoformat(form_data.get("launch_date", ""))
        except ValueError:
            errors.append("Enter a valid launch date.")
            launch_date = None

        try:
            duration_days = int(form_data.get("duration_days", ""))
            if duration_days < 1 or duration_days > 2147483647:
                raise ValueError
        except ValueError:
            errors.append("Duration must be a whole number greater than zero.")
            duration_days = 0

        try:
            crew_size = int(form_data.get("crew_size", ""))
            if crew_size < 1 or crew_size > 2147483647:
                raise ValueError
        except ValueError:
            errors.append("Crew size must be a whole number greater than zero.")
            crew_size = 0

        if not errors:
            connection = None
            cursor = None
            try:
                connection = get_db_connection()
                cursor = connection.cursor()
                cursor.execute(
                    """
                    INSERT INTO missions
                        (mission_name, mission_type, launch_date, duration_days,
                         crew_size, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        mission_name,
                        mission_type,
                        launch_date,
                        duration_days,
                        crew_size,
                        status,
                    ),
                )
                connection.commit()
                flash("Mission added successfully.", "success")
                return redirect(url_for("missions"))
            except (Error, RuntimeError):
                if connection is not None:
                    connection.rollback()
                app.logger.exception("Could not create a mission.")
                return (
                    "Could not save the mission. Check the database connection and try again.",
                    503,
                )
            finally:
                if cursor is not None:
                    cursor.close()
                if connection is not None and connection.is_connected():
                    connection.close()

    return (
        render_template("add_mission.html", form_data=form_data, errors=errors),
        400 if errors else 200,
    )


@app.route("/astronauts")
@staff_or_above
def astronauts():
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT a.astronaut_id, a.astronaut_name, m.mission_name, a.role,
                   a.mission_id
            FROM astronauts a
            JOIN missions m ON a.mission_id = m.mission_id
            ORDER BY a.astronaut_id
            """
        )
        astronauts_data = cursor.fetchall()
        cursor.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM astronauts),
                (SELECT COUNT(DISTINCT mission_id) FROM astronauts),
                (SELECT COUNT(*) FROM missions)
            """
        )
        total_astronauts, assigned_missions, total_missions = cursor.fetchone()
        cursor.execute("SELECT mission_id, mission_name FROM missions ORDER BY mission_name")
        astronaut_missions = cursor.fetchall()
    except (Error, RuntimeError):
        app.logger.exception("Could not load astronauts from MySQL.")
        return (
            "Could not connect to the database. Check the MySQL service and "
            "database settings, including MYSQL_PASSWORD.",
            503,
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    return render_template(
        "astronauts.html",
        astronauts=astronauts_data,
        total_astronauts=total_astronauts,
        assigned_missions=assigned_missions,
        total_missions=total_missions,
        astronaut_missions=astronaut_missions,
        added=request.args.get("added") == "1",
        updated=request.args.get("updated") == "1",
        deleted=request.args.get("deleted") == "1",
        action_error=request.args.get("action_error"),
    )


@app.route("/add-astronaut", methods=["GET", "POST"])
@manager_required
def add_astronaut():
    connection = None
    cursor = None
    form_data = request.form.to_dict() if request.method == "POST" else {}
    errors = []

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT mission_id, mission_name FROM missions ORDER BY mission_name"
        )
        missions_data = cursor.fetchall()

        if request.method == "POST":
            astronaut_name = form_data.get("astronaut_name", "").strip()
            role = form_data.get("role", "").strip()
            if not astronaut_name or len(astronaut_name) > 100:
                errors.append(
                    "Astronaut name is required and must be 100 characters or fewer."
                )
            if not role or len(role) > 100:
                errors.append("Role is required and must be 100 characters or fewer.")

            try:
                mission_id = int(form_data.get("mission_id", ""))
                if mission_id not in {row[0] for row in missions_data}:
                    raise ValueError
            except ValueError:
                errors.append("Select a valid mission.")
                mission_id = 0

            if not errors:
                cursor.execute(
                    """
                    INSERT INTO astronauts (astronaut_name, mission_id, role)
                    VALUES (%s, %s, %s)
                    """,
                    (astronaut_name, mission_id, role),
                )
                connection.commit()
                flash("Astronaut added successfully.", "success")
                return redirect(url_for("astronauts"))
    except (Error, RuntimeError):
        if connection is not None:
            connection.rollback()
        app.logger.exception("Could not load missions or create an astronaut.")
        return (
            "Could not save the astronaut. Check the database connection and try again.",
            503,
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    return (
        render_template(
            "add_astronaut.html",
            missions=missions_data,
            form_data=form_data,
            errors=errors,
        ),
        400 if errors else 200,
    )


@app.route("/edit-astronaut/<int:astronaut_id>", methods=["GET", "POST"])
@manager_required
def edit_astronaut(astronaut_id):
    connection = None
    cursor = None
    errors = []
    form_data = request.form.to_dict() if request.method == "POST" else None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT mission_id, mission_name FROM missions ORDER BY mission_name"
        )
        missions_data = cursor.fetchall()
        cursor.execute(
            """
            SELECT astronaut_id, astronaut_name, mission_id, role
            FROM astronauts
            WHERE astronaut_id = %s
            """,
            (astronaut_id,),
        )
        astronaut = cursor.fetchone()
        if astronaut is None:
            return "Astronaut not found.", 404

        if request.method == "POST":
            astronaut_name = form_data.get("astronaut_name", "").strip()
            role = form_data.get("role", "").strip()
            if not astronaut_name or len(astronaut_name) > 100:
                errors.append(
                    "Astronaut name is required and must be 100 characters or fewer."
                )
            if not role or len(role) > 100:
                errors.append("Role is required and must be 100 characters or fewer.")

            try:
                mission_id = int(form_data.get("mission_id", ""))
                if mission_id not in {row[0] for row in missions_data}:
                    raise ValueError
            except ValueError:
                errors.append("Select a valid mission.")
                mission_id = 0

            if not errors:
                cursor.execute(
                    """
                    UPDATE astronauts
                    SET astronaut_name = %s, mission_id = %s, role = %s
                    WHERE astronaut_id = %s
                    """,
                    (astronaut_name, mission_id, role, astronaut_id),
                )
                connection.commit()
                flash("Astronaut updated successfully.", "success")
                return redirect(url_for("astronauts"))
    except (Error, RuntimeError):
        if connection is not None:
            connection.rollback()
        app.logger.exception("Could not load or update astronaut %s.", astronaut_id)
        return (
            "Could not update the astronaut. Check the database connection and try again.",
            503,
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    if form_data is None:
        form_data = {
            "astronaut_name": astronaut[1],
            "mission_id": str(astronaut[2]),
            "role": astronaut[3] or "",
        }

    return (
        render_template(
            "edit_astronaut.html",
            missions=missions_data,
            form_data=form_data,
            errors=errors,
        ),
        400 if errors else 200,
    )


@app.route("/delete-astronaut/<int:astronaut_id>", methods=["POST"])
@manager_required
def delete_astronaut(astronaut_id):
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM food_allocation WHERE astronaut_id = %s",
            (astronaut_id,),
        )
        if cursor.fetchone()[0]:
            return redirect(url_for("astronauts", action_error="referenced"))

        cursor.execute(
            "DELETE FROM astronauts WHERE astronaut_id = %s",
            (astronaut_id,),
        )
        if cursor.rowcount == 0:
            connection.rollback()
            return redirect(url_for("astronauts", action_error="not_found"))

        connection.commit()
        flash("Astronaut deleted successfully.", "success")
        return redirect(url_for("astronauts"))
    except (Error, RuntimeError):
        if connection is not None:
            connection.rollback()
        app.logger.exception("Could not delete astronaut %s.", astronaut_id)
        return redirect(url_for("astronauts", action_error="failed"))
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/edit-mission/<int:mission_id>", methods=["GET", "POST"])
@manager_required
def edit_mission(mission_id):
    connection = None
    cursor = None
    errors = []
    form_data = request.form.to_dict() if request.method == "POST" else None
    valid_statuses = {"Planned", "Active", "Completed", "Cancelled"}

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT mission_id, mission_name, mission_type, launch_date,
                   duration_days, crew_size, status
            FROM missions
            WHERE mission_id = %s
            """,
            (mission_id,),
        )
        mission = cursor.fetchone()
        if mission is None:
            return "Mission not found.", 404

        if request.method == "POST":
            mission_name = form_data.get("mission_name", "").strip()
            mission_type = form_data.get("mission_type", "").strip()
            status = form_data.get("status", "")
            if not mission_name or len(mission_name) > 150:
                errors.append("Mission name is required and must be 150 characters or fewer.")
            if not mission_type or len(mission_type) > 100:
                errors.append("Mission type is required and must be 100 characters or fewer.")
            if status not in valid_statuses:
                errors.append("Select a valid mission status.")

            try:
                launch_date = date.fromisoformat(form_data.get("launch_date", ""))
            except ValueError:
                errors.append("Enter a valid launch date.")
                launch_date = None

            try:
                duration_days = int(form_data.get("duration_days", ""))
                if duration_days < 1 or duration_days > 2147483647:
                    raise ValueError
            except ValueError:
                errors.append("Duration must be a whole number greater than zero.")
                duration_days = 0

            try:
                crew_size = int(form_data.get("crew_size", ""))
                if crew_size < 1 or crew_size > 2147483647:
                    raise ValueError
            except ValueError:
                errors.append("Crew size must be a whole number greater than zero.")
                crew_size = 0

            if not errors:
                cursor.execute(
                    """
                    UPDATE missions
                    SET mission_name = %s,
                        mission_type = %s,
                        launch_date = %s,
                        duration_days = %s,
                        crew_size = %s,
                        status = %s
                    WHERE mission_id = %s
                    """,
                    (
                        mission_name,
                        mission_type,
                        launch_date,
                        duration_days,
                        crew_size,
                        status,
                        mission_id,
                    ),
                )
                connection.commit()
                flash("Mission updated successfully.", "success")
                return redirect(url_for("missions"))
    except (Error, RuntimeError):
        if connection is not None:
            connection.rollback()
        app.logger.exception("Could not load or update mission %s.", mission_id)
        return (
            "Could not update the mission. Check the database connection and try again.",
            503,
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    if form_data is None:
        form_data = {
            "mission_name": mission[1],
            "mission_type": mission[2] or "",
            "launch_date": mission[3].isoformat() if mission[3] else "",
            "duration_days": str(mission[4]) if mission[4] is not None else "",
            "crew_size": str(mission[5]) if mission[5] is not None else "",
            "status": mission[6] or "Planned",
        }

    return (
        render_template(
            "edit_mission.html",
            mission=mission,
            form_data=form_data,
            errors=errors,
            statuses=sorted(valid_statuses),
        ),
        400 if errors else 200,
    )


@app.route("/delete-mission/<int:mission_id>", methods=["POST"])
@manager_required
def delete_mission(mission_id):
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM astronauts WHERE mission_id = %s),
                (SELECT COUNT(*) FROM food_allocation WHERE mission_id = %s)
            """,
            (mission_id, mission_id),
        )
        astronaut_count, allocation_count = cursor.fetchone()
        if astronaut_count > 0 or allocation_count > 0:
            return redirect(
                url_for(
                    "missions",
                    delete_error="referenced",
                    astronaut_count=astronaut_count,
                    allocation_count=allocation_count,
                )
            )

        cursor.execute(
            "DELETE FROM missions WHERE mission_id = %s",
            (mission_id,),
        )
        if cursor.rowcount == 0:
            connection.rollback()
            return redirect(url_for("missions", delete_error="not_found"))

        connection.commit()
        flash("Mission deleted successfully.", "success")
        return redirect(url_for("missions"))
    except (Error, RuntimeError):
        if connection is not None:
            connection.rollback()
        app.logger.exception("Could not delete mission %s.", mission_id)
        return redirect(url_for("missions", delete_error="failed"))
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/allocations")
@staff_or_above
def allocations():
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                fa.allocation_id,
                m.mission_name,
                a.astronaut_name,
                f.food_name,
                fa.quantity,
                fa.allocation_date,
                fa.mission_id,
                fa.food_id
            FROM food_allocation fa
            JOIN missions m ON fa.mission_id = m.mission_id
            JOIN astronauts a ON fa.astronaut_id = a.astronaut_id
            JOIN food_items f ON fa.food_id = f.food_id
            ORDER BY fa.allocation_date DESC
            """
        )
        allocation_data = cursor.fetchall()
        cursor.execute(
            """
            SELECT
                COUNT(*),
                COALESCE(SUM(quantity), 0),
                COUNT(DISTINCT mission_id)
            FROM food_allocation
            """
        )
        total_allocations, total_allocated, allocated_missions = cursor.fetchone()
    except (Error, RuntimeError):
        app.logger.exception("Could not load food allocations from MySQL.")
        return (
            "Could not connect to the database. Check the MySQL service and "
            "database settings, including MYSQL_PASSWORD.",
            503,
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    return render_template(
        "allocations.html",
        allocation_data=allocation_data,
        allocation_missions=sorted(
            {(row[6], row[1]) for row in allocation_data},
            key=lambda option: option[1].lower(),
        ),
        allocation_foods=sorted(
            {(row[7], row[3]) for row in allocation_data},
            key=lambda option: option[1].lower(),
        ),
        total_allocations=total_allocations,
        total_allocated=total_allocated,
        allocated_missions=allocated_missions,
        added=request.args.get("added") == "1",
        updated=request.args.get("updated") == "1",
        deleted=request.args.get("deleted") == "1",
        action_error=request.args.get("action_error"),
    )


@app.route("/add-allocation", methods=["GET", "POST"])
@staff_or_above
def add_allocation():
    connection = None
    cursor = None
    form_data = request.form.to_dict() if request.method == "POST" else {}
    errors = []

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT mission_id, mission_name FROM missions ORDER BY mission_name"
        )
        missions_data = cursor.fetchall()
        cursor.execute(
            "SELECT food_id, food_name FROM food_items ORDER BY food_name"
        )
        foods_data = cursor.fetchall()
        cursor.execute(
            """
            SELECT a.astronaut_id, a.astronaut_name, a.mission_id, m.mission_name
            FROM astronauts a
            JOIN missions m ON a.mission_id = m.mission_id
            ORDER BY astronaut_name
            """
        )
        astronauts_data = cursor.fetchall()

        if request.method == "POST":
            try:
                mission_id = int(form_data.get("mission_id", ""))
                if mission_id not in {row[0] for row in missions_data}:
                    raise ValueError
            except ValueError:
                errors.append("Select a valid mission.")
                mission_id = 0

            try:
                food_id = int(form_data.get("food_id", ""))
                if food_id not in {row[0] for row in foods_data}:
                    raise ValueError
            except ValueError:
                errors.append("Select a valid food item.")
                food_id = 0

            try:
                astronaut_id = int(form_data.get("astronaut_id", ""))
                astronaut_missions = {
                    row[0]: row[2] for row in astronauts_data
                }
                if astronaut_missions.get(astronaut_id) != mission_id:
                    raise ValueError
            except ValueError:
                errors.append("Select an astronaut assigned to the chosen mission.")
                astronaut_id = 0

            try:
                quantity = int(form_data.get("quantity", ""))
                if quantity < 1 or quantity > 2147483647:
                    raise ValueError
            except ValueError:
                errors.append("Quantity must be a whole number greater than zero.")
                quantity = 0

            try:
                allocation_date = date.fromisoformat(
                    form_data.get("allocation_date", "")
                )
            except ValueError:
                errors.append("Enter a valid allocation date.")
                allocation_date = None

            if not missions_data:
                errors.append("Add a mission before creating an allocation.")
            if not foods_data:
                errors.append("Add a food item before creating an allocation.")
            if not astronauts_data:
                errors.append("Add an astronaut before creating an allocation.")

            if not errors:
                cursor.execute(
                    "SELECT quantity FROM inventory WHERE food_id = %s FOR UPDATE",
                    (food_id,),
                )
                inventory_row = cursor.fetchone()
                if inventory_row is None:
                    errors.append(
                        "This food item has no inventory record. Add its inventory before creating an allocation."
                    )
                elif quantity > inventory_row[0]:
                    errors.append(
                        f"Insufficient stock: available stock is {inventory_row[0]}, "
                        f"but the requested quantity is {quantity}."
                    )

            if not errors:
                cursor.execute(
                    """
                    INSERT INTO food_allocation
                        (mission_id, food_id, astronaut_id, quantity, allocation_date)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        mission_id,
                        food_id,
                        astronaut_id,
                        quantity,
                        allocation_date,
                    ),
                )
                cursor.execute(
                    """
                    UPDATE inventory
                    SET quantity = quantity - %s
                    WHERE food_id = %s
                    """,
                    (quantity, food_id),
                )
                connection.commit()
                flash("Food allocation added successfully.", "success")
                return redirect(url_for("allocations"))
            connection.rollback()
    except (Error, RuntimeError):
        if connection is not None:
            connection.rollback()
        app.logger.exception("Could not load allocation choices or create allocation.")
        return (
            "Could not save the food allocation. Check the database connection and try again.",
            503,
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    return (
        render_template(
            "add_allocation.html",
            missions=missions_data,
            foods=foods_data,
            astronauts=astronauts_data,
            form_data=form_data,
            errors=errors,
        ),
        400 if errors else 200,
    )


@app.route("/edit-allocation/<int:allocation_id>", methods=["GET", "POST"])
@manager_required
def edit_allocation(allocation_id):
    connection = None
    cursor = None
    form_data = request.form.to_dict() if request.method == "POST" else None
    errors = []

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT mission_id, mission_name FROM missions ORDER BY mission_name"
        )
        missions_data = cursor.fetchall()
        cursor.execute("SELECT food_id, food_name FROM food_items ORDER BY food_name")
        foods_data = cursor.fetchall()
        cursor.execute(
            """
            SELECT a.astronaut_id, a.astronaut_name, a.mission_id, m.mission_name
            FROM astronauts a
            JOIN missions m ON a.mission_id = m.mission_id
            ORDER BY astronaut_name
            """
        )
        astronauts_data = cursor.fetchall()
        cursor.execute(
            """
            SELECT allocation_id, mission_id, food_id, astronaut_id,
                   quantity, allocation_date
            FROM food_allocation
            WHERE allocation_id = %s
            """,
            (allocation_id,),
        )
        allocation = cursor.fetchone()
        if allocation is None:
            return "Food allocation not found.", 404

        if request.method == "POST":
            try:
                mission_id = int(form_data.get("mission_id", ""))
                if mission_id not in {row[0] for row in missions_data}:
                    raise ValueError
            except ValueError:
                errors.append("Select a valid mission.")
                mission_id = 0

            try:
                food_id = int(form_data.get("food_id", ""))
                if food_id not in {row[0] for row in foods_data}:
                    raise ValueError
            except ValueError:
                errors.append("Select a valid food item.")
                food_id = 0

            try:
                astronaut_id = int(form_data.get("astronaut_id", ""))
                astronaut_missions = {row[0]: row[2] for row in astronauts_data}
                if astronaut_missions.get(astronaut_id) != mission_id:
                    raise ValueError
            except ValueError:
                errors.append("Select an astronaut assigned to the chosen mission.")
                astronaut_id = 0

            try:
                quantity = int(form_data.get("quantity", ""))
                if quantity < 1 or quantity > 2147483647:
                    raise ValueError
            except ValueError:
                errors.append("Quantity must be a whole number greater than zero.")
                quantity = 0

            try:
                allocation_date = date.fromisoformat(
                    form_data.get("allocation_date", "")
                )
            except ValueError:
                errors.append("Enter a valid allocation date.")
                allocation_date = None

            if not errors:
                cursor.execute(
                    """
                    SELECT food_id, quantity
                    FROM food_allocation
                    WHERE allocation_id = %s
                    FOR UPDATE
                    """,
                    (allocation_id,),
                )
                old_allocation = cursor.fetchone()
                if old_allocation is None:
                    errors.append("This allocation no longer exists.")
                else:
                    old_food_id, old_quantity = old_allocation
                    affected_food_ids = sorted({old_food_id, food_id})
                    inventory_quantities = {}
                    for affected_food_id in affected_food_ids:
                        cursor.execute(
                            """
                            SELECT quantity
                            FROM inventory
                            WHERE food_id = %s
                            FOR UPDATE
                            """,
                            (affected_food_id,),
                        )
                        inventory_row = cursor.fetchone()
                        if inventory_row is not None:
                            inventory_quantities[affected_food_id] = inventory_row[0]

                    if old_food_id not in inventory_quantities:
                        errors.append(
                            "The original food item has no inventory record."
                        )
                    if food_id not in inventory_quantities:
                        errors.append(
                            "The selected food item has no inventory record."
                        )

                    if not errors:
                        old_available = inventory_quantities[old_food_id]
                        old_restored = old_available + old_quantity
                        if old_restored > 2147483647:
                            errors.append(
                                "Restoring the original allocation would exceed "
                                "the maximum inventory quantity."
                            )

                        if old_food_id == food_id:
                            if quantity > old_restored:
                                errors.append(
                                    f"Insufficient stock: available stock after "
                                    f"restoring this allocation is {old_restored}, "
                                    f"but the requested quantity is {quantity}."
                                )
                        else:
                            new_available = inventory_quantities[food_id]
                            if quantity > new_available:
                                errors.append(
                                    f"Insufficient stock: available stock is "
                                    f"{new_available}, but the requested quantity "
                                    f"is {quantity}."
                                )

                    if not errors:
                        if old_food_id == food_id:
                            cursor.execute(
                                """
                                UPDATE inventory
                                SET quantity = quantity + %s - %s
                                WHERE food_id = %s
                                """,
                                (old_quantity, quantity, old_food_id),
                            )
                        else:
                            cursor.execute(
                                """
                                UPDATE inventory
                                SET quantity = quantity + %s
                                WHERE food_id = %s
                                """,
                                (old_quantity, old_food_id),
                            )
                            cursor.execute(
                                """
                                UPDATE inventory
                                SET quantity = quantity - %s
                                WHERE food_id = %s
                                """,
                                (quantity, food_id),
                            )

                        cursor.execute(
                            """
                            UPDATE food_allocation
                            SET mission_id = %s,
                                food_id = %s,
                                astronaut_id = %s,
                                quantity = %s,
                                allocation_date = %s
                            WHERE allocation_id = %s
                            """,
                            (
                                mission_id,
                                food_id,
                                astronaut_id,
                                quantity,
                                allocation_date,
                                allocation_id,
                            ),
                        )
                        connection.commit()
                        flash("Food allocation updated successfully.", "success")
                        return redirect(url_for("allocations"))

            connection.rollback()
    except (Error, RuntimeError):
        if connection is not None:
            connection.rollback()
        app.logger.exception("Could not load or update allocation %s.", allocation_id)
        return (
            "Could not update the food allocation. Check the database connection and try again.",
            503,
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    if form_data is None:
        form_data = {
            "mission_id": str(allocation[1]),
            "food_id": str(allocation[2]),
            "astronaut_id": str(allocation[3]),
            "quantity": str(allocation[4]),
            "allocation_date": allocation[5].isoformat(),
        }

    return (
        render_template(
            "edit_allocation.html",
            missions=missions_data,
            foods=foods_data,
            astronauts=astronauts_data,
            form_data=form_data,
            errors=errors,
        ),
        400 if errors else 200,
    )


@app.route("/delete-allocation/<int:allocation_id>", methods=["POST"])
@manager_required
def delete_allocation(allocation_id):
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT food_id, quantity
            FROM food_allocation
            WHERE allocation_id = %s
            FOR UPDATE
            """,
            (allocation_id,),
        )
        allocation = cursor.fetchone()
        if allocation is None:
            connection.rollback()
            return redirect(url_for("allocations", action_error="not_found"))

        food_id, quantity = allocation
        cursor.execute(
            """
            SELECT quantity
            FROM inventory
            WHERE food_id = %s
            FOR UPDATE
            """,
            (food_id,),
        )
        inventory_row = cursor.fetchone()
        if inventory_row is None:
            connection.rollback()
            app.logger.error(
                "Cannot delete allocation %s: inventory record for food %s is missing.",
                allocation_id,
                food_id,
            )
            return redirect(
                url_for("allocations", action_error="inventory_missing")
            )
        if inventory_row[0] > 2147483647 - quantity:
            connection.rollback()
            return redirect(url_for("allocations", action_error="quantity_overflow"))

        cursor.execute(
            "UPDATE inventory SET quantity = quantity + %s WHERE food_id = %s",
            (quantity, food_id),
        )
        cursor.execute(
            "DELETE FROM food_allocation WHERE allocation_id = %s",
            (allocation_id,),
        )
        if cursor.rowcount == 0:
            connection.rollback()
            return redirect(url_for("allocations", action_error="not_found"))

        connection.commit()
        flash("Food allocation deleted successfully.", "success")
        return redirect(url_for("allocations"))
    except (Error, RuntimeError):
        if connection is not None:
            connection.rollback()
        app.logger.exception("Could not delete allocation %s.", allocation_id)
        return redirect(url_for("allocations", action_error="failed"))
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/transactions")
@staff_or_above
def transactions():
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                st.transaction_id,
                f.food_name,
                st.transaction_type,
                st.quantity,
                st.transaction_date,
                st.remarks
            FROM stock_transactions st
            JOIN food_items f ON st.food_id = f.food_id
            ORDER BY st.transaction_date DESC
            """
        )
        transaction_data = cursor.fetchall()
        cursor.execute(
            """
            SELECT
                COUNT(*),
                COALESCE(SUM(CASE WHEN transaction_type = %s THEN quantity ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN transaction_type IN (%s, %s) THEN quantity ELSE 0 END), 0)
            FROM stock_transactions
            """,
            ("IN", "OUT", "WASTAGE"),
        )
        total_transactions, total_in, total_out = cursor.fetchone()
    except (Error, RuntimeError):
        app.logger.exception("Could not load stock transactions from MySQL.")
        return (
            "Could not connect to the database. Check the MySQL service and "
            "database settings, including MYSQL_PASSWORD.",
            503,
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    return render_template(
        "transactions.html",
        transaction_data=transaction_data,
        total_transactions=total_transactions,
        total_in=total_in,
        total_out=total_out,
        added=request.args.get("added") == "1",
    )


@app.route("/add-transaction", methods=["GET", "POST"])
@staff_or_above
def add_transaction():
    connection = None
    cursor = None
    form_data = request.form.to_dict() if request.method == "POST" else {}
    errors = []
    transaction_types = {
        "IN": "Stock Received",
        "OUT": "Food Issued",
        "RETURN": "Food Returned",
        "WASTAGE": "Damaged/Expired",
    }

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT food_id, food_name FROM food_items ORDER BY food_name")
        foods_data = cursor.fetchall()

        if request.method == "POST":
            try:
                food_id = int(form_data.get("food_id", ""))
                if food_id not in {row[0] for row in foods_data}:
                    raise ValueError
            except ValueError:
                errors.append("Select a valid food item.")
                food_id = 0

            transaction_type = form_data.get("transaction_type", "")
            if transaction_type not in transaction_types:
                errors.append("Select a valid transaction type.")

            try:
                quantity = int(form_data.get("quantity", ""))
                if quantity < 1 or quantity > 2147483647:
                    raise ValueError
            except ValueError:
                errors.append("Quantity must be a whole number greater than zero.")
                quantity = 0

            remarks = form_data.get("remarks", "").strip()
            if len(remarks) > 255:
                errors.append("Remarks must be 255 characters or fewer.")

            if not foods_data:
                errors.append("Add a food item before recording a transaction.")

            current_quantity = None
            if not errors:
                cursor.execute(
                    "SELECT quantity FROM inventory WHERE food_id = %s FOR UPDATE",
                    (food_id,),
                )
                inventory_row = cursor.fetchone()
                if inventory_row is None:
                    errors.append(
                        "This food item has no inventory record. Add its inventory before recording a transaction."
                    )
                else:
                    current_quantity = inventory_row[0]
                    if transaction_type in {"OUT", "WASTAGE"} and quantity > current_quantity:
                        errors.append(
                            f"Insufficient stock: only {current_quantity} units are available."
                        )
                    elif (
                        transaction_type in {"IN", "RETURN"}
                        and current_quantity > 2147483647 - quantity
                    ):
                        errors.append("This transaction would exceed the maximum inventory quantity.")

            if not errors:
                cursor.execute(
                    """
                    INSERT INTO stock_transactions
                        (food_id, transaction_type, quantity, remarks)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (food_id, transaction_type, quantity, remarks or None),
                )
                if transaction_type in {"IN", "RETURN"}:
                    cursor.execute(
                        """
                        UPDATE inventory
                        SET quantity = quantity + %s
                        WHERE food_id = %s
                        """,
                        (quantity, food_id),
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE inventory
                        SET quantity = quantity - %s
                        WHERE food_id = %s
                        """,
                        (quantity, food_id),
                    )
                connection.commit()
                flash("Stock transaction recorded successfully.", "success")
                return redirect(url_for("transactions"))
            connection.rollback()
    except (Error, RuntimeError):
        if connection is not None:
            connection.rollback()
        app.logger.exception("Could not load food choices or create stock transaction.")
        return (
            "Could not save the stock transaction. Check the database connection and try again.",
            503,
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    return (
        render_template(
            "add_transaction.html",
            foods=foods_data,
            form_data=form_data,
            errors=errors,
            transaction_types=transaction_types,
        ),
        400 if errors else 200,
    )


@app.errorhandler(403)
def forbidden(_error):
    return render_template("403.html"), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(_error):
    return render_template("500.html"), 500


if __name__ == "__main__":
    if not os.environ.get("MYSQL_PASSWORD"):
        os.environ["MYSQL_PASSWORD"] = getpass("MySQL password (input hidden): ")
    flask_secret = os.environ.get("FLASK_SECRET_KEY") or os.environ.get("SECRET_KEY")
    if not flask_secret:
        os.environ["FLASK_SECRET_KEY"] = getpass(
            "Flask session secret (input hidden; use a random 32+ character value): "
        )
        flask_secret = os.environ["FLASK_SECRET_KEY"]
    app.secret_key = flask_secret
    if len(app.secret_key) < 32:
        raise RuntimeError("FLASK_SECRET_KEY must be at least 32 characters long.")
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
