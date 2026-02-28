# Deployment Checklist

## ✅ Pre-Deployment Checklist

### 1. Dependencies Installation
- [ ] Python 3.8+ installed
- [ ] PostgreSQL installed and running
- [ ] Install Python packages:
  ```bash
  pip install psycopg2 playwright beautifulsoup4 requests
  ```
- [ ] Install Playwright browser:
  ```bash
  playwright install chromium
  ```

### 2. Database Setup
- [ ] PostgreSQL service running
- [ ] Database created:
  ```sql
  CREATE DATABASE school_scrapper_db;
  ```
- [ ] Database credentials correct in `database.py`:
  - dbname: school_scrapper_db
  - user: postgres
  - password: Infinity
  - host: localhost
- [ ] Run schema initialization:
  ```bash
  python init_db.py
  ```
- [ ] Verify tables created:
  ```sql
  \dt  -- Should show: visited_urls, schools, query_progress
  ```

### 3. API Configuration
- [ ] SerpAPI key valid (check at https://serpapi.com/dashboard)
- [ ] API key updated in `searchApi.py` or `config.py`
- [ ] Test API with sample query:
  ```bash
  python test_components.py
  ```

### 4. Configuration Review
- [ ] `TARGET_SCHOOLS` set in `main.py` (default: 2000)
- [ ] `MAX_URLS_PER_QUERY` appropriate in `config.py` (default: 100)
- [ ] `BROWSER_HEADLESS` set correctly (True for production)
- [ ] `EXCLUDED_DOMAINS` list reviewed

### 5. System Test
- [ ] Run component tests:
  ```bash
  python test_components.py
  ```
- [ ] All tests pass:
  - ✓ Database connection
  - ✓ Search API
  - ✓ Query builder
  - ✓ Query harvester
  - ✓ Utils (hashing & fingerprinting)

## 🚀 Deployment Steps

### Step 1: Initial Run
```bash
python main.py
```

### Step 2: Monitor Progress
Open second terminal:
```bash
# Watch progress in real-time
watch -n 10 python stats.py

# Or manually check
python stats.py
```

### Step 3: Database Monitoring
```sql
-- Check total schools
SELECT COUNT(*) FROM schools;

-- Check data quality
SELECT 
  COUNT(*) as total,
  COUNT(email) as with_email,
  COUNT(phone) as with_phone,
  COUNT(CASE WHEN email IS NOT NULL AND phone IS NOT NULL THEN 1 END) as with_both
FROM schools;

-- Check query progress
SELECT 
  COUNT(*) as total_queries,
  COUNT(CASE WHEN completed THEN 1 END) as completed,
  COUNT(CASE WHEN NOT completed THEN 1 END) as in_progress
FROM query_progress;
```

## 🔍 Verification Checklist

### Data Quality Checks
- [ ] Schools have names (should be 100%)
- [ ] At least 30% have email addresses
- [ ] At least 30% have phone numbers
- [ ] No duplicate fingerprints:
  ```sql
  SELECT fingerprint, COUNT(*) 
  FROM schools 
  GROUP BY fingerprint 
  HAVING COUNT(*) > 1;
  -- Should return 0 rows
  ```
- [ ] No duplicate URL hashes:
  ```sql
  SELECT url_hash, COUNT(*) 
  FROM visited_urls 
  GROUP BY url_hash 
  HAVING COUNT(*) > 1;
  -- Should return 0 rows
  ```

### System Health Checks
- [ ] No errors in console output
- [ ] Progress increasing steadily
- [ ] Memory usage stable (< 2GB)
- [ ] Disk space sufficient (> 1GB free)
- [ ] Network connectivity stable

## 🛠️ Troubleshooting Guide

### Issue: Database Connection Error
**Symptoms**: `psycopg2.OperationalError`
**Solutions**:
- [ ] Check PostgreSQL is running: `pg_ctl status`
- [ ] Verify credentials in `database.py`
- [ ] Test connection: `psql -U postgres -d school_scrapper_db`

### Issue: SerpAPI Quota Exceeded
**Symptoms**: "API quota exceeded" or empty results
**Solutions**:
- [ ] Check quota at https://serpapi.com/dashboard
- [ ] Upgrade plan or wait for reset
- [ ] Reduce `MAX_URLS_PER_QUERY` temporarily

### Issue: Playwright Browser Error
**Symptoms**: Browser launch fails
**Solutions**:
- [ ] Reinstall browser: `playwright install chromium`
- [ ] Check disk space
- [ ] Try headless=False for debugging

### Issue: No Schools Extracted
**Symptoms**: URLs scraped but 0 schools inserted
**Solutions**:
- [ ] Check extractor regex patterns
- [ ] Verify websites are accessible
- [ ] Review excluded domains list
- [ ] Check sample URLs manually

### Issue: Slow Performance
**Symptoms**: < 10 schools per minute
**Solutions**:
- [ ] Check network speed
- [ ] Verify database indexes exist
- [ ] Reduce `PAGE_TIMEOUT` if sites are slow
- [ ] Check system resources (CPU, RAM)

### Issue: Duplicate Schools Appearing
**Symptoms**: Same school multiple times
**Solutions**:
- [ ] Verify UNIQUE constraint on fingerprint
- [ ] Check fingerprint generation logic
- [ ] Review normalization function
- [ ] Rebuild database if needed

## 📊 Success Metrics

### Minimum Acceptable
- [ ] Target schools reached (e.g., 2000)
- [ ] At least 25% have email
- [ ] At least 25% have phone
- [ ] Zero duplicates (by fingerprint)
- [ ] Completion time < 6 hours

### Good Performance
- [ ] 40%+ have email
- [ ] 40%+ have phone
- [ ] 20%+ have both
- [ ] Completion time < 4 hours
- [ ] < 5% error rate on URLs

### Excellent Performance
- [ ] 50%+ have email
- [ ] 50%+ have phone
- [ ] 30%+ have both
- [ ] Completion time < 3 hours
- [ ] < 2% error rate on URLs

## 🔄 Post-Deployment

### Data Export
```sql
-- Export to CSV
COPY schools TO '/tmp/schools.csv' CSV HEADER;

-- Export with filters
COPY (
  SELECT name, email, phone, website 
  FROM schools 
  WHERE email IS NOT NULL AND phone IS NOT NULL
) TO '/tmp/schools_complete.csv' CSV HEADER;
```

### Backup Database
```bash
pg_dump school_scrapper_db > backup_$(date +%Y%m%d).sql
```

### Clean Up (Optional)
```sql
-- Remove URLs without schools (optional)
DELETE FROM visited_urls 
WHERE url NOT IN (SELECT website FROM schools);

-- Archive old query progress
DELETE FROM query_progress WHERE completed = TRUE;
```

### Schedule Regular Runs
```bash
# Add to crontab for weekly runs
0 2 * * 0 cd /path/to/school_scrapper_app && python main.py >> scraper.log 2>&1
```

## 📝 Final Verification

Before considering deployment complete:
- [ ] Target number of schools reached
- [ ] Data quality meets requirements
- [ ] No duplicate records
- [ ] Database backed up
- [ ] Documentation reviewed
- [ ] Stats.py shows expected metrics
- [ ] Sample data manually verified
- [ ] Export successful

## 🎯 Ready to Deploy?

If all checkboxes above are checked:
✅ **System is ready for production use**

If any checkboxes are unchecked:
⚠️ **Review and complete missing items before deployment**

---

**Deployment Date**: _____________
**Deployed By**: _____________
**Target Schools**: _____________
**Actual Schools**: _____________
**Success**: ☐ Yes  ☐ No
**Notes**: _____________________________________________
