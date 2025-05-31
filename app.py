# app.py
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user, UserMixin
)
from passlib.context import CryptContext
from decimal import Decimal, InvalidOperation

from database import db
from config import settings

app = Flask(__name__)
app.secret_key = settings.SECRET_KEY

# Делаем настройки доступными в Jinja2
app.jinja_env.globals['settings'] = settings

# Настройка Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = "login"

# Passlib для bcrypt
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ----------------- Модель пользователя -----------------
class User(UserMixin):
    def __init__(self, id, username, password_hash, role):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    row = db.fetchone(
        "SELECT id, username, password_hash, role FROM users WHERE id=%s",
        user_id
    )
    if not row:
        return None
    return User(row['id'], row['username'], row['password_hash'], row['role'])

# ------------------ Декоратор ролей ------------------
def roles_required(*roles):
    def decorator(f):
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                flash("Доступ запрещён", "warning")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        wrapped.__name__ = f.__name__
        return wrapped
    return decorator

# -------------------- /login --------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = db.fetchone(
            "SELECT id, username, password_hash, role FROM users WHERE username=%s",
            request.form['username']
        )
        if u and pwd_ctx.verify(request.form['password'], u['password_hash']):
            user = User(u['id'], u['username'], u['password_hash'], u['role'])
            login_user(user)
            return redirect(request.args.get('next') or url_for('dashboard'))
        flash("Неверный логин или пароль", "danger")
    return render_template("login.html")

# -------------------- /logout --------------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# -------------------- Dashboard --------------------
@app.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html", user=current_user)

# ------------------ Estimates ------------------
@app.route("/estimates")
@login_required
@roles_required(*settings.ESTIMATE_VIEW)
def estimates():
    q = request.args.get("q", "").strip()
    if q:
        pattern = f"%{q}%"
        items = db.fetchall(
            "SELECT * FROM psd.estimate_documentation "
            "WHERE work_expense_name ILIKE %s OR price_code_resource_codes ILIKE %s",
            pattern, pattern
        )
    else:
        items = db.fetchall("SELECT * FROM psd.estimate_documentation")
    return render_template("estimates.html", items=items, q=q)

@app.route("/estimate/add", methods=["POST"])
@login_required
@roles_required(*settings.ESTIMATE_EDIT)
def estimate_add():
    d = request.form
    required_fields = ['price_code', 'name', 'unit', 'quantity', 'price', 'base', 'total']
    for fld in required_fields:
        if not d.get(fld):
            flash(f"Поле «{fld}» обязательно для заполнения.", "error")
            return redirect(url_for("estimates"))

    if len(d['price_code']) > 100:
        flash("Код ресурса слишком длинный (максимум 100).", "error")
        return redirect(url_for("estimates"))
    if len(d['name']) > 300:
        flash("Наименование работ слишком длинное (максимум 300).", "error")
        return redirect(url_for("estimates"))
    if len(d['unit']) > 50:
        flash("Ед. изм. слишком длинная (максимум 50).", "error")
        return redirect(url_for("estimates"))

    try:
        quantity = Decimal(d['quantity'])
        unit_price = Decimal(d['price'])
        base_cost = Decimal(d['base'])
        total_cost = Decimal(d['total'])
    except (InvalidOperation, ValueError):
        flash("Некорректное числовое значение.", "error")
        return redirect(url_for("estimates"))

    if quantity < 0 or unit_price < 0 or base_cost < 0 or total_cost < 0:
        flash("Числовые поля не могут быть отрицательными.", "error")
        return redirect(url_for("estimates"))

    try:
        db.execute(
            "INSERT INTO psd.estimate_documentation "
            "(price_code_resource_codes, work_expense_name, unit_of_measurement, quantity,"
            " unit_price_rub, adjustment_coefficients, winter_increase_coefficients,"
            " total_base_cost_rub, recalc_indices_standards, total_current_cost_rub) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            d['price_code'], d['name'], d['unit'], quantity,
            unit_price, d.get('adjust'), d.get('winter'),
            base_cost, d.get('indices'), total_cost
        )
        flash("Запись успешно добавлена.", "success")
    except Exception as e:
        db.conn.rollback()
        flash(f"Ошибка при вставке: {e}", "error")
    return redirect(url_for("estimates"))

@app.route("/estimate/delete/<int:estimate_id>")
@login_required
@roles_required(*settings.ESTIMATE_EDIT)
def estimate_delete(estimate_id):
    try:
        db.execute("DELETE FROM psd.estimate_documentation WHERE estimate_id=%s", estimate_id)
        flash("Запись удалена.", "success")
    except Exception as e:
        db.conn.rollback()
        flash(f"Ошибка при удалении: {e}", "error")
    return redirect(url_for("estimates"))

# ------------------ Materials specification ------------------
@app.route("/materials")
@login_required
@roles_required(*settings.MATERIALS_VIEW)
def materials():
    q = request.args.get("q", "").strip()
    if q:
        pattern = f"%{q}%"
        items = db.fetchall(
            "SELECT * FROM psd.main_materials_equipment "
            "WHERE name_technical_specification ILIKE %s OR type_brand_size ILIKE %s",
            pattern, pattern
        )
    else:
        items = db.fetchall("SELECT * FROM psd.main_materials_equipment")
    return render_template("materials.html", items=items, q=q)

@app.route("/material/add", methods=["POST"])
@login_required
@roles_required(*settings.MATERIALS_EDIT)
def material_add():
    d = request.form
    required = ['estimate_id', 'name', 'type', 'unit', 'quantity', 'location']
    for fld in required:
        if not d.get(fld):
            flash(f"Поле «{fld}» обязательно для заполнения.", "error")
            return redirect(url_for("materials"))

    try:
        estimate_id = int(d['estimate_id'])
    except ValueError:
        flash("Estimate ID должен быть целым числом.", "error")
        return redirect(url_for("materials"))

    if estimate_id <= 0:
        flash("Estimate ID должен быть положительным.", "error")
        return redirect(url_for("materials"))

    exists = db.fetchone(
        "SELECT 1 FROM psd.estimate_documentation WHERE estimate_id=%s",
        estimate_id
    )
    if not exists:
        flash(f"Сметы с ID={estimate_id} не существует.", "error")
        return redirect(url_for("materials"))

    if len(d['name']) > 300:
        flash("Тех. спецификация слишком длинная (до 300).", "error")
        return redirect(url_for("materials"))
    if len(d['type']) > 100:
        flash("Тип/Марка/Размер слишком длинные (до 100).", "error")
        return redirect(url_for("materials"))
    if len(d['unit']) > 50:
        flash("Ед. изм. слишком длинная (до 50).", "error")
        return redirect(url_for("materials"))

    try:
        quantity = Decimal(d['quantity'])
    except (InvalidOperation, ValueError):
        flash("Некорректное значение «quantity».", "error")
        return redirect(url_for("materials"))

    if quantity < 0:
        flash("Количество не может быть отрицательным.", "error")
        return redirect(url_for("materials"))

    try:
        db.execute(
            "INSERT INTO psd.main_materials_equipment "
            "(estimate_id, name_technical_specification, type_brand_size, unit_of_measurement,"
            " quantity, installation_location_method) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            estimate_id, d['name'], d['type'], d['unit'], quantity, d['location']
        )
        flash("Запись успешно добавлена.", "success")
    except Exception as e:
        db.conn.rollback()
        flash(f"Ошибка при вставке: {e}", "error")
    return redirect(url_for("materials"))

@app.route("/material/delete/<int:material_equipment_id>")
@login_required
@roles_required(*settings.MATERIALS_EDIT)
def material_delete(material_equipment_id):
    try:
        db.execute("DELETE FROM psd.main_materials_equipment WHERE material_equipment_id=%s", material_equipment_id)
        flash("Запись удалена.", "success")
    except Exception as e:
        db.conn.rollback()
        flash(f"Ошибка при удалении: {e}", "error")
    return redirect(url_for("materials"))

# ------------------ Materials reference ------------------
@app.route("/materials_ref")
@login_required
@roles_required(*settings.MATERIALS_REF_VIEW)
def materials_ref():
    q = request.args.get("q", "").strip()
    if q:
        pattern = f"%{q}%"
        items = db.fetchall(
            "SELECT * FROM materials_equipment WHERE name ILIKE %s OR supplier ILIKE %s",
            pattern, pattern
        )
    else:
        items = db.fetchall("SELECT * FROM materials_equipment")
    return render_template("materials_ref.html", items=items, q=q)

@app.route("/materials_ref/add", methods=["POST"])
@login_required
@roles_required(*settings.MATERIALS_REF_EDIT)
def materials_ref_add():
    d = request.form
    required = ['name', 'type_brand_size', 'unit_of_measurement', 'quantity']
    for fld in required:
        if not d.get(fld):
            flash(f"Поле «{fld}» обязательно для заполнения.", "error")
            return redirect(url_for("materials_ref"))

    if len(d['name']) > 300:
        flash("Наименование слишком длинное (до 300).", "error")
        return redirect(url_for("materials_ref"))
    if len(d['type_brand_size']) > 100:
        flash("Тип/Марка/Размер слишком длинные (до 100).", "error")
        return redirect(url_for("materials_ref"))
    if len(d['unit_of_measurement']) > 50:
        flash("Ед. изм. слишком длинная (до 50).", "error")
        return redirect(url_for("materials_ref"))

    try:
        quantity = Decimal(d['quantity'])
    except (InvalidOperation, ValueError):
        flash("Некорректное значение «quantity».", "error")
        return redirect(url_for("materials_ref"))

    if quantity < 0:
        flash("Количество не может быть отрицательным.", "error")
        return redirect(url_for("materials_ref"))

    if d.get('supplier') and len(d['supplier']) > 200:
        flash("Поставщик слишком длинный (до 200).", "error")
        return redirect(url_for("materials_ref"))

    unit_cost = None
    if d.get('unit_cost_rub'):
        try:
            unit_cost = Decimal(d['unit_cost_rub'])
            if unit_cost < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            flash("Некорректное значение «unit_cost_rub».", "error")
            return redirect(url_for("materials_ref"))

    total_cost = None
    if d.get('total_cost_rub'):
        try:
            total_cost = Decimal(d['total_cost_rub'])
            if total_cost < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            flash("Некорректное значение «total_cost_rub».", "error")
            return redirect(url_for("materials_ref"))

    if d.get('storage_location') and len(d['storage_location']) > 200:
        flash("Местоположение слишком длинное (до 200).", "error")
        return redirect(url_for("materials_ref"))

    try:
        db.execute(
            "INSERT INTO materials_equipment "
            "(name, type_brand_size, unit_of_measurement, quantity, supplier, unit_cost_rub, total_cost_rub, storage_location) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            d['name'], d['type_brand_size'], d['unit_of_measurement'],
            quantity, d.get('supplier'), unit_cost, total_cost, d.get('storage_location')
        )
        flash("Запись успешно добавлена.", "success")
    except Exception as e:
        db.conn.rollback()
        flash(f"Ошибка при вставке: {e}", "error")
    return redirect(url_for("materials_ref"))

@app.route("/materials_ref/delete/<int:material_equipment_id>")
@login_required
@roles_required(*settings.MATERIALS_REF_EDIT)
def materials_ref_delete(material_equipment_id):
    try:
        db.execute("DELETE FROM materials_equipment WHERE material_equipment_id=%s", material_equipment_id)
        flash("Запись удалена.", "success")
    except Exception as e:
        db.conn.rollback()
        flash(f"Ошибка при удалении: {e}", "error")
    return redirect(url_for("materials_ref"))

# ------------------ Mechanisms specification ------------------
@app.route("/mechanisms")
@login_required
@roles_required(*settings.MECHANISMS_VIEW)
def mechanisms():
    q = request.args.get("q", "").strip()
    if q:
        pattern = f"%{q}%"
        items = db.fetchall(
            "SELECT * FROM psd.main_mechanisms WHERE mechanism_name ILIKE %s OR location ILIKE %s",
            pattern, pattern
        )
    else:
        items = db.fetchall("SELECT * FROM psd.main_mechanisms")
    return render_template("mechanisms.html", items=items, q=q)

@app.route("/mechanism/add", methods=["POST"])
@login_required
@roles_required(*settings.MECHANISMS_EDIT)
def mechanism_add():
    d = request.form
    required = ['estimate_id', 'name', 'type', 'quantity', 'location']
    for fld in required:
        if not d.get(fld):
            flash(f"Поле «{fld}» обязательно для заполнения.", "error")
            return redirect(url_for("mechanisms"))

    try:
        estimate_id = int(d['estimate_id'])
    except ValueError:
        flash("Estimate ID должен быть целым числом.", "error")
        return redirect(url_for("mechanisms"))

    if estimate_id <= 0:
        flash("Estimate ID должен быть положительным.", "error")
        return redirect(url_for("mechanisms"))

    exists = db.fetchone(
        "SELECT 1 FROM psd.estimate_documentation WHERE estimate_id=%s",
        estimate_id
    )
    if not exists:
        flash(f"Сметы с ID={estimate_id} не существует.", "error")
        return redirect(url_for("mechanisms"))

    if len(d['name']) > 300:
        flash("Название механизма слишком длинное (до 300).", "error")
        return redirect(url_for("mechanisms"))
    if len(d['type']) > 100:
        flash("Тип/Марка/Грузоподъемность слишком длинные (до 100).", "error")
        return redirect(url_for("mechanisms"))

    try:
        qty = int(d['quantity'])
    except ValueError:
        flash("Количество должно быть целым числом.", "error")
        return redirect(url_for("mechanisms"))

    if qty < 0:
        flash("Количество не может быть отрицательным.", "error")
        return redirect(url_for("mechanisms"))
    if len(d['location']) > 200:
        flash("Локация слишком длинная (до 200).", "error")
        return redirect(url_for("mechanisms"))

    try:
        db.execute(
            "INSERT INTO psd.main_mechanisms "
            "(estimate_id, mechanism_name, type_brand_load_capacity, quantity, location) "
            "VALUES (%s,%s,%s,%s,%s)",
            estimate_id, d['name'], d['type'], qty, d['location']
        )
        flash("Запись успешно добавлена.", "success")
    except Exception as e:
        db.conn.rollback()
        flash(f"Ошибка при вставке: {e}", "error")
    return redirect(url_for("mechanisms"))

@app.route("/mechanism/delete/<int:mechanism_id>")
@login_required
@roles_required(*settings.MECHANISMS_EDIT)
def mechanism_delete(mechanism_id):
    try:
        db.execute("DELETE FROM psd.main_mechanisms WHERE mechanism_id=%s", mechanism_id)
        flash("Запись удалена.", "success")
    except Exception as e:
        db.conn.rollback()
        flash(f"Ошибка при удалении: {e}", "error")
    return redirect(url_for("mechanisms"))

# ------------------ Mechanisms reference ------------------
@app.route("/mechanisms_ref")
@login_required
@roles_required(*settings.MECHANISMS_REF_VIEW)
def mechanisms_ref():
    q = request.args.get("q", "").strip()
    if q:
        pattern = f"%{q}%"
        items = db.fetchall(
            "SELECT * FROM mechanisms WHERE mechanism_name ILIKE %s OR type_brand_load_capacity ILIKE %s",
            pattern, pattern
        )
    else:
        items = db.fetchall("SELECT * FROM mechanisms")
    return render_template("mechanisms_ref.html", items=items, q=q)

@app.route("/mechanisms_ref/add", methods=["POST"])
@login_required
@roles_required(*settings.MECHANISMS_REF_EDIT)
def mechanisms_ref_add():
    d = request.form
    required = ['mechanism_name', 'type_brand_load_capacity', 'stock_quantity']
    for fld in required:
        if not d.get(fld):
            flash(f"Поле «{fld}» обязательно для заполнения.", "error")
            return redirect(url_for("mechanisms_ref"))

    if len(d['mechanism_name']) > 300:
        flash("Название механизма слишком длинное (до 300).", "error")
        return redirect(url_for("mechanisms_ref"))
    if len(d['type_brand_load_capacity']) > 100:
        flash("Тип/Марка/Грузоподъемность слишком длинные (до 100).", "error")
        return redirect(url_for("mechanisms_ref"))

    try:
        stock_q = int(d['stock_quantity'])
    except ValueError:
        flash("stock_quantity должен быть целым числом.", "error")
        return redirect(url_for("mechanisms_ref"))

    if stock_q < 0:
        flash("stock_quantity не может быть отрицательным.", "error")
        return redirect(url_for("mechanisms_ref"))

    if d.get('storage_location') and len(d['storage_location']) > 200:
        flash("storage_location слишком длинное (до 200).", "error")
        return redirect(url_for("mechanisms_ref"))

    site_q = None
    if d.get('site_quantity'):
        try:
            site_q = int(d['site_quantity'])
        except ValueError:
            flash("site_quantity должен быть целым числом.", "error")
            return redirect(url_for("mechanisms_ref"))
        if site_q < 0:
            flash("site_quantity не может быть отрицательным.", "error")
            return redirect(url_for("mechanisms_ref"))

    stock_r = None
    if d.get('stock_remaining'):
        try:
            stock_r = int(d['stock_remaining'])
        except ValueError:
            flash("stock_remaining должен быть целым числом.", "error")
            return redirect(url_for("mechanisms_ref"))
        if stock_r < 0:
            flash("stock_remaining не может быть отрицательным.", "error")
            return redirect(url_for("mechanisms_ref"))

    try:
        db.execute(
            "INSERT INTO mechanisms "
            "(mechanism_name, type_brand_load_capacity, stock_quantity, storage_location, site_quantity, stock_remaining) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            d['mechanism_name'], d['type_brand_load_capacity'], stock_q,
            d.get('storage_location'), site_q, stock_r
        )
        flash("Запись успешно добавлена.", "success")
    except Exception as e:
        db.conn.rollback()
        flash(f"Ошибка при вставке: {e}", "error")
    return redirect(url_for("mechanisms_ref"))

@app.route("/mechanisms_ref/delete/<int:mechanism_id>")
@login_required
@roles_required(*settings.MECHANISMS_REF_EDIT)
def mechanisms_ref_delete(mechanism_id):
    try:
        db.execute("DELETE FROM mechanisms WHERE mechanism_id=%s", mechanism_id)
        flash("Запись удалена.", "success")
    except Exception as e:
        db.conn.rollback()
        flash(f"Ошибка при удалении: {e}", "error")
    return redirect(url_for("mechanisms_ref"))

# ------------------ Work volumes ------------------
@app.route("/work_volumes")
@login_required
@roles_required(*settings.WORK_VOLUMES_VIEW)
def work_volumes():
    q = request.args.get("q", "").strip()
    if q:
        pattern = f"%{q}%"
        items = db.fetchall(
            "SELECT * FROM psd.work_volumes WHERE work_name ILIKE %s OR notes ILIKE %s",
            pattern, pattern
        )
    else:
        items = db.fetchall("SELECT * FROM psd.work_volumes")
    return render_template("work_volumes.html", items=items, q=q)

@app.route("/work_volume/add", methods=["POST"])
@login_required
@roles_required(*settings.WORK_VOLUMES_EDIT)
def work_volume_add():
    d = request.form
    required = ['name', 'unit', 'quantity']
    for fld in required:
        if not d.get(fld):
            flash(f"Поле «{fld}» обязательно для заполнения.", "error")
            return redirect(url_for("work_volumes"))

    if len(d['name']) > 300:
        flash("Наименование работы слишком длинное (до 300).", "error")
        return redirect(url_for("work_volumes"))
    if len(d['unit']) > 50:
        flash("Ед. изм. слишком длинная (до 50).", "error")
        return redirect(url_for("work_volumes"))

    try:
        quantity = Decimal(d['quantity'])
    except (InvalidOperation, ValueError):
        flash("Некорректное значение «quantity».", "error")
        return redirect(url_for("work_volumes"))

    if quantity < 0:
        flash("Количество не может быть отрицательным.", "error")
        return redirect(url_for("work_volumes"))

    if d.get('notes') and len(d['notes']) > 1000:
        flash("Примечания слишком длинные.", "error")
        return redirect(url_for("work_volumes"))

    try:
        db.execute(
            "INSERT INTO psd.work_volumes "
            "(work_name, unit_of_measurement, quantity, notes) "
            "VALUES (%s,%s,%s,%s)",
            d['name'], d['unit'], quantity, d.get('notes')
        )
        flash("Запись успешно добавлена.", "success")
    except Exception as e:
        db.conn.rollback()
        flash(f"Ошибка при вставке: {e}", "error")
    return redirect(url_for("work_volumes"))

@app.route("/work_volume/delete/<int:work_id>")
@login_required
@roles_required(*settings.WORK_VOLUMES_EDIT)
def work_volume_delete(work_id):
    try:
        db.execute("DELETE FROM psd.work_volumes WHERE work_id=%s", work_id)
        flash("Запись удалена.", "success")
    except Exception as e:
        db.conn.rollback()
        flash(f"Ошибка при удалении: {e}", "error")
    return redirect(url_for("work_volumes"))

# -------- Билдеры / спец (builders_specialists) --------
@app.route("/builders_specialists")
@login_required
@roles_required(*settings.BUILDERS_SPECIALISTS_VIEW)
def builders_specialists():
    q = request.args.get("q", "").strip()
    if q:
        pattern = f"%{q}%"
        items = db.fetchall(
            "SELECT * FROM builders_specialists WHERE full_name ILIKE %s OR position_specialty ILIKE %s",
            pattern, pattern
        )
    else:
        items = db.fetchall("SELECT * FROM builders_specialists")
    return render_template("builders_specialists.html", items=items, q=q)

@app.route("/builder/add", methods=["POST"])
@login_required
@roles_required(*settings.BUILDERS_SPECIALISTS_EDIT)
def builder_add():
    d = request.form
    required = ['full_name', 'position', 'experience', 'section', 'salary']
    for fld in required:
        if not d.get(fld):
            flash(f"Поле «{fld}» обязательно для заполнения.", "error")
            return redirect(url_for("builders_specialists"))

    if len(d['full_name']) > 300:
        flash("ФИО слишком длинное (до 300).", "error")
        return redirect(url_for("builders_specialists"))
    if len(d['position']) > 100:
        flash("Специальность слишком длинная (до 100).", "error")
        return redirect(url_for("builders_specialists"))

    try:
        experience = int(d['experience'])
    except ValueError:
        flash("Опыт должен быть целым числом.", "error")
        return redirect(url_for("builders_specialists"))
    if experience < 0:
        flash("Опыт не может быть отрицательным.", "error")
        return redirect(url_for("builders_specialists"))
    if len(d['section']) > 100:
        flash("Участок слишком длинный (до 100).", "error")
        return redirect(url_for("builders_specialists"))

    try:
        salary = Decimal(d['salary'])
    except (InvalidOperation, ValueError):
        flash("Некорректное значение «salary».", "error")
        return redirect(url_for("builders_specialists"))
    if salary < 0:
        flash("Зарплата не может быть отрицательной.", "error")
        return redirect(url_for("builders_specialists"))

    try:
        db.execute(
            "INSERT INTO builders_specialists "
            "(full_name, position_specialty, experience_years, section, salary) "
            "VALUES (%s,%s,%s,%s,%s)",
            d['full_name'], d['position'], experience, d['section'], salary
        )
        flash("Запись успешно добавлена.", "success")
    except Exception as e:
        db.conn.rollback()
        flash(f"Ошибка при вставке: {e}", "error")
    return redirect(url_for("builders_specialists"))

@app.route("/builder/delete/<int:specialist_id>")
@login_required
@roles_required(*settings.BUILDERS_SPECIALISTS_EDIT)
def builder_delete(specialist_id):
    try:
        db.execute("DELETE FROM builders_specialists WHERE specialist_id=%s", specialist_id)
        flash("Запись удалена.", "success")
    except Exception as e:
        db.conn.rollback()
        flash(f"Ошибка при удалении: {e}", "error")
    return redirect(url_for("builders_specialists"))

# ----------------- ITR -----------------
@app.route("/itr")
@login_required
@roles_required(*settings.ITR_VIEW)
def itr_list():
    q = request.args.get("q", "").strip()
    if q:
        pattern = f"%{q}%"
        items = db.fetchall(
            "SELECT * FROM itr WHERE full_name ILIKE %s OR position ILIKE %s",
            pattern, pattern
        )
    else:
        items = db.fetchall("SELECT * FROM itr")
    return render_template("itr.html", items=items, q=q)

@app.route("/itr/add", methods=["POST"])
@login_required
@roles_required(*settings.ITR_EDIT)
def itr_add():
    d = request.form
    required = ['full_name', 'position', 'experience', 'section', 'salary']
    for fld in required:
        if not d.get(fld):
            flash(f"Поле «{fld}» обязательно для заполнения.", "error")
            return redirect(url_for("itr_list"))

    if len(d['full_name']) > 300:
        flash("ФИО слишком длинное (до 300).", "error")
        return redirect(url_for("itr_list"))
    if len(d['position']) > 100:
        flash("Должность слишком длинная (до 100).", "error")
        return redirect(url_for("itr_list"))

    try:
        experience = int(d['experience'])
    except ValueError:
        flash("Опыт должен быть целым числом.", "error")
        return redirect(url_for("itr_list"))
    if experience < 0:
        flash("Опыт не может быть отрицательным.", "error")
        return redirect(url_for("itr_list"))
    if len(d['section']) > 100:
        flash("Секция слишком длинная (до 100).", "error")
        return redirect(url_for("itr_list"))

    try:
        salary = Decimal(d['salary'])
    except (InvalidOperation, ValueError):
        flash("Некорректное значение «salary».", "error")
        return redirect(url_for("itr_list"))
    if salary < 0:
        flash("Зарплата не может быть отрицательной.", "error")
        return redirect(url_for("itr_list"))

    try:
        db.execute(
            "INSERT INTO itr "
            "(full_name, position, experience_years, section, salary) "
            "VALUES (%s,%s,%s,%s,%s)",
            d['full_name'], d['position'], experience, d['section'], salary
        )
        flash("Запись успешно добавлена.", "success")
    except Exception as e:
        db.conn.rollback()
        flash(f"Ошибка при вставке: {e}", "error")
    return redirect(url_for("itr_list"))

@app.route("/itr/delete/<int:worker_id>")
@login_required
@roles_required(*settings.ITR_EDIT)
def itr_delete(worker_id):
    try:
        db.execute("DELETE FROM itr WHERE worker_id=%s", worker_id)
        flash("Запись удалена.", "success")
    except Exception as e:
        db.conn.rollback()
        flash(f"Ошибка при удалении: {e}", "error")
    return redirect(url_for("itr_list"))

# ----------------- AUP -----------------
@app.route("/aup")
@login_required
@roles_required(*settings.AUP_VIEW)
def aup_list():
    q = request.args.get("q", "").strip()
    if q:
        pattern = f"%{q}%"
        items = db.fetchall(
            "SELECT * FROM aup WHERE full_name ILIKE %s OR position ILIKE %s",
            pattern, pattern
        )
    else:
        items = db.fetchall("SELECT * FROM aup")
    return render_template("aup.html", items=items, q=q)

@app.route("/aup/add", methods=["POST"])
@login_required
@roles_required(*settings.AUP_EDIT)
def aup_add():
    d = request.form
    required = ['full_name', 'position', 'experience', 'section', 'salary']
    for fld in required:
        if not d.get(fld):
            flash(f"Поле «{fld}» обязательно для заполнения.", "error")
            return redirect(url_for("aup_list"))

    if len(d['full_name']) > 300:
        flash("ФИО слишком длинное (до 300).", "error")
        return redirect(url_for("aup_list"))
    if len(d['position']) > 100:
        flash("Должность слишком длинная (до 100).", "error")
        return redirect(url_for("aup_list"))

    try:
        experience = int(d['experience'])
    except ValueError:
        flash("Опыт должен быть целым числом.", "error")
        return redirect(url_for("aup_list"))
    if experience < 0:
        flash("Опыт не может быть отрицательным.", "error")
        return redirect(url_for("aup_list"))
    if len(d['section']) > 100:
        flash("Секция слишком длинная (до 100).", "error")
        return redirect(url_for("aup_list"))

    try:
        salary = Decimal(d['salary'])
    except (InvalidOperation, ValueError):
        flash("Некорректное значение «salary».", "error")
        return redirect(url_for("aup_list"))
    if salary < 0:
        flash("Зарплата не может быть отрицательной.", "error")
        return redirect(url_for("aup_list"))

    try:
        db.execute(
            "INSERT INTO aup "
            "(full_name, position, experience_years, section, salary) "
            "VALUES (%s,%s,%s,%s,%s)",
            d['full_name'], d['position'], experience, d['section'], salary
        )
        flash("Запись успешно добавлена.", "success")
    except Exception as e:
        db.conn.rollback()
        flash(f"Ошибка при вставке: {e}", "error")
    return redirect(url_for("aup_list"))

@app.route("/aup/delete/<int:staff_id>")
@login_required
@roles_required(*settings.AUP_EDIT)
def aup_delete(staff_id):
    try:
        db.execute("DELETE FROM aup WHERE staff_id=%s", staff_id)
        flash("Запись удалена.", "success")
    except Exception as e:
        db.conn.rollback()
        flash(f"Ошибка при удалении: {e}", "error")
    return redirect(url_for("aup_list"))

if __name__ == "__main__":
    app.run(debug=True)
