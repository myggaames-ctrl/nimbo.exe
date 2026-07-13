"""
Servicio de correo
Nimbo AI
"""
import logging
from flask import current_app
from flask_mail import Mail, Message

mail = Mail()

logger = logging.getLogger("nimbo.mail")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


def enviar_reset_password(destinatario, link):
    msg = Message(
        subject="Recuperación de contraseña - Nimbo AI",
        recipients=[destinatario],
        html=f"""
        <p>Solicitaste recuperar la contraseña de administrador de <b>Nimbo AI</b> (Mi Cocina Electrodomésticos).</p>
        <p><a href="{link}">Haz clic aquí para crear una nueva contraseña</a></p>
        <p>Este enlace expira en 1 hora. Si tú no solicitaste esto, ignora este mensaje.</p>
        """
    )

    server = current_app.config.get("MAIL_SERVER")
    port = current_app.config.get("MAIL_PORT")
    username = current_app.config.get("MAIL_USERNAME")
    use_tls = current_app.config.get("MAIL_USE_TLS")

    logger.info(
        "Enviando correo de recuperación a %s via %s:%s (usuario=%s, tls=%s)",
        destinatario, server, port, username, use_tls
    )

    try:
        mail.send(msg)
    except Exception:
        logger.exception(
            "FALLO al enviar correo a %s via %s:%s (usuario=%s, tls=%s)",
            destinatario, server, port, username, use_tls
        )
        raise

    logger.info("Correo enviado correctamente a %s", destinatario)
