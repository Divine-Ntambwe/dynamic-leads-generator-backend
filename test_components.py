"""
Test script to verify components individually
"""
import asyncio
from database import Database
from searchApi import SearchAPI
from queryBuilder import queryBuilder
from queryHarvest import queryHarvest
from utils import hash_url, generate_fingerprint

def test_database():
    print("\n=== Testing Database Connection ===")
    try:
        db = Database()
        count = db.get_school_count()
        print(f"✓ Database connected. Current schools: {count}")
        return True
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False

def test_search_api():
    print("\n=== Testing Search API ===")
    try:
        api = SearchAPI()
        results = api.search_google("test school south africa", start=0)
        print(f"✓ Search API working. Got {len(results)} results")
        if results:
            print(f"  Sample URL: {results[0]}")
        return True
    except Exception as e:
        print(f"✗ Search API error: {e}")
        return False

def test_query_builder():
    print("\n=== Testing Query Builder ===")
    try:
        builder = queryBuilder()
        queries = builder.generate_queries()
        print(f"✓ Generated {len(queries)} queries")
        print(f"  Sample: {queries[0]}")
        return True
    except Exception as e:
        print(f"✗ Query builder error: {e}")
        return False

def test_query_harvest():
    print("\n=== Testing Query Harvester ===")
    try:
        db = Database()
        harvester = queryHarvest(db)
        urls = harvester.harvest_query("primary school Gauteng", max_urls_per_query=10)
        print(f"✓ Harvested {len(urls)} URLs")
        if urls:
            print(f"  Sample: {urls[0]}")
        return True
    except Exception as e:
        print(f"✗ Query harvester error: {e}")
        return False

def test_utils():
    print("\n=== Testing Utilities ===")
    try:
        # Test URL hashing
        url = "https://example.com/school"
        url_hash = hash_url(url)
        print(f"✓ URL hash: {url_hash[:16]}...")
        
        # Test fingerprinting
        school = {
            "name": "Test School",
            "phone": "0123456789",
            "email": "test@school.co.za"
        }
        fingerprint = generate_fingerprint(school)
        print(f"✓ Fingerprint: {fingerprint[:16]}...")
        
        # Test deduplication
        school2 = {
            "name": "TEST SCHOOL",  # Different case
            "phone": "0123456789",
            "email": "TEST@SCHOOL.CO.ZA"  # Different case
        }
        fingerprint2 = generate_fingerprint(school2)
        
        if fingerprint == fingerprint2:
            print(f"✓ Deduplication working (same fingerprint for normalized data)")
        else:
            print(f"✗ Deduplication issue (different fingerprints)")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Utils error: {e}")
        return False

def test_all():
    print("\n" + "="*60)
    print("COMPONENT TESTING")
    print("="*60)
    
    results = {
        "Database": test_database(),
        "Search API": test_search_api(),
        "Query Builder": test_query_builder(),
        "Query Harvester": test_query_harvest(),
        "Utils": test_utils()
    }
    
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    
    for component, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{component:20} {status}")
    
    all_passed = all(results.values())
    print("\n" + "="*60)
    if all_passed:
        print("✓ All tests passed! System ready to run.")
    else:
        print("✗ Some tests failed. Please fix issues before running.")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_all()
