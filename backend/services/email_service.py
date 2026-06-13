# backend/services/email_service.py

"""
SendGrid email integration with SMTP fallback support.

Design decision: SendGrid is the primary transport. If SENDGRID_API_KEY is
missing or blank, the service falls back to Python's smtplib SMTP transport
(useful in local dev without a SendGrid account). The fallback logs a warning
so it is never silent in production.

All public functions are async — they offload the blocking SDK/SMTP calls to
a thread pool via asyncio.to_thread so they don't block the event loop.

WARN: Never call this service directly from the event loop's main thread
with blocking code — always await the public async functions.
"""

import asyncio
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SENDGRID_API_KEY: str = os.environ.get("SENDGRID_API_KEY", "")
FROM_EMAIL: str = os.environ.get("FROM_EMAIL", "noreply@jobtracker.app")

# SMTP fallback settings (for local dev — set via env vars)
SMTP_HOST: str = os.environ.get("SMTP_HOST", "localhost")
SMTP_PORT: int = int(os.environ.get("SMTP_PORT", "1025"))   # MailHog default
SMTP_USER: Optional[str] = os.environ.get("SMTP_USER")
SMTP_PASS: Optional[str] = os.environ.get("SMTP_PASS")


# ---------------------------------------------------------------------------
# Low-level send — runs in a thread pool (blocking I/O)
# ---------------------------------------------------------------------------

def _send_via_sendgrid(to_email: str, subject: str, html_body: str) -> None:
    """
    Send an email using the SendGrid Web API (v3).
    Raises RuntimeError on non-2xx responses.
    """
    # Import here to keep the module importable even when sendgrid is absent.
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
    except ImportError as exc:
        raise RuntimeError("sendgrid package is not installed.") from exc

    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=to_email,
        subject=subject,
        html_content=html_body,
    )
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    response = sg.send(message)

    if response.status_code not in (200, 202):
        raise RuntimeError(
            f"SendGrid returned unexpected status {response.status_code}: "
            f"{response.body}"
        )
    logger.info("Email sent via SendGrid to %s — subject: %s", to_email, subject)


def _send_via_smtp(to_email: str, subject: str, html_body: str) -> None:
    """
    SMTP fallback — useful in local dev (e.g. with MailHog on port 1025).

    WARN: This transport sends email in plaintext unless SMTP_HOST supports
    STARTTLS. Do not use for production without TLS configured.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        if SMTP_USER and SMTP_PASS:
            smtp.login(SMTP_USER, SMTP_PASS)
        smtp.sendmail(FROM_EMAIL, to_email, msg.as_string())

    logger.info("Email sent via SMTP to %s — subject: %s", to_email, subject)


def _send_email_sync(to_email: str, subject: str, html_body: str) -> None:
    """
    Dispatcher: try SendGrid first, fall back to SMTP if the API key is absent.
    """
    if SENDGRID_API_KEY:
        _send_via_sendgrid(to_email, subject, html_body)
    else:
        logger.warning(
            "SENDGRID_API_KEY is not set — falling back to SMTP transport. "
            "Set SENDGRID_API_KEY in .env for production use."
        )
        _send_via_smtp(to_email, subject, html_body)


# ---------------------------------------------------------------------------
# Public async API
# ---------------------------------------------------------------------------

async def send_email(to_email: str, subject: str, html_body: str) -> None:
    """
    Async wrapper — offloads blocking SDK/SMTP calls to a thread pool.
    Always await this; never call _send_email_sync directly from async code.
    """
    await asyncio.to_thread(_send_email_sync, to_email, subject, html_body)


# ---------------------------------------------------------------------------
# Email templates
# ---------------------------------------------------------------------------

def _base_template(title: str, body_html: str) -> str:
    """
    Minimal but clean HTML email wrapper.
    Inline styles are used for maximum email client compatibility.
    """
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head><meta charset="UTF-8"><title>{title}</title></head>
    <body style="margin:0;padding:0;font-family:Arial,sans-serif;background:#f4f4f4;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td align="center" style="padding:32px 0;">
            <table width="600" cellpadding="0" cellspacing="0"
                   style="background:#ffffff;border-radius:8px;overflow:hidden;">
              <tr>
                <td style="background:#1e40af;padding:24px 32px;">
                  <h1 style="color:#ffffff;margin:0;font-size:20px;">
                    Job Application Tracker
                  </h1>
                </td>
              </tr>
              <tr>
                <td style="padding:32px;">
                  {body_html}
                </td>
              </tr>
              <tr>
                <td style="padding:16px 32px;background:#f4f4f4;
                           color:#9ca3af;font-size:12px;text-align:center;">
                  This is an automated reminder from your Job Application Tracker.
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """


async def send_interview_reminder(
    to_email: str,
    company: str,
    job_title: str,
    interview_date: str,
    interview_type: Optional[str] = None,
    interviewer: Optional[str] = None,
) -> None:
    """Send a 24-hour interview reminder email."""
    type_line = f"<p><strong>Type:</strong> {interview_type}</p>" if interview_type else ""
    interviewer_line = f"<p><strong>With:</strong> {interviewer}</p>" if interviewer else ""
    body = f"""
        <h2 style="color:#1e40af;">Interview Reminder ⏰</h2>
        <p>You have an interview scheduled in <strong>24 hours</strong>.</p>
        <p><strong>Company:</strong> {company}</p>
        <p><strong>Role:</strong> {job_title}</p>
        <p><strong>Date:</strong> {interview_date}</p>
        {type_line}
        {interviewer_line}
        <p style="margin-top:24px;color:#6b7280;">Good luck — you've got this!</p>
    """
    await send_email(
        to_email,
        subject=f"Interview Reminder: {job_title} at {company}",
        html_body=_base_template("Interview Reminder", body),
    )


async def send_followup_reminder(
    to_email: str,
    company: str,
    job_title: str,
    days_since_applied: int,
) -> None:
    """Send a follow-up due reminder email."""
    body = f"""
        <h2 style="color:#1e40af;">Time to Follow Up 📧</h2>
        <p>It's been <strong>{days_since_applied} days</strong> since you applied.</p>
        <p><strong>Company:</strong> {company}</p>
        <p><strong>Role:</strong> {job_title}</p>
        <p style="margin-top:24px;">
          Consider sending a polite follow-up email to check on your application status.
        </p>
    """
    await send_email(
        to_email,
        subject=f"Follow-up Reminder: {job_title} at {company}",
        html_body=_base_template("Follow-up Reminder", body),
    )


async def send_stale_alert(
    to_email: str,
    company: str,
    job_title: str,
    days_since_update: int,
) -> None:
    """Send a stale application alert — no update in 7+ days."""
    body = f"""
        <h2 style="color:#dc2626;">Stale Application Alert ⚠️</h2>
        <p>No update in <strong>{days_since_update} days</strong>.</p>
        <p><strong>Company:</strong> {company}</p>
        <p><strong>Role:</strong> {job_title}</p>
        <p style="margin-top:24px;">
          You may want to follow up or mark this application as closed.
        </p>
    """
    await send_email(
        to_email,
        subject=f"Stale Application: {job_title} at {company}",
        html_body=_base_template("Stale Application Alert", body),
    )


async def send_weekly_summary(
    to_email: str,
    total: int,
    by_status: dict,
    interviews_this_week: int,
) -> None:
    """Send a Monday morning weekly digest."""
    status_rows = "".join(
        f"<tr><td style='padding:4px 8px;'>{s.capitalize()}</td>"
        f"<td style='padding:4px 8px;text-align:right;'><strong>{c}</strong></td></tr>"
        for s, c in by_status.items()
    )
    body = f"""
        <h2 style="color:#1e40af;">Weekly Summary 📊</h2>
        <p>Here's your job search recap for the week.</p>
        <table style="width:100%;border-collapse:collapse;margin:16px 0;">
          <thead>
            <tr style="background:#eff6ff;">
              <th style="padding:8px;text-align:left;">Status</th>
              <th style="padding:8px;text-align:right;">Count</th>
            </tr>
          </thead>
          <tbody>{status_rows}</tbody>
          <tfoot>
            <tr style="border-top:2px solid #e5e7eb;">
              <td style="padding:8px;"><strong>Total applications</strong></td>
              <td style="padding:8px;text-align:right;"><strong>{total}</strong></td>
            </tr>
          </tfoot>
        </table>
        <p>Interviews scheduled this week: <strong>{interviews_this_week}</strong></p>
    """
    await send_email(
        to_email,
        subject="Your Weekly Job Search Summary",
        html_body=_base_template("Weekly Summary", body),
    )


async def send_test_email(to_email: str) -> None:
    """Send a quick test email to verify the notification configuration."""
    body = """
        <h2 style="color:#16a34a;">Test Email ✅</h2>
        <p>Your Job Application Tracker notification settings are working correctly.</p>
        <p style="color:#6b7280;margin-top:24px;">
          You will receive reminders for interviews, follow-ups, and stale applications
          based on your configured preferences.
        </p>
    """
    await send_email(
        to_email,
        subject="Job Tracker — Test Notification",
        html_body=_base_template("Test Email", body),
    )
