import os
from datetime import date, timedelta, datetime
from mailer import send_email
from database import Database

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "https://dynamic-leads-generator-frontend-iota.vercel.app"
)


async def run_digest_for_user(row: dict):
    user_email = row["user_email"]
    recipient  = row["recipient_email"] or user_email

    job_params = {
        "email":           user_email,
        "job_name":        f"[Weekly Digest] {row.get('job_name') or 'Auto-run'}",
        "lead_type":       row.get("lead_type"),
        "location":        row.get("location"),
        "job_title":       row.get("job_title") or "",
        "target_num":      row.get("target_leads") or 0,
        "industry":        row.get("industry") or "",
        "custom_keywords": row.get("custom") or "",
    }

    print(f"[Digest] Running scrape for {user_email}")

    try:
        db = Database()
        job_id = db.create_job(job_params)
        print(f"[Digest] Created job {job_id}")

        # ← Clear previously visited URLs for this query so digest always re-scrapes fresh
        cur = db.conn.cursor()
        cur.execute(
            "DELETE FROM visited_urls WHERE query LIKE %s",
            (f"%{row.get('industry') or ''}%",)
        )
        db.conn.commit()
        cur.close()
        print(f"[Digest] Cleared visited URLs for fresh scrape")

        from orchestrator import ScraperOrchestrator
        orchestrator = ScraperOrchestrator(job_params, job_id)
        await orchestrator.run()

        # Read actual count from DB
        leads_found = db.get_leads_count(job_id)
        leads_found = leads_found or 0

        db.mark_job_completed(job_id, "complete", leads_found)
        print(f"[Digest] Job {job_id} complete — {leads_found} leads found")

        _send_summary_email(
            to=recipient,
            job_id=job_id,
            job_name=job_params["job_name"],
            leads_found=leads_found,
            row=row,
        )

    except Exception as e:
        print(f"[Digest] Error for {user_email}: {e}")


def _send_summary_email(to, job_id, job_name, leads_found, row):
    contacted_count = None

    if row.get("contacted_leads", False):
        try:
            db = Database()
            cur = db.conn.cursor()
            # ← Query ALL jobs for this user, not just the current digest job
            cur.execute(
                """
                SELECT COUNT(*) FROM leads l
                JOIN jobs j ON l.job_id = j.id
                WHERE j.user_email = %s AND l.marked = true
                """,
                (row["user_email"],)
            )
            result = cur.fetchone()
            contacted_count = result[0] if result else 0
            cur.close()
        except Exception as e:
            print(f"[Digest] Could not fetch contacted count: {e}")

    # Plain-text fallback
    lines = []
    if row.get("new_leads", True):
        lines.append(f"New leads scraped this week: {leads_found}")
    if contacted_count is not None:
        lines.append(f"Leads marked as contacted: {contacted_count}")
    content = "\n".join(lines) if lines else "No data to report this week."

    plain_body = f"""Hi there,

Your weekly lead digest is ready.

Job: {job_name}

{content}

Log in to review your leads:
{FRONTEND_URL}

—
Dynamic Lead Engine
"""

    html_body = _build_html_email(
        job_id=job_id,
        job_name=job_name,
        leads_found=leads_found,
        contacted_count=contacted_count,
        row=row,
    )

    send_email(
        to=to,
        subject="Your Weekly Leads Digest",
        body=plain_body,
        html_body=html_body,
    )
    print(f"[Digest] Email sent to {to}")


def _build_html_email(job_id, job_name, leads_found, contacted_count, row):
    new_leads_row = ""
    if row.get("new_leads", True):
        new_leads_row = f"""
        <tr>
          <td style="padding:12px 0;border-bottom:1px solid #f0ede9;color:#726965;font-size:14px;">
            New leads scraped
          </td>
          <td style="padding:12px 0;border-bottom:1px solid #f0ede9;text-align:right;font-size:14px;font-weight:600;color:#1d1816;">
            {leads_found}
          </td>
        </tr>
        """

    contacted_row = ""
    if contacted_count is not None:
        contacted_row = f"""
        <tr>
          <td style="padding:12px 0;color:#726965;font-size:14px;">
            Leads marked as contacted
          </td>
          <td style="padding:12px 0;text-align:right;font-size:14px;font-weight:600;color:#1d1816;">
            {contacted_count}
          </td>
        </tr>
        """

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>Weekly Leads Digest</title>
</head>
<body style="margin:0;padding:0;background:#fbfaf9;font-family:'Inter',Arial,sans-serif;color:#1d1816;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#fbfaf9;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0"
               style="max-width:600px;width:100%;background:#ffffff;border:1px solid #e3e0dd;border-radius:8px;overflow:hidden;">

          <!-- Header -->
          <tr>
            <td style="background:#1d1816;padding:32px 40px;">
              <p style="margin:0;font-size:11px;letter-spacing:2.4px;color:#ce673b;text-transform:uppercase;font-family:monospace;">
                Weekly Digest
              </p>
              <h1 style="margin:12px 0 0;font-size:28px;font-weight:400;color:#fbfaf9;line-height:1.15;">
                Your leads are ready.
              </h1>
            </td>
          </tr>

          <!-- Job name -->
          <tr>
            <td style="padding:28px 40px 0;">
              <p style="margin:0;font-size:11px;letter-spacing:1.5px;color:#726965;text-transform:uppercase;font-family:monospace;">
                Job
              </p>
              <p style="margin:6px 0 0;font-size:18px;font-weight:500;color:#1d1816;">
                {job_name}
              </p>
            </td>
          </tr>

          <!-- Stats table -->
          <tr>
            <td style="padding:24px 40px;">
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="border:1px solid #e3e0dd;border-radius:6px;padding:0 16px;background:#fbfaf9;">
                <tr>
                  <td colspan="2" style="padding:14px 0 4px;">
                    <p style="margin:0;font-size:11px;letter-spacing:1.5px;color:#726965;text-transform:uppercase;font-family:monospace;">
                      Summary
                    </p>
                  </td>
                </tr>
                {new_leads_row}
                {contacted_row}
              </table>
            </td>
          </tr>

          <!-- CTA button -->
          <tr>
            <td style="padding:0 40px 36px;">
              <a href="{FRONTEND_URL}"
                 style="display:inline-block;background:#1d1816;color:#fbfaf9;text-decoration:none;
                        padding:12px 24px;border-radius:4px;font-size:14px;font-weight:500;">
                View your leads →
              </a>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:20px 40px;border-top:1px solid #e3e0dd;">
              <p style="margin:0;font-size:12px;color:#726965;">
                Dynamic Lead Engine · Weekly digest
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


async def run_weekly_digests(pool):
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    today = date.today()

    print(f"[Digest] Tick — {current_time}")

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM digest_settings
            WHERE enabled = TRUE
              AND next_digest_date <= $1
              AND send_time = $2
            """,
            today,
            current_time,
        )

        if not rows:
            return

        print(f"[Digest] {len(rows)} digest(s) due at {current_time}")

        for row in rows:
            row_dict = dict(row)
            await run_digest_for_user(row_dict)

            new_next = today + timedelta(days=7)
            await conn.execute(
                """
                UPDATE digest_settings
                SET next_digest_date = $1, updated_at = NOW()
                WHERE user_email = $2
                """,
                new_next,
                row_dict["user_email"],
            )
            print(f"[Digest] Next digest for {row_dict['user_email']} → {new_next}")