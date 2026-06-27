"""
Email Distribution Service
Send reports and notifications via email with OAuth and SMTP support
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import asyncio


class EmailProvider(Enum):
    """Email providers"""
    GMAIL = "gmail"
    OFFICE365 = "office365"
    CUSTOM_SMTP = "custom_smtp"


@dataclass
class EmailConfig:
    """Email provider configuration"""
    provider: EmailProvider
    username: str
    password: Optional[str] = None
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    use_tls: bool = True
    oauth_token: Optional[str] = None
    from_address: Optional[str] = None
    from_name: str = "QAMill"


@dataclass
class EmailMessage:
    """Email message"""
    to: List[str]
    subject: str
    body: str
    html_body: Optional[str] = None
    attachments: List[Dict[str, Any]] = None
    cc: List[str] = None
    bcc: List[str] = None


@dataclass
class EmailLog:
    """Email delivery log"""
    id: str
    message: EmailMessage
    provider: EmailProvider
    status: str  # sent, failed, pending
    timestamp: datetime
    error_message: Optional[str] = None
    retry_count: int = 0


class EmailService:
    """Service for email distribution and report sharing"""

    def __init__(self):
        self.config: Optional[EmailConfig] = None
        self.log: List[EmailLog] = []
        self.email_id_counter = 0

    def set_email_config(self, config: EmailConfig) -> None:
        """Set email configuration"""
        self.config = config

    def set_gmail_config(self, username: str, oauth_token: str) -> None:
        """Configure Gmail with OAuth"""
        self.config = EmailConfig(
            provider=EmailProvider.GMAIL,
            username=username,
            oauth_token=oauth_token,
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            from_address=username,
            from_name="QAMill"
        )

    def set_office365_config(self, username: str, password: str) -> None:
        """Configure Office 365"""
        self.config = EmailConfig(
            provider=EmailProvider.OFFICE365,
            username=username,
            password=password,
            smtp_server="smtp.office365.com",
            smtp_port=587,
            use_tls=True,
            from_address=username,
            from_name="QAMill"
        )

    def set_custom_smtp_config(
        self,
        smtp_server: str,
        smtp_port: int,
        username: str,
        password: str,
        from_address: str,
        use_tls: bool = True
    ) -> None:
        """Configure custom SMTP"""
        self.config = EmailConfig(
            provider=EmailProvider.CUSTOM_SMTP,
            username=username,
            password=password,
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            use_tls=use_tls,
            from_address=from_address,
            from_name="QAMill"
        )

    async def send_report(
        self,
        to_emails: List[str],
        subject: str,
        report_html: str,
        report_filename: str = "analysis-report.html"
    ) -> bool:
        """Send analysis report via email"""

        if not self.config:
            return False

        message = EmailMessage(
            to=to_emails,
            subject=subject,
            body=f"Please see attached report: {report_filename}",
            html_body=report_html,
            attachments=[{
                "filename": report_filename,
                "content": report_html,
                "content_type": "text/html"
            }]
        )

        return await self.send_email(message)

    async def send_notification(
        self,
        to_emails: List[str],
        title: str,
        message: str,
        action_url: Optional[str] = None
    ) -> bool:
        """Send notification email"""

        if not self.config:
            return False

        html_body = f"""
        <html>
            <body>
                <h2>{title}</h2>
                <p>{message}</p>
                {f'<a href="{action_url}">View Details</a>' if action_url else ''}
            </body>
        </html>
        """

        email_message = EmailMessage(
            to=to_emails,
            subject=title,
            body=message,
            html_body=html_body
        )

        return await self.send_email(email_message)

    async def send_email(self, message: EmailMessage) -> bool:
        """Send email message"""

        if not self.config:
            return False

        self.email_id_counter += 1
        log_entry = EmailLog(
            id=f"email_{self.email_id_counter:04d}",
            message=message,
            provider=self.config.provider,
            status="pending",
            timestamp=datetime.now()
        )

        try:
            # Simulate email sending
            # In real implementation, would use smtplib or aiosmtplib
            await self._send_via_smtp(message)

            log_entry.status = "sent"
            self.log.append(log_entry)
            return True

        except Exception as e:
            log_entry.status = "failed"
            log_entry.error_message = str(e)
            self.log.append(log_entry)
            return False

    async def _send_via_smtp(self, message: EmailMessage) -> None:
        """Send email via SMTP"""

        # In real implementation:
        # 1. Connect to SMTP server
        # 2. Authenticate with credentials
        # 3. Send message
        # 4. Handle attachments
        # 5. Close connection

        await asyncio.sleep(0.1)  # Simulate network delay

    async def send_batch(self, messages: List[EmailMessage]) -> Dict[str, int]:
        """Send multiple emails"""

        results = {"sent": 0, "failed": 0}

        for message in messages:
            success = await self.send_email(message)
            if success:
                results["sent"] += 1
            else:
                results["failed"] += 1

        return results

    async def schedule_email(
        self,
        message: EmailMessage,
        send_at: datetime
    ) -> str:
        """Schedule email for later delivery"""

        # In real implementation, would persist to database
        self.email_id_counter += 1
        scheduled_id = f"scheduled_{self.email_id_counter:04d}"

        return scheduled_id

    def get_email_log(
        self,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[EmailLog]:
        """Get email delivery log"""

        logs = self.log

        if status:
            logs = [l for l in logs if l.status == status]

        return logs[-limit:]

    def get_email_statistics(self) -> Dict[str, Any]:
        """Get email sending statistics"""

        total_sent = sum(1 for l in self.log if l.status == "sent")
        total_failed = sum(1 for l in self.log if l.status == "failed")
        total_emails = len(self.log)

        return {
            "total": total_emails,
            "sent": total_sent,
            "failed": total_failed,
            "success_rate": (total_sent / total_emails * 100) if total_emails > 0 else 0,
            "recent_logs": self.log[-10:] if self.log else []
        }

    def test_configuration(self) -> bool:
        """Test email configuration"""

        if not self.config:
            return False

        # In real implementation, would attempt SMTP connection
        return True

    def get_configuration(self) -> Dict[str, Any]:
        """Get current email configuration"""

        if not self.config:
            return {}

        return {
            "provider": self.config.provider.value,
            "username": self.config.username,
            "from_address": self.config.from_address,
            "from_name": self.config.from_name,
            "smtp_server": self.config.smtp_server,
            "smtp_port": self.config.smtp_port,
            "use_tls": self.config.use_tls
        }


class ScheduledEmailService:
    """Service for managing scheduled email deliveries"""

    def __init__(self, email_service: EmailService):
        self.email_service = email_service
        self.scheduled: Dict[str, Dict[str, Any]] = {}

    async def schedule_report_delivery(
        self,
        to_emails: List[str],
        report_html: str,
        send_at: datetime,
        frequency: Optional[str] = None  # daily, weekly, monthly
    ) -> str:
        """Schedule recurring report delivery"""

        schedule_id = f"schedule_{len(self.scheduled):04d}"

        self.scheduled[schedule_id] = {
            "to_emails": to_emails,
            "report_html": report_html,
            "send_at": send_at,
            "frequency": frequency,
            "created_at": datetime.now(),
            "last_sent": None,
            "next_send": send_at
        }

        return schedule_id

    async def check_scheduled_deliveries(self) -> Dict[str, int]:
        """Check and send due scheduled emails"""

        results = {"sent": 0, "failed": 0}
        now = datetime.now()

        for schedule_id, schedule in self.scheduled.items():
            if schedule["next_send"] <= now:
                success = await self.email_service.send_report(
                    to_emails=schedule["to_emails"],
                    subject="Scheduled QAMill Report",
                    report_html=schedule["report_html"]
                )

                if success:
                    results["sent"] += 1
                    schedule["last_sent"] = now

                    # Calculate next send time
                    if schedule["frequency"] == "daily":
                        from datetime import timedelta
                        schedule["next_send"] = now + timedelta(days=1)
                    elif schedule["frequency"] == "weekly":
                        from datetime import timedelta
                        schedule["next_send"] = now + timedelta(weeks=1)
                    elif schedule["frequency"] == "monthly":
                        from datetime import timedelta
                        schedule["next_send"] = now + timedelta(days=30)
                else:
                    results["failed"] += 1

        return results

    def cancel_schedule(self, schedule_id: str) -> bool:
        """Cancel scheduled email"""

        if schedule_id in self.scheduled:
            del self.scheduled[schedule_id]
            return True

        return False

    def get_schedules(self) -> List[Dict[str, Any]]:
        """Get all scheduled emails"""

        return list(self.scheduled.values())
