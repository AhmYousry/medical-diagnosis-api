"""Async email service using aiosmtplib."""

from __future__ import annotations

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_email(*, to: str, subject: str, html: str) -> None:
    """Send an HTML email. Silently logs on failure — never raises."""
    if not settings.smtp_username:
        logger.warning("SMTP not configured — skipping email to %s", to)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    msg["To"] = to
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            start_tls=settings.smtp_tls,
        )
        logger.info("Email sent — to=%s subject=%s", to, subject)
    except Exception:  # pragma: no cover
        logger.exception("Failed to send email to %s", to)


# ── HTML templates ──────────────────────────────────────────────────────────

def _base_template(content: str) -> str:
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>MedScan AI</title>
</head>
<body style="margin:0;padding:0;background:#0a0e1a;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0e1a;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0"
               style="background:#111827;border:1px solid rgba(0,212,255,0.12);border-radius:16px;overflow:hidden;">
          <!-- header -->
          <tr>
            <td style="padding:28px 32px;background:linear-gradient(135deg,#0d1a2e,#111827);border-bottom:1px solid rgba(0,212,255,0.12);">
              <table cellpadding="0" cellspacing="0">
                <tr>
                  <td style="background:#00D4FF;width:36px;height:36px;border-radius:8px;text-align:center;vertical-align:middle;">
                    <span style="color:#0a0e1a;font-size:18px;font-weight:bold;line-height:36px;">✦</span>
                  </td>
                  <td style="padding-left:12px;">
                    <span style="color:#f1f5f9;font-size:18px;font-weight:700;letter-spacing:-0.5px;">MedScan AI</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <!-- body -->
          <tr>
            <td style="padding:32px;">
              {content}
            </td>
          </tr>
          <!-- footer -->
          <tr>
            <td style="padding:20px 32px;border-top:1px solid rgba(255,255,255,0.06);text-align:center;">
              <p style="margin:0;font-size:11px;color:#64748b;">
                © 2026 MedScan AI · This email was sent automatically — please do not reply.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def _button(url: str, label: str) -> str:
    return f"""
<table cellpadding="0" cellspacing="0" style="margin:24px 0;">
  <tr>
    <td style="background:#00D4FF;border-radius:10px;text-align:center;padding:0;">
      <a href="{url}" target="_blank"
         style="display:inline-block;padding:14px 28px;color:#0a0e1a;font-size:14px;font-weight:700;
                text-decoration:none;letter-spacing:0.3px;">{label}</a>
    </td>
  </tr>
</table>
"""


def build_verification_email(full_name: str, verify_url: str) -> str:
    content = f"""
      <h2 style="margin:0 0 8px;color:#f1f5f9;font-size:22px;font-weight:700;">Verify your email</h2>
      <p style="margin:0 0 20px;color:#94a3b8;font-size:14px;line-height:1.6;">
        Hi {full_name}, welcome to MedScan AI! Click the button below to confirm your email address.
        This link expires in <strong style="color:#f1f5f9;">24 hours</strong>.
      </p>
      {_button(verify_url, "Verify Email Address")}
      <p style="margin:0;color:#64748b;font-size:12px;word-break:break-all;">
        Or copy this link:<br/>
        <span style="color:#00D4FF;">{verify_url}</span>
      </p>
    """
    return _base_template(content)


def build_password_reset_email(full_name: str, reset_url: str) -> str:
    content = f"""
      <h2 style="margin:0 0 8px;color:#f1f5f9;font-size:22px;font-weight:700;">Reset your password</h2>
      <p style="margin:0 0 20px;color:#94a3b8;font-size:14px;line-height:1.6;">
        Hi {full_name}, we received a request to reset your MedScan AI password.
        This link expires in <strong style="color:#f1f5f9;">2 hours</strong>.
        If you didn't make this request, you can safely ignore this email.
      </p>
      {_button(reset_url, "Reset Password")}
      <p style="margin:0;color:#64748b;font-size:12px;word-break:break-all;">
        Or copy this link:<br/>
        <span style="color:#00D4FF;">{reset_url}</span>
      </p>
      <p style="margin:16px 0 0;color:#ef4444;font-size:12px;">
        ⚠️  For your security, never share this link with anyone.
      </p>
    """
    return _base_template(content)
