# ai_server/infra/email_utils.py
import logging
from email.mime.text import MIMEText

import aiosmtplib

from ai_server.config import get_settings

logger = logging.getLogger(__name__)


async def send_completion_email(to: str, product_id: str, result_text: str) -> None:
    """장기 이력 분석 완료 알림 이메일 발송.

    SMTP 설정이 없으면 조용히 skip.
    발송 실패 시 예외를 raise하지 않고 로그만 남김 (분석 결과에 영향 없음).
    """
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_user:
        print("[EMAIL] SMTP 설정 없음 — 이메일 알림 skip")
        logger.debug("SMTP 설정 없음 — 이메일 알림 skip")
        return

    subject = f"[분석 완료 알림] {product_id} 장기 이력 분석이 완료되었습니다"
    body = (
        f"안녕하세요,\n\n"
        f"요청하신 '{product_id}' 제품의 장기 이력 분석이 완료되었습니다.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f" 분석 결과\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{result_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"자세한 내용은 Display Defect Analyzer 시스템에서 확인하실 수 있습니다.\n\n"
        f"본 메일은 자동 발송된 알림 메일입니다.\n"
    )

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to

    print(f"[EMAIL] 발송 시도: {settings.smtp_user} → {to} (host={settings.smtp_host}:{settings.smtp_port})")
    logger.info("이메일 발송 시도 → %s", to)
    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
        print(f"[EMAIL] 발송 완료 → {to}")
        logger.info("이메일 알림 발송 완료 → %s", to)
    except Exception as exc:
        print(f"[EMAIL] 발송 실패: {exc}")
        logger.warning("이메일 발송 실패 (무시): %s", exc)
