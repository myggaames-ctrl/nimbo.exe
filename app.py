"""
Nimbo AI Dashboard - Backend Flask
Conecta con OpenClaw, Aronium SQLite y Gemini API
"""
import os
import sqlite3
import subprocess
import json
from functools import wraps
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from google import genai
from openclaw_bridge import send_to_openclaw, check_openclaw_status
from core.nimbo import send as nimbo_send
from services.inventory import InventoryService
from core.action_engine import ActionEngine
from core.tool_registry import list_tools
from services.skills_service import SkillsService
from services.mail_service import mail, enviar_reset_password
from core.auth import (
    init_usuarios, get_usuario_by_id, verify_login, existe_algun_usuario,
    listar_usuarios, crear_usuario, set_usuario_activo, cambiar_password_usuario,
    get_admin_activo, crear_token_reset, validar_token_reset, usar_token_reset
)
from core.configuracion import init_configuracion, get_config, set_config
import tools

load_dotenv('/home/ictor_axtor/micocina-dashboard/.env')

app = Flask(__name__)
app.secret_key = "nimbo-secret-key-2026"
CORS(app)

# ── Correo (recuperación de contraseña) ────────────────────
app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME", "")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD", "")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_USERNAME", "")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")
mail.init_app(app)

# ── Login / Roles ──────────────────────────────────────────
init_usuarios()
init_configuracion()

from database.aronium import init_cotizaciones
init_cotizaciones()

from database.aronium import init_caja
init_caja()

# Instalaciones que ya tenian usuarios antes de que existiera el wizard de
# onboarding (o que lo completaron con el /setup viejo de un solo paso) se
# marcan como completas automaticamente, para no forzar el wizard nuevo.
if existe_algun_usuario() and get_config("onboarding_completado") != "1":
    set_config("onboarding_completado", "1")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return get_usuario_by_id(user_id)


# ── Onboarding (primera instalación) ───────────────────────
ONBOARDING_PASOS = (1, 2, 3, 4, 5, 6)
_setup_completado = False


def _onboarding_completado():
    return get_config("onboarding_completado") == "1"


def _onboarding_paso_actual():
    try:
        paso = int(get_config("onboarding_step", "1"))
    except (TypeError, ValueError):
        paso = 1
    return paso if paso in ONBOARDING_PASOS else 1


@app.before_request
def require_setup():
    global _setup_completado
    if request.endpoint in ("setup", "setup_paso", "static"):
        return None
    if not _setup_completado:
        if _onboarding_completado():
            _setup_completado = True
        else:
            return redirect(url_for("setup"))


def admin_required(f):
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            return jsonify({"error": "Acceso restringido a administrador"}), 403
        return f(*args, **kwargs)
    return wrapper

# ── Configuración ──────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
ARONIUM_DB = os.environ.get(
    "ARONIUM_DB",
    "/mnt/c/Users/Victor Paxtor/AppData/Local/Aronium/Data/pos.db"
)

gemini_client = None
if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)

inventory = InventoryService()
engine = ActionEngine()
skills = SkillsService()


# ── Historial de chat en memoria ───────────────────────────
chat_history = []
nimbo_context = {}

# ══════════════════════════════════════════════════════════
# RUTAS PRINCIPALES
# ══════════════════════════════════════════════════════════

@app.route("/")
@login_required
def index():
    return render_template("index.html", rol=current_user.rol, nombre=current_user.nombre,
                            negocio_nombre=get_config("negocio_nombre", "Mi Cocina"))


@app.route("/setup")
def setup():
    if _onboarding_completado():
        return redirect(url_for("login"))
    return redirect(url_for("setup_paso", paso=_onboarding_paso_actual()))


def _avanzar_onboarding(siguiente):
    set_config("onboarding_step", str(siguiente))
    return redirect(url_for("setup_paso", paso=siguiente))


@app.route("/setup/<int:paso>", methods=["GET", "POST"])
def setup_paso(paso):
    global _setup_completado

    if _onboarding_completado():
        return redirect(url_for("login"))
    if paso not in ONBOARDING_PASOS:
        return redirect(url_for("setup"))

    paso_actual = _onboarding_paso_actual()
    if paso > paso_actual:
        return redirect(url_for("setup_paso", paso=paso_actual))

    error = None

    if request.method == "POST":
        saltar = request.form.get("accion") == "saltar"

        if paso == 1:
            negocio_nombre = request.form.get("negocio_nombre", "").strip()
            tipo_negocio = request.form.get("tipo_negocio", "").strip()
            pais = request.form.get("pais", "").strip()
            if not negocio_nombre or not tipo_negocio or not pais:
                error = "Nombre del negocio, tipo de negocio y pais son obligatorios."
            else:
                set_config("negocio_nombre", negocio_nombre)
                set_config("negocio_tipo", tipo_negocio)
                set_config("negocio_pais", pais)
                return _avanzar_onboarding(2)

        elif paso == 2:
            if existe_algun_usuario():
                # La cuenta admin ya se creo en un intento anterior de este paso
                return _avanzar_onboarding(3)
            dueno_nombre = request.form.get("dueno_nombre", "").strip()
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            email = request.form.get("email", "").strip()
            if not dueno_nombre or not username or not password:
                error = "Nombre, usuario y contraseña son obligatorios."
            elif len(password) < 6:
                error = "La contraseña debe tener al menos 6 caracteres."
            else:
                try:
                    crear_usuario(username, password, dueno_nombre, "admin")
                    set_config("dueno_nombre", dueno_nombre)
                    set_config("negocio_email", email)
                    return _avanzar_onboarding(3)
                except Exception as e:
                    error = str(e)

        elif paso == 3:
            moneda = request.form.get("moneda", "").strip() or "Q"
            apertura = request.form.get("horario_apertura", "").strip()
            cierre = request.form.get("horario_cierre", "").strip()
            dias = request.form.getlist("dias_laborales")
            set_config("moneda", moneda)
            set_config("horario_apertura", apertura)
            set_config("horario_cierre", cierre)
            set_config("dias_laborales", ",".join(dias))
            return _avanzar_onboarding(4)

        elif paso == 4:
            if saltar:
                return _avanzar_onboarding(5)
            nombre = request.form.get("producto_nombre", "").strip()
            precio = request.form.get("producto_precio", "").strip()
            costo = request.form.get("producto_costo", "").strip()
            cantidad = request.form.get("producto_cantidad", "").strip()
            if not nombre or not precio:
                error = "Escribe al menos el nombre y el precio, o salta este paso."
            else:
                try:
                    from database.aronium import connect, add_stock
                    conn = connect()
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO Product (Name, Code, Price, Cost, IsEnabled) VALUES (?, ?, ?, ?, 1)",
                        (nombre, "", float(precio), float(costo or 0))
                    )
                    conn.commit()
                    product_id = cur.lastrowid
                    conn.close()
                    qty = int(float(cantidad or 0))
                    if qty > 0:
                        add_stock(product_id, qty)
                    set_config("onboarding_producto_nombre", nombre)
                    return _avanzar_onboarding(5)
                except Exception as e:
                    error = f"No se pudo guardar el producto ({e}). Puedes saltarte este paso y agregarlo despues desde Inventario."

        elif paso == 5:
            if saltar:
                return _avanzar_onboarding(6)
            nombre = request.form.get("cliente_nombre", "").strip()
            telefono = request.form.get("cliente_telefono", "").strip()
            email_cliente = request.form.get("cliente_email", "").strip()
            if not nombre:
                error = "Escribe al menos el nombre, o salta este paso."
            else:
                try:
                    from database.aronium import crear_cliente_completo
                    crear_cliente_completo(nombre, telefono, email_cliente)
                    set_config("onboarding_cliente_nombre", nombre)
                    return _avanzar_onboarding(6)
                except Exception as e:
                    error = f"No se pudo guardar el cliente ({e})."

        elif paso == 6:
            set_config("onboarding_completado", "1")
            _setup_completado = True
            return redirect(url_for("login"))

    resumen = None
    if paso == 6:
        resumen = {
            "negocio_nombre": get_config("negocio_nombre", ""),
            "negocio_tipo": get_config("negocio_tipo", ""),
            "negocio_pais": get_config("negocio_pais", ""),
            "dueno_nombre": get_config("dueno_nombre", ""),
            "negocio_email": get_config("negocio_email", ""),
            "moneda": get_config("moneda", "Q"),
            "horario_apertura": get_config("horario_apertura", ""),
            "horario_cierre": get_config("horario_cierre", ""),
            "dias_laborales": get_config("dias_laborales", ""),
            "producto_nombre": get_config("onboarding_producto_nombre", ""),
            "cliente_nombre": get_config("onboarding_cliente_nombre", ""),
        }

    return render_template("setup.html", paso=paso, total_pasos=len(ONBOARDING_PASOS),
                            error=error, resumen=resumen)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = verify_login(username, password)
        if user:
            login_user(user)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))
        error = "Usuario o contraseña incorrectos"

    return render_template("login.html", error=error)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    mensaje = None
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        mensaje = "Si el correo es válido, te enviamos un enlace de recuperación."

        if ADMIN_EMAIL and email.lower() == ADMIN_EMAIL.lower():
            admin_user = get_admin_activo()
            if admin_user:
                token = crear_token_reset(admin_user.id)
                link = url_for("reset_password", token=token, _external=True)
                try:
                    enviar_reset_password(ADMIN_EMAIL, link)
                except Exception as e:
                    print("Error enviando correo de recuperación:", e)

        return render_template("forgot_password.html", mensaje=mensaje)

    return render_template("forgot_password.html", mensaje=mensaje)


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    token = request.args.get("token", "") or request.form.get("token", "")
    user = validar_token_reset(token) if token else None

    if not token or not user:
        return render_template("reset_password.html", token_valido=False)

    if request.method == "POST":
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")
        if not password or len(password) < 6:
            return render_template("reset_password.html", token_valido=True, token=token,
                                    error="La contraseña debe tener al menos 6 caracteres.")
        if password != password2:
            return render_template("reset_password.html", token_valido=True, token=token,
                                    error="Las contraseñas no coinciden.")
        if usar_token_reset(token, password):
            return redirect(url_for("login", reset="ok"))
        return render_template("reset_password.html", token_valido=False)

    return render_template("reset_password.html", token_valido=True, token=token)


# ══════════════════════════════════════════════════════════
# USUARIOS (solo admin)
# ══════════════════════════════════════════════════════════

@app.route("/api/usuarios", methods=["GET"])
@admin_required
def api_usuarios_list():
    return jsonify(listar_usuarios())


@app.route("/api/usuarios", methods=["POST"])
@admin_required
def api_usuarios_create():
    data = request.json
    try:
        crear_usuario(
            data.get("username", ""),
            data.get("password", ""),
            data.get("nombre", ""),
            data.get("rol", "empleado")
        )
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/usuarios/<int:uid>/toggle", methods=["POST"])
@admin_required
def api_usuarios_toggle(uid):
    data = request.json or {}
    set_usuario_activo(uid, data.get("activo", True))
    return jsonify({"ok": True})


@app.route("/api/usuarios/<int:uid>/password", methods=["PUT"])
@admin_required
def api_usuarios_password(uid):
    data = request.json or {}
    try:
        cambiar_password_usuario(uid, data.get("password", ""))
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ══════════════════════════════════════════════════════════
# CHAT CON GEMINI / OPENCLAW
# ══════════════════════════════════════════════════════════

@app.route("/api/chat", methods=["POST"])
@login_required
def chat():

    data = request.json
    mensaje = data.get("message", "").strip()

    if not mensaje:
        return jsonify({"error": "Mensaje vacío"}), 400

    # ==================================================
    # 1. Intentar resolver usando herramientas
    # ==================================================

    # ==================================================
    # 1. Intentar resolver usando NimboCore
    # ==================================================
    from core.nimbo import send as nimbo_send_gemini
    ctx_gemini = session.get("nimbo_ctx_gemini", {})
    respuesta_tool, ctx_gemini = nimbo_send_gemini(mensaje, context=ctx_gemini, role=current_user.rol)
    session["nimbo_ctx_gemini"] = ctx_gemini
    if respuesta_tool:
        is_html = "<a " in str(respuesta_tool)
        chat_history.append({"role": "user", "content": mensaje, "time": datetime.now().strftime("%H:%M")})
        chat_history.append({"role": "assistant", "content": respuesta_tool, "time": datetime.now().strftime("%H:%M")})
        from database.aronium import guardar_mensaje_chat
        guardar_mensaje_chat("user", mensaje)
        guardar_mensaje_chat("assistant", str(respuesta_tool))
        return jsonify({"response": respuesta_tool, "source": "tool", "html": is_html})
    # 2. Si ninguna herramienta aplica, usar Gemini
    # ==================================================

    if not gemini_client:
        return jsonify({"error": "API key de Gemini no configurada"}), 500

    if current_user.rol != "admin":
        return jsonify({
            "response": "No entendí esa instrucción. Si necesitas ayuda con algo fuera "
                        "de inventario, ventas o clientes, contacta a un administrador.",
            "source": "blocked"
        })

    try:

        system_prompt = """
Eres Nimbo AI.

Si existe una herramienta para resolver una tarea debes utilizarla.

Si no existe una herramienta disponible,
responde normalmente como asistente inteligente.

Siempre responde en español.
"""

        from core.chat_context import resumen_texto
        contexto_reciente = resumen_texto()
        if contexto_reciente:
            system_prompt += (
                "\n\nResumen de la conversacion reciente (puede ser de dias anteriores, "
                "usalo para entender referencias como 'eso' o preguntas de seguimiento):\n"
                f"{contexto_reciente}"
            )

        respuesta = gemini_client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=f"{system_prompt}\n\nUsuario: {mensaje}"
        )

        texto = respuesta.text

        chat_history.append({
            "role": "user",
            "content": mensaje,
            "time": datetime.now().strftime("%H:%M")
        })

        chat_history.append({
            "role": "assistant",
            "content": texto,
            "time": datetime.now().strftime("%H:%M")
        })

        return jsonify({
            "response": texto,
            "source": "gemini"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat/history", methods=["GET"])
@login_required
def get_history():
    return jsonify(chat_history)


@app.route("/api/chat/clear", methods=["POST"])
@login_required
def clear_history():
    chat_history.clear()
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════
# INVENTARIO ARONIUM
# ══════════════════════════════════════════════════════════

def get_db():
    conn = sqlite3.connect(ARONIUM_DB)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/api/inventory", methods=["GET"])
@login_required
def get_inventory():
    try:
        conn = get_db()
        cur = conn.cursor()
        # Tablas comunes en Aronium
        cur.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table'
            ORDER BY name
        """)
        tables = [r[0] for r in cur.fetchall()]
        conn.close()
        return jsonify({"tables": tables})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/inventory/products", methods=["GET"])
@login_required
def get_products():
    try:
        conn = get_db()
        cur = conn.cursor()
        search = request.args.get("search", "")

        # Intentar con tablas comunes de Aronium
        for table in ["items", "products", "Items", "Products", "item", "product"]:
            try:
                if search:
                    cur.execute(f"SELECT * FROM {table} WHERE name LIKE ? LIMIT 100",
                                (f"%{search}%",))
                else:
                    cur.execute(f"SELECT * FROM {table} LIMIT 100")
                rows = [dict(r) for r in cur.fetchall()]
                cols = [d[0] for d in cur.description]
                conn.close()
                return jsonify({"products": rows, "columns": cols, "table": table})
            except Exception:
                continue

        conn.close()
        return jsonify({"products": [], "columns": [], "table": None,
                        "message": "No se encontró tabla de productos"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/inventory/stats", methods=["GET"])
@login_required
def get_stats():
    try:
        conn = get_db()
        cur = conn.cursor()
        stats = {}

        for table in ["items", "products", "Items", "Products"]:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                stats["total_products"] = cur.fetchone()[0]
                stats["table"] = table
                break
            except Exception:
                continue

        # Intentar ventas
        for table in ["sales", "Sales", "transactions", "Transactions"]:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                stats["total_sales"] = cur.fetchone()[0]
                break
            except Exception:
                continue

        conn.close()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/inventory/query", methods=["POST"])
@admin_required
def custom_query():
    """Consulta SQL personalizada (solo SELECT)"""
    data = request.json
    sql = data.get("sql", "").strip()
    if not sql.lower().startswith("select"):
        return jsonify({"error": "Solo se permiten consultas SELECT"}), 400
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(sql)
        rows = [dict(r) for r in cur.fetchall()]
        cols = [d[0] for d in cur.description]
        conn.close()
        return jsonify({"rows": rows, "columns": cols})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/inventory/analyze", methods=["POST"])
@login_required
def analyze_inventory():
    """Análisis con Gemini sobre el inventario"""
    if not gemini_client:
        return jsonify({"error": "API key no configurada"}), 500
    data = request.json
    context = data.get("context", "")
    question = data.get("question", "Dame un análisis del inventario")
    try:
        prompt = f"""Eres un analista de negocios para Mi Cocina Electrodomésticos en Guatemala.
Datos del inventario:
{context}

Pregunta: {question}
Responde en español con análisis claro y recomendaciones prácticas."""
        resp = gemini_client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt
        )
        return jsonify({"analysis": resp.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════
# GENERADOR DE CONTENIDO
# ══════════════════════════════════════════════════════════

@app.route("/api/content/generate", methods=["POST"])
@admin_required
def generate_content():
    if not gemini_client:
        return jsonify({"error": "API key no configurada"}), 500
    data = request.json
    tipo = data.get("type", "post")
    producto = data.get("product", "")
    tono = data.get("tone", "profesional")

    prompts = {
        "post": f"""Crea un post para redes sociales para Mi Cocina Electrodomésticos Guatemala.
Producto: {producto}
Tono: {tono}
Incluye: texto principal, emojis, call to action y hashtags.
Formato: breve, para Instagram/Facebook.""",

        "script": f"""Crea un script para video/reel de 30-45 segundos para Mi Cocina Electrodomésticos Guatemala.
Producto: {producto}
Tono: {tono}
Incluye: gancho inicial, beneficios clave, llamada a la acción.
Formato: guión con indicaciones de escena.""",

        "description": f"""Crea una descripción de producto para Mi Cocina Electrodomésticos Guatemala.
Producto: {producto}
Tono: {tono}
Incluye: características principales, beneficios, precio (si aplica: "consultar precio").
Formato: descripción atractiva para catálogo/tienda online.""",

        "hashtags": f"""Genera 20 hashtags relevantes para Mi Cocina Electrodomésticos Guatemala.
Producto/tema: {producto}
Mix de: hashtags populares, nicho, y locales de Guatemala."""
    }

    prompt = prompts.get(tipo, prompts["post"])

    try:
        resp = gemini_client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt
        )
        return jsonify({"content": resp.text, "type": tipo})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════
# TAREAS / NOTAS
# ══════════════════════════════════════════════════════════

tasks = []

@app.route("/api/tasks", methods=["GET"])
@admin_required
def get_tasks():
    return jsonify(tasks)


@app.route("/api/tasks", methods=["POST"])
@admin_required
def add_task():
    data = request.json
    task = {
        "id": len(tasks) + 1,
        "text": data.get("text", ""),
        "done": False,
        "created": datetime.now().strftime("%d/%m %H:%M")
    }
    tasks.append(task)
    return jsonify(task)


@app.route("/api/tasks/<int:task_id>", methods=["PATCH"])
@admin_required
def update_task(task_id):
    for t in tasks:
        if t["id"] == task_id:
            t["done"] = not t["done"]
            return jsonify(t)
    return jsonify({"error": "No encontrado"}), 404


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
@admin_required
def delete_task(task_id):
    global tasks
    tasks = [t for t in tasks if t["id"] != task_id]
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════
# SISTEMA
# ══════════════════════════════════════════════════════════

@app.route("/api/status", methods=["GET"])
@login_required
def status():
    gemini_ok = False
    if gemini_client:
        try:
            gemini_client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents="ping"
            )
            gemini_ok = True
        except Exception:
            pass

    db_ok = False
    try:
        conn = sqlite3.connect(ARONIUM_DB)
        conn.close()
        db_ok = True
    except Exception:
        pass

    return jsonify({
        "gemini": gemini_ok,
        "aronium": db_ok,
        "time": datetime.now().strftime("%d/%m/%Y %H:%M")
    })
@app.route("/api/openclaw/chat", methods=["POST"])
@login_required
def openclaw_chat():

    data = request.json
    message = data.get("message", "").strip()

    if not message:
        return jsonify({
            "error": "Mensaje vacío"
        }), 400

    # ==================================================
    # 1. Intentar resolver usando herramientas
    # ==================================================

    from core.nimbo import send as nimbo_send_ctx
    ctx = session.get("nimbo_ctx", {})
    response, ctx = nimbo_send_ctx(message, context=ctx, role=current_user.rol)
    session["nimbo_ctx"] = ctx
    from database.aronium import guardar_mensaje_chat
    guardar_mensaje_chat("user", message)
    guardar_mensaje_chat("assistant", str(response))

    chat_history.append({
        "role": "user",
        "content": message,
        "time": datetime.now().strftime("%H:%M")
    })

    chat_history.append({
        "role": "assistant",
        "content": response,
        "time": datetime.now().strftime("%H:%M")
    })

    if not response:
        return jsonify({
        "error": "OpenClaw no devolvió ninguna respuesta."
        }), 500

    is_html = "<a " in str(response) or "<button" in str(response)
    return jsonify({
        "response": response,
        "source": "openclaw",
        "html": is_html
    })

@app.route("/api/inventory/product-columns", methods=["GET"])
@login_required
def product_columns():

    try:
        return jsonify(inventory.product_columns())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/api/inventory/stock-columns", methods=["GET"])
@login_required
def stock_columns():

    try:
        return jsonify(inventory.stock_columns())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/api/inventory/products", methods=["GET"])
@login_required
def inventory_products():

    try:
        return jsonify(
            inventory.products()
        )
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500
    
@app.route("/api/skills/check", methods=["GET"])
@admin_required
def skills_check():

    try:

        return jsonify(

            skills.status()

        )

    except Exception as e:

        return jsonify({

            "error": str(e)

        }), 500
      
@app.route("/api/inventory/search")
@login_required
def inventory_search():

    barcode = request.args.get("barcode", "").strip()

    product = inventory.search_barcode(barcode)

    if product:
        return jsonify(product)

    return jsonify({
        "error": "Producto no encontrado"
    }), 404

@app.route("/api/tool/inventory/search", methods=["GET"])
@login_required
def tool_inventory_search():

    text = request.args.get("q", "")

    return jsonify({
        "response": search_product(text)
    })

@app.route("/pos")
@login_required
def pos():

    return render_template("pos.html")

@app.route("/api/tools")
@admin_required
def api_tools():
    return jsonify({
        "tools": list_tools()
    })


@app.route("/api/db/products")
@login_required
def db_products():
    from database.aronium import get_products
    search = request.args.get("search", "")
    return jsonify(get_products(search=search))

@app.route("/api/db/stats")
@login_required
def db_stats():
    from database.aronium import get_sales_today, get_sales_month, get_low_stock, get_top_products
    return jsonify({
        "sales_today": get_sales_today(),
        "sales_month": get_sales_month(),
        "low_stock": get_low_stock(),
        "top_products": get_top_products()
    })

@app.route("/api/db/customers")
@login_required
def db_customers():
    from database.aronium import get_customers
    search = request.args.get("search", "")
    return jsonify(get_customers(search=search))

@app.route("/api/db/products/add", methods=["POST"])
@login_required
def db_add_product():
    from database.aronium import connect
    data = request.json
    try:
        conn = connect()
        cur = conn.cursor()
        cur.execute("INSERT INTO Product (Name, Code, Price, Cost, IsEnabled) VALUES (?, ?, ?, ?, 1)",
            (data["Name"], data["Code"], data["Price"], data["Cost"]))
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "id": cur.lastrowid})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/db/products/<int:pid>", methods=["PUT"])
@login_required
def db_edit_product(pid):
    from database.aronium import connect
    data = request.json
    try:
        conn = connect()
        cur = conn.cursor()
        cur.execute("UPDATE Product SET Name=?, Code=?, Price=?, Cost=? WHERE Id=?",
            (data["Name"], data["Code"], data["Price"], data["Cost"], pid))
        conn.commit()
        conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/db/products/<int:pid>", methods=["DELETE"])
@login_required
def db_delete_product(pid):
    from database.aronium import connect
    try:
        conn = connect()
        cur = conn.cursor()
        cur.execute("UPDATE Product SET IsEnabled=0 WHERE Id=?", (pid,))
        conn.commit()
        conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/db/stock/add", methods=["POST"])
@login_required
def db_add_stock():
    from database.aronium import add_stock
    data = request.json
    ok = add_stock(data["product_id"], data["quantity"])
    return jsonify({"ok": ok})

@app.route("/api/db/stock/remove", methods=["POST"])
@login_required
def db_remove_stock():
    from database.aronium import remove_stock
    data = request.json
    ok = remove_stock(data["product_id"], data["quantity"])
    if not ok:
        return jsonify({"error": "Stock insuficiente"}), 400
    return jsonify({"ok": ok})

@app.route("/api/db/stock/<int:pid>", methods=["GET"])
@login_required
def db_get_stock(pid):
    from database.aronium import get_stock
    qty = get_stock(pid)
    return jsonify({"stock": qty})


@app.route("/api/db/kardex")
@login_required
def db_kardex():
    from database.aronium import get_kardex
    product_id = request.args.get("product_id")
    limit = int(request.args.get("limit", 50))
    return jsonify(get_kardex(product_id=product_id, limit=limit))

@app.route("/api/db/alertas")
@login_required
def db_alertas():
    from database.aronium import get_alertas_stock
    return jsonify(get_alertas_stock())

@app.route("/api/db/stock-minimo", methods=["POST"])
@login_required
def db_set_stock_minimo():
    from database.aronium import set_stock_minimo
    data = request.json
    set_stock_minimo(data["product_id"], data["product_name"], data["minimo"])
    return jsonify({"ok": True})


@app.route("/api/download/<path:filename>")
@login_required
def download_file(filename):
    import os
    from flask import send_file
    filepath = f"/home/ictor_axtor/micocina-dashboard/{filename}"
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return jsonify({"error": "Archivo no encontrado"}), 404


@app.route("/api/db/alertas-precios")
@admin_required
def db_alertas_precios():
    from database.aronium import get_alertas_precios
    return jsonify(get_alertas_precios())


import os
UPLOAD_FOLDER = '/home/ictor_axtor/micocina-dashboard/static/fotos'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/api/productos/foto", methods=["POST"])
@login_required
def subir_foto_producto():
    from flask import request
    from database.aronium import nimbo_connect
    
    if 'foto' not in request.files:
        return jsonify({"error": "No se envio foto"}), 400
    
    producto_nombre = request.form.get("producto", "")
    producto_id = request.form.get("producto_id", 0)
    foto = request.files['foto']
    
    if foto.filename == '':
        return jsonify({"error": "Archivo vacio"}), 400
    
    ext = foto.filename.rsplit('.', 1)[-1].lower()
    if ext not in ['jpg', 'jpeg', 'png', 'webp']:
        return jsonify({"error": "Formato no permitido"}), 400
    
    import uuid
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    foto.save(filepath)
    
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO ProductoFoto (ProductoId, ProductoNombre, RutaFoto) VALUES (?,?,?)",
        (producto_id, producto_nombre, f"/static/fotos/{filename}"))
    conn.commit()
    conn.close()
    
    return jsonify({"ok": True, "ruta": f"/static/fotos/{filename}"})

@app.route("/api/productos/fotos/<int:producto_id>")
@login_required
def get_fotos_producto(producto_id):
    from database.aronium import nimbo_connect
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ProductoFoto WHERE ProductoId=? ORDER BY FechaSubida DESC", (producto_id,))
    fotos = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(fotos)


@app.route("/tiktok-verification.html")
def tiktok_verify():
    return "tiktok-verification"


@app.route("/tiktokpxma0DpKg90IGKsTJYXp0AInP21T3LWN.txt")
@app.route("/tiktokpxma0DpKg90IGKsTJYXp0AInP21T3LWN.txt/")
def tiktok_verify_file():
    return "tiktok-developers-site-verification=pxma0DpKg90IGKsTJYXp0AInP21T3LWN"


@app.route("/api/limpieza-anual", methods=["POST"])
@admin_required
def limpieza_anual():
    from database.aronium import archivar_y_limpiar_anio
    data = request.json
    anio = data.get("anio", 2026)
    try:
        archivo = archivar_y_limpiar_anio(anio)
        return jsonify({"ok": True, "archivo": archivo})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/recordatorios")
@admin_required
def get_recordatorios():
    from database.aronium import get_recordatorios
    return jsonify(get_recordatorios())


@app.route("/api/cotizaciones/resumen")
@admin_required
def get_resumen_cotizaciones():
    from database.aronium import get_resumen_cotizaciones
    return jsonify(get_resumen_cotizaciones())


# ── CAJA REGISTRADORA ──────────────────────────────────────

def _requiere_turno_abierto():
    from database.aronium import get_turno_abierto
    turno = get_turno_abierto()
    if not turno:
        return None, (jsonify({"error": "No hay ningun turno de caja abierto."}), 400)
    return turno, None


@app.route("/api/caja/estado")
@login_required
def caja_estado():
    from database.aronium import get_turno_abierto, get_denominaciones_actuales, sencillo_bajo, DENOMINACIONES
    turno = get_turno_abierto()
    if not turno:
        return jsonify({"turno": None, "denominaciones": DENOMINACIONES})
    bajo, pequenas = sencillo_bajo(turno["Id"])
    return jsonify({
        "turno": turno,
        "denominaciones_actuales": get_denominaciones_actuales(turno["Id"]),
        "denominaciones": DENOMINACIONES,
        "sencillo_bajo": bajo,
        "denominaciones_pequenas": pequenas
    })


@app.route("/api/caja/abrir", methods=["POST"])
@login_required
def caja_abrir():
    from database.aronium import get_turno_abierto, abrir_turno
    if get_turno_abierto():
        return jsonify({"error": "Ya hay un turno de caja abierto."}), 400
    data = request.json or {}
    fondo_inicial = data.get("fondo_inicial", {})
    turno_id, total = abrir_turno(int(current_user.id), current_user.nombre, fondo_inicial)
    return jsonify({"ok": True, "turno_id": turno_id, "efectivo_esperado": total})


@app.route("/api/caja/cerrar", methods=["POST"])
@login_required
def caja_cerrar():
    from database.aronium import cerrar_turno
    turno, error = _requiere_turno_abierto()
    if error:
        return error
    data = request.json or {}
    conteo_fisico = data.get("conteo_fisico", {})
    resultado = cerrar_turno(turno["Id"], conteo_fisico)
    return jsonify(resultado)


@app.route("/api/caja/carrito")
@login_required
def caja_carrito():
    from database.aronium import get_carrito
    turno, error = _requiere_turno_abierto()
    if error:
        return error
    items = get_carrito(turno["Id"])
    total = round(sum(i["Total"] for i in items), 2)
    return jsonify({"items": items, "total": total})


@app.route("/api/caja/carrito/agregar", methods=["POST"])
@login_required
def caja_carrito_agregar():
    from database.aronium import get_product_by_id, get_product_by_code, get_products, agregar_a_carrito
    turno, error = _requiere_turno_abierto()
    if error:
        return error
    data = request.json or {}
    cantidad = data.get("cantidad", 1)
    try:
        cantidad = float(cantidad)
    except (TypeError, ValueError):
        return jsonify({"error": "Cantidad invalida"}), 400
    if cantidad <= 0:
        return jsonify({"error": "Cantidad invalida"}), 400

    producto = None
    if data.get("producto_id"):
        producto = get_product_by_id(data["producto_id"])
    elif data.get("query"):
        query = data["query"].strip()
        producto = get_product_by_code(query)
        if not producto:
            productos = get_products(search=query)
            if len(productos) > 1:
                return jsonify({"multiples": True, "productos": productos[:8]})
            producto = productos[0] if productos else None

    if not producto:
        return jsonify({"error": "Producto no encontrado."}), 404
    if producto["Stock"] < cantidad:
        return jsonify({"error": f"Stock insuficiente de {producto['Name']} ({int(producto['Stock'])} disponibles)."}), 400

    items = agregar_a_carrito(turno["Id"], producto["Id"], producto["Name"], cantidad, producto["Price"])
    total = round(sum(i["Total"] for i in items), 2)
    return jsonify({"items": items, "total": total})


@app.route("/api/caja/carrito/quitar", methods=["POST"])
@login_required
def caja_carrito_quitar():
    from database.aronium import quitar_de_carrito
    data = request.json or {}
    item_id = data.get("item_id")
    if not item_id:
        return jsonify({"error": "item_id requerido"}), 400
    items = quitar_de_carrito(item_id)
    total = round(sum(i["Total"] for i in items), 2)
    return jsonify({"items": items, "total": total})


@app.route("/api/caja/carrito/vaciar", methods=["POST"])
@login_required
def caja_carrito_vaciar():
    from database.aronium import vaciar_carrito
    turno, error = _requiere_turno_abierto()
    if error:
        return error
    vaciar_carrito(turno["Id"])
    return jsonify({"ok": True, "items": [], "total": 0})


@app.route("/api/caja/cobrar", methods=["POST"])
@login_required
def caja_cobrar():
    from database.aronium import cobrar_carrito
    from services.ticket import generar_texto_ticket
    turno, error = _requiere_turno_abierto()
    if error:
        return error
    data = request.json or {}
    resultado = cobrar_carrito(
        turno["Id"],
        data.get("metodo_pago"),
        cliente_id=data.get("cliente_id"),
        monto_efectivo=data.get("monto_efectivo"),
        monto_tarjeta=data.get("monto_tarjeta"),
        denominaciones_recibidas=data.get("denominaciones_recibidas")
    )
    if resultado.get("error"):
        return jsonify(resultado), 400

    ticket_items = [{
        "nombre": i["ProductoNombre"], "cantidad": i["Cantidad"],
        "precio_unit": i["PrecioUnit"], "subtotal": i["Total"]
    } for i in resultado["items"]]
    resultado["ticket"] = generar_texto_ticket(
        resultado["venta_id"], resultado["fecha"], ticket_items, resultado["total"],
        resultado["metodo_pago"], cliente_nombre=data.get("cliente_nombre", ""),
        efectivo_recibido=resultado["monto_efectivo"] if resultado["metodo_pago"] == "efectivo" else None,
        cambio=resultado["cambio"], cajero=current_user.nombre
    )
    return jsonify(resultado)


@app.route("/api/caja/retirar", methods=["POST"])
@login_required
def caja_retirar():
    if not current_user.is_admin:
        return jsonify({"error": "Solo un administrador puede retirar efectivo de caja."}), 403
    from database.aronium import retirar_caja
    turno, error = _requiere_turno_abierto()
    if error:
        return error
    data = request.json or {}
    monto = data.get("monto", 0)
    try:
        monto = float(monto)
    except (TypeError, ValueError):
        return jsonify({"error": "Monto invalido"}), 400
    resultado = retirar_caja(turno["Id"], monto, data.get("descripcion", ""), data.get("denominaciones"))
    if resultado.get("error"):
        return jsonify(resultado), 400
    return jsonify(resultado)


@app.route("/api/caja/movimientos")
@login_required
def caja_movimientos():
    from database.aronium import get_movimientos_caja
    turno, error = _requiere_turno_abierto()
    if error:
        return error
    return jsonify(get_movimientos_caja(turno["Id"]))


@app.route("/api/caja/imprimir-ticket", methods=["POST"])
@login_required
def caja_imprimir_ticket():
    from database.aronium import nimbo_connect
    from services.ticket import generar_texto_ticket
    data = request.json or {}
    venta_id = data.get("venta_id")
    if not venta_id:
        return jsonify({"error": "venta_id requerido"}), 400
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""SELECT v.*, c.Nombre as ClienteNombre FROM Venta v
        LEFT JOIN Cliente c ON v.ClienteId=c.Id WHERE v.Id=?""", (venta_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Venta no encontrada"}), 404
    venta = dict(row)
    # Reimpresion: no se conserva el detalle por producto de ventas ya cerradas,
    # se reconstruye un ticket simplificado a partir de la descripcion guardada.
    items = [{"nombre": venta["Descripcion"], "cantidad": 1, "precio_unit": venta["Total"], "subtotal": venta["Total"]}]
    ticket = generar_texto_ticket(
        venta_id, venta["Fecha"], items, venta["Total"], "(reimpresion)",
        cliente_nombre=venta.get("ClienteNombre") or ""
    )
    return jsonify({"ticket": ticket})


@app.route("/api/chat/historial")
@admin_required
def get_historial_guardado():
    from database.aronium import get_historial_chat
    return jsonify(get_historial_chat())

@app.route("/api/chat/limpiar-historial", methods=["POST"])
@admin_required
def limpiar_historial_guardado():
    from database.aronium import limpiar_historial_chat
    limpiar_historial_chat()
    return jsonify({"ok": True})


@app.route("/api/chat/archivar", methods=["POST"])
@admin_required
def archivar_chat():
    from database.aronium import archivar_chat_trimestral
    archivo = archivar_chat_trimestral()
    if archivo:
        return jsonify({"ok": True, "archivo": archivo.split("/")[-1]})
    return jsonify({"ok": True, "mensaje": "No hay mensajes antiguos para archivar"})


@app.route("/api/contabilidad/equilibrio")
@admin_required
def get_equilibrio():
    from database.aronium import get_gastos, get_pagos_fijos, get_margen_productos
    gastos = get_gastos()
    total_gastos = sum(float(g["Monto"]) for g in gastos)
    productos = get_margen_productos()
    if not productos:
        return jsonify({"error": "Sin datos"})
    precios = [float(p["Price"]) for p in productos if float(p["Price"]) > 0]
    costos = [float(p["Cost"]) for p in productos if float(p["Cost"]) > 0]
    if not precios or not costos:
        return jsonify({"error": "Sin precios"})
    precio_prom = sum(precios) / len(precios)
    costo_prom = sum(costos) / len(costos)
    contribucion = (precio_prom - costo_prom) - (precio_prom * 0.06)
    if contribucion <= 0:
        return jsonify({"error": "Margen negativo"})
    unidades = total_gastos / contribucion if total_gastos > 0 else 0
    ventas_necesarias = unidades * precio_prom
    from database.aronium import nimbo_connect
    from datetime import datetime
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT IFNULL(SUM(Total),0) as total FROM Venta WHERE Mes=? AND Anio=?",
        (datetime.now().month, datetime.now().year))
    ventas_actuales = float(cur.fetchone()["total"])
    conn.close()
    return jsonify({
        "gastos": round(total_gastos, 2),
        "ventas_necesarias": round(ventas_necesarias, 2),
        "ventas_actuales": round(ventas_actuales, 2),
        "superado": ventas_actuales >= ventas_necesarias
    })


@app.route("/api/graficas/ventas")
@admin_required
def graficas_ventas():
    from database.aronium import get_comparacion_meses
    meses = get_comparacion_meses(6)
    return jsonify({
        "labels": [m["nombre"] for m in meses],
        "ventas": [m["total"] for m in meses],
        "gastos": [m["gastos"] for m in meses],
        "utilidad": [m["utilidad"] for m in meses]
    })


@app.route("/api/backup", methods=["POST"])
@admin_required
def hacer_backup_route():
    from database.aronium import hacer_backup
    try:
        fecha = hacer_backup()
        return jsonify({"ok": True, "fecha": fecha})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("=" * 50)
    print("  Nimbo AI Dashboard")
    print("  http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)
