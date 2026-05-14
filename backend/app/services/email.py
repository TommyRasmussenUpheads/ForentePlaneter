import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.core.config import get_settings

settings = get_settings()


def _send(to_email: str, subject: str, html: str, text: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.sendmail(settings.smtp_from_email, to_email, msg.as_string())


def send_verification_email(to_email: str, username: str, token: str):
    url = f"{settings.game_base_url}/verify-email?token={token}"
    subject = f"Bekreft din konto — {settings.game_name}"
    html = f"""
    <h2>Velkommen til {settings.game_name}, {username}!</h2>
    <p>Klikk lenken under for å bekrefte e-postadressen din:</p>
    <p><a href="{url}" style="padding:10px 20px;background:#7F77DD;color:white;
       border-radius:6px;text-decoration:none">Bekreft e-post</a></p>
    <p>Lenken er gyldig i {settings.email_verify_token_expire_hours} timer.</p>
    <p style="color:#999;font-size:12px">
      Hvis du ikke registrerte deg, kan du ignorere denne e-posten.
    </p>
    """
    text = f"Bekreft e-post: {url}"
    _send(to_email, subject, html, text)


def send_invite_email(to_email: str, from_username: str, token: str):
    url = f"{settings.game_base_url}/register?invite={token}"
    subject = f"{from_username} inviterer deg til {settings.game_name}"
    html = f"""
    <h2>Du er invitert til {settings.game_name}!</h2>
    <p><strong>{from_username}</strong> har invitert deg til å bli med i 
    det galaktiske romstrategispillet {settings.game_name}.</p>
    <p><a href="{url}" style="padding:10px 20px;background:#7F77DD;color:white;
       border-radius:6px;text-decoration:none">Registrer deg nå</a></p>
    <p style="color:#999;font-size:12px">
      Invitasjonen er gyldig i {settings.invite_token_expire_days} dager.
    </p>
    """
    text = f"Registrer deg: {url}"
    _send(to_email, subject, html, text)


def send_password_reset_email(to_email: str, username: str, token: str):
    url = f"{settings.game_base_url}/reset-password?token={token}"
    subject = f"Tilbakestill passord — {settings.game_name}"
    html = f"""
    <h2>Tilbakestill passord</h2>
    <p>Hei {username}, klikk under for å velge nytt passord:</p>
    <p><a href="{url}" style="padding:10px 20px;background:#7F77DD;color:white;
       border-radius:6px;text-decoration:none">Nytt passord</a></p>
    <p style="color:#999;font-size:12px">
      Lenken er gyldig i 2 timer. 
      Hvis du ikke ba om dette, kan du ignorere e-posten.
    </p>
    """
    text = f"Tilbakestill passord: {url}"
    _send(to_email, subject, html, text)
