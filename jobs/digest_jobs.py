from datetime import date, timedelta
from mailer import send_email
from database import Database

FRONTEND_URL = "https://dynamic-leads-generator-frontend-iota.vercel.app/"


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

        from orchestrator import ScraperOrchestrator
        orchestrator = ScraperOrchestrator(job_params, job_id)
        leads_found = await orchestrator.run()

        leads_found = leads_found or 0  # ← ensure never None

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


def _build_html_email(job_id, job_name, leads_found, contacted_count, row):
    """
    Builds a branded HTML email that matches the Dynamic Lead Engine app aesthetic:
    cream background, dark ink header, coral accent, JetBrains Mono labels.
    """

    today_str = date.today().strftime("%A, %d %B %Y")
    lead_type = (row.get("lead_type") or "").capitalize()

    # ── Stat blocks ───────────────────────────────────────────────────────────
    stat_blocks = ""

    if row.get("new_leads", True):
        stat_blocks += f"""
        <td style="width:50%;padding:0 6px 0 0;">
          <div style="background:#ffffff;border:1px solid #e3e0dd;border-radius:6px;
                      padding:20px 22px;text-align:center;">
            <div style="font-family:'Courier New',Courier,monospace;font-size:10px;
                        letter-spacing:2px;color:#726965;text-transform:uppercase;
                        margin-bottom:10px;">New Leads</div>
            <div style="font-size:40px;font-weight:300;color:#1d1816;line-height:1;">
              {leads_found}
            </div>
            <div style="font-size:11px;color:#726965;margin-top:6px;">
              scraped this week
            </div>
          </div>
        </td>"""

    if row.get("contacted_leads", False) and contacted_count is not None:
        stat_blocks += f"""
        <td style="width:50%;padding:0 0 0 6px;">
          <div style="background:#ffffff;border:1px solid #e3e0dd;border-radius:6px;
                      padding:20px 22px;text-align:center;">
            <div style="font-family:'Courier New',Courier,monospace;font-size:10px;
                        letter-spacing:2px;color:#726965;text-transform:uppercase;
                        margin-bottom:10px;">Contacted</div>
            <div style="font-size:40px;font-weight:300;color:#1d1816;line-height:1;">
              {contacted_count}
            </div>
            <div style="font-size:11px;color:#726965;margin-top:6px;">
              leads marked this week
            </div>
          </div>
        </td>"""

    stats_row = f"""
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
      <tr>{stat_blocks}</tr>
    </table>""" if stat_blocks else ""

    # ── Job meta pill ─────────────────────────────────────────────────────────
    job_meta = ""
    if lead_type:
        job_meta = f"""
        <table width="100%" cellpadding="0" cellspacing="0"
               style="background:#f7f5f3;border:1px solid #e3e0dd;border-radius:6px;
                      margin-bottom:28px;">
          <tr>
            <td style="padding:14px 18px;border-right:1px solid #e3e0dd;width:33%;">
              <div style="font-family:'Courier New',Courier,monospace;font-size:9px;
                          letter-spacing:1.5px;color:#726965;text-transform:uppercase;
                          margin-bottom:4px;">Lead Type</div>
              <div style="font-size:13px;font-weight:500;color:#1d1816;">{lead_type}</div>
            </td>
            <td style="padding:14px 18px;border-right:1px solid #e3e0dd;width:33%;">
              <div style="font-family:'Courier New',Courier,monospace;font-size:9px;
                          letter-spacing:1.5px;color:#726965;text-transform:uppercase;
                          margin-bottom:4px;">Job</div>
              <div style="font-size:13px;font-weight:500;color:#1d1816;
                          white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
                          max-width:140px;">{job_name}</div>
            </td>
            <td style="padding:14px 18px;width:33%;">
              <div style="font-family:'Courier New',Courier,monospace;font-size:9px;
                          letter-spacing:1.5px;color:#726965;text-transform:uppercase;
                          margin-bottom:4px;">Run Date</div>
              <div style="font-size:13px;font-weight:500;color:#1d1816;">{today_str}</div>
            </td>
          </tr>
        </table>"""

    # ── No-data fallback ──────────────────────────────────────────────────────
    if not stat_blocks:
        stats_row = """
        <div style="background:#fff8f5;border:1px solid #f0ddd3;border-radius:6px;
                    padding:16px 18px;margin-bottom:24px;font-size:13px;color:#726965;">
          No data to report this week.
        </div>"""

    # ── Full HTML ─────────────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1.0" />
  <title>Your Weekly Leads Digest</title>
</head>
<body style="margin:0;padding:0;background-color:#fbfaf9;
             font-family:'Helvetica Neue',Arial,sans-serif;color:#1d1816;">

  <!-- Outer wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0"
         style="background:#fbfaf9;padding:40px 16px 60px;">
    <tr>
      <td align="center">

        <!-- Card -->
        <table width="100%" cellpadding="0" cellspacing="0"
               style="max-width:600px;">

          <!-- ── Header bar ───────────────────────────────────────────── -->
          <tr>
            <td style="background:#1d1816;border-radius:8px 8px 0 0;
                        padding:28px 36px 26px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <!-- Coral label -->
                    <div style="margin-bottom:14px;">
                      <span style="display:inline-block;width:24px;height:1px;
                                   background:#ce673b;margin-right:8px;
                                   vertical-align:middle;"></span>
                      <span style="font-family:'Courier New',Courier,monospace;
                                   font-size:10px;letter-spacing:2.5px;color:#ce673b;
                                   text-transform:uppercase;vertical-align:middle;">
                        Weekly Digest
                      </span>
                    </div>
                    <!-- Big heading -->
                    <div style="font-size:32px;font-weight:300;color:#fbfaf9;
                                line-height:1.1;letter-spacing:-0.02em;margin-bottom:10px;">
                      Your leads are<br/>ready.
                    </div>
                    <div style="font-size:12px;color:#a09894;">
                      {today_str}
                    </div>
                  </td>
                  <td align="right" valign="top">
                    <!-- DLE monogram -->
                    <div style="width:44px;height:44px;border:1px solid #3a3532;
                                border-radius:4px;display:inline-block;
                                text-align:center;line-height:44px;">
                      <span style="font-family:'Courier New',Courier,monospace;
                                   font-size:11px;color:#726965;letter-spacing:1px;">
                        DLE
                      </span>
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ── Body ────────────────────────────────────────────────── -->
          <tr>
            <td style="background:#ffffff;padding:32px 36px 28px;
                        border-left:1px solid #e3e0dd;border-right:1px solid #e3e0dd;">

              <!-- Intro line -->
              <p style="font-size:14px;color:#726965;margin:0 0 28px;line-height:1.6;">
                The weekly scrape for <strong style="color:#1d1816;">{job_name}</strong>
                has completed. Here's a summary of this week's activity.
              </p>

              <!-- Stat cards -->
              {stats_row}

              <!-- Job meta pill -->
              {job_meta}

              <!-- CTA button -->
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <a href="{FRONTEND_URL}"
                       style="display:inline-block;background:#1d1816;color:#fbfaf9;
                              text-decoration:none;font-size:13px;font-weight:500;
                              padding:13px 28px;border-radius:3px;letter-spacing:0.2px;">
                      View dashboard &rarr;
                    </a>
                  </td>
                </tr>
              </table>

            </td>
          </tr>

          <!-- ── Divider strip ────────────────────────────────────────── -->
          <tr>
            <td style="height:3px;background:linear-gradient(90deg,#ce673b 0%,#1d1816 100%);"></td>
          </tr>

          <!-- ── Footer ───────────────────────────────────────────────── -->
          <tr>
            <td style="background:#f7f5f3;border:1px solid #e3e0dd;border-top:none;
                        border-radius:0 0 8px 8px;padding:20px 36px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <span style="font-family:'Courier New',Courier,monospace;
                                 font-size:11px;color:#1d1816;font-weight:500;
                                 letter-spacing:0.5px;">
                      Dynamic Lead Engine
                    </span>
                    <br/>
                    <span style="font-size:11px;color:#a09894;">
                      Automated weekly digest — manage your settings at
                      <a href="{FRONTEND_URL}"
                         style="color:#ce673b;text-decoration:none;">
                        dynamicleadengine.app
                      </a>.
                    </span>
                  </td>
                  <td align="right" valign="middle">
                    <span style="font-family:'Courier New',Courier,monospace;
                                 font-size:10px;color:#c0bbb8;letter-spacing:1px;">
                      #{job_id}
                    </span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

        </table>
        <!-- /Card -->

      </td>
    </tr>
  </table>

</body>
</html>"""

    return html


def _send_summary_email(to, job_id, job_name, leads_found, row):
    contacted_count = None

    if row.get("contacted_leads", False):
        try:
            db = Database()
            cur = db.conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM leads WHERE job_id = %s AND marked = true",
                (job_id,)
            )
            result = cur.fetchone()
            contacted_count = result[0] if result else 0
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


async def run_weekly_digests(pool):
    today = date.today()
    print(f"[Digest] Checking for due digests — {today}")

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM digest_settings
            WHERE enabled = TRUE
              AND next_digest_date <= $1
            """,
            today,
        )

        if not rows:
            print("[Digest] No digests due today.")
            return

        print(f"[Digest] {len(rows)} digest(s) to run.")

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