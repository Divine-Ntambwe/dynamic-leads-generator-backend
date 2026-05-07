from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date, timedelta
from auth import verify_token, get_db

router = APIRouter(prefix="/digest", tags=["digest"])


class DigestSettings(BaseModel):
    enabled: bool = True
    recipient_email: Optional[str] = None
    send_time: Optional[str] = None
    job_id: Optional[int] = None
    new_leads: bool = True
    contacted_leads: bool = False


@router.get("/settings")
async def get_digest_settings(
    username: str = Depends(verify_token),
    conn=Depends(get_db),
):
    row = await conn.fetchrow(
        "SELECT * FROM digest_settings WHERE user_email = $1", username
    )
    return dict(row) if row else {}


@router.post("/settings")
async def save_digest_settings(
    body: DigestSettings,
    username: str = Depends(verify_token),
    conn=Depends(get_db),
):
    job_row = None
    if body.job_id:
        job_row = await conn.fetchrow(
            """
            SELECT name, lead_type, location, job_title, target_leads
            FROM jobs
            WHERE id = $1 AND user_email = $2
            """,
            body.job_id, username,
        )
        if not job_row:
            raise HTTPException(status_code=404, detail="Job not found")

    next_date = date.today() + timedelta(days=7)

    await conn.execute(
        """
        INSERT INTO digest_settings (
            user_email, enabled, recipient_email, send_time,
            job_id, job_name, new_leads, contacted_leads,
            location, lead_type, job_title, target_leads,
            next_digest_date, updated_at
        ) VALUES (
            $1, $2, $3, $4,
            $5, $6, $7, $8,
            $9, $10, $11, $12,
            $13, NOW()
        )
        ON CONFLICT (user_email) DO UPDATE SET
            enabled          = EXCLUDED.enabled,
            recipient_email  = EXCLUDED.recipient_email,
            send_time        = EXCLUDED.send_time,
            job_id           = EXCLUDED.job_id,
            job_name         = EXCLUDED.job_name,
            new_leads        = EXCLUDED.new_leads,
            contacted_leads  = EXCLUDED.contacted_leads,
            location         = EXCLUDED.location,
            lead_type        = EXCLUDED.lead_type,
            job_title        = EXCLUDED.job_title,
            target_leads     = EXCLUDED.target_leads,
            next_digest_date = EXCLUDED.next_digest_date,
            updated_at       = NOW()
        """,
        username,
        body.enabled,
        body.recipient_email,
        body.send_time,
        body.job_id,
        job_row["name"] if job_row else None,
        body.new_leads,
        body.contacted_leads,
        job_row["location"] if job_row else None,
        job_row["lead_type"] if job_row else None,
        job_row["job_title"] if job_row else None,
        job_row["target_leads"] if job_row else 0,
        next_date,
    )
    return {
        "message": "Digest settings saved",
        "next_digest_date": next_date.isoformat()
    }


@router.post("/send-now")
async def send_digest_now(
    username: str = Depends(verify_token),
    conn=Depends(get_db),
):
    row = await conn.fetchrow(
        "SELECT * FROM digest_settings WHERE user_email = $1", username
    )
    if not row:
        raise HTTPException(status_code=404, detail="No digest settings found. Save settings first.")

    from jobs.digest_jobs import run_digest_for_user
    await run_digest_for_user(dict(row))
    return {"message": "Digest triggered successfully"}