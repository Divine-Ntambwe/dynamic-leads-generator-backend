import psycopg2
from database import Database

def show_stats():
    db = Database()
    cur = db.conn.cursor()
    
    print("\n" + "="*60)
    print("SCHOOL SCRAPER STATISTICS")
    print("="*60)
    
    # Total schools
    cur.execute("SELECT COUNT(*) FROM schools")
    total = cur.fetchone()[0]
    print(f"\n📊 Total Schools: {total}")
    
    # Schools with contact info
    cur.execute("SELECT COUNT(*) FROM schools WHERE email IS NOT NULL")
    with_email = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM schools WHERE phone IS NOT NULL")
    with_phone = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM schools WHERE email IS NOT NULL AND phone IS NOT NULL")
    with_both = cur.fetchone()[0]
    
    if(with_email > 0):
        print(f"\n📧 With Email: {with_email} ({with_email/total*100:.1f}%)")
    if(with_phone > 0):
        print(f"📞 With Phone: {with_phone} ({with_phone/total*100:.1f}%)")
    if(with_both > 0):
        print(f"✅ With Both: {with_both} ({with_both/total*100:.1f}%)")
    
    # URLs visited
    cur.execute("SELECT COUNT(*) FROM visited_urls")
    urls_visited = cur.fetchone()[0]
    print(f"\n🔗 URLs Visited: {urls_visited}")
    if(urls_visited > 0):
        print(f"📈 Conversion Rate: {total/urls_visited*100:.1f}% (schools per URL)")
    
    # Query progress
    cur.execute("SELECT COUNT(*) FROM query_progress WHERE completed = TRUE")
    completed_queries = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM query_progress")
    total_queries = cur.fetchone()[0]
    
    print(f"\n🔍 Queries Completed: {completed_queries}/{total_queries}")
    
    # Recent additions
    # cur.execute("SELECT COUNT(*) FROM schools WHERE created_at > NOW() - INTERVAL '24 hours'")
    # recent = cur.fetchone()[0]
    # print(f"🆕 Added (Last 24h): {recent}")
    
    # Sample schools
    print(f"\n📋 Sample Schools:")
    cur.execute("SELECT name, email, phone FROM schools WHERE email IS NOT NULL LIMIT 5")
    for idx, (name, email, phone) in enumerate(cur.fetchall(), 1):
        print(f"  {idx}. {name[:50]}")
        print(f"     Email: {email}, Phone: {phone}")
    
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    show_stats()
