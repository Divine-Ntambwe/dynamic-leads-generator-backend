import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_email(to: str, subject: str, body: str, html_body: str = None):
    sender   = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASSWORD")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = to

    # Plain-text part first — email clients show the last part they support,
    # so HTML must come second to be preferred over plain text.
    msg.attach(MIMEText(body, "plain"))

    if html_body:
        msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, to, msg.as_string())

    print(f"[Mailer] Email sent to {to}")