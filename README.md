# waybackurls

waybackurls.py - pure-Python (stdlib only) take on waybackurls.
 
Fetch all URLs the Wayback Machine (and optionally Common Crawl) knows about for a domain.

Usage:
    
    python3 waybackurls.py example.com
    cat domains.txt | python3 waybackurls.py
    python3 waybackurls.py -no-subs -dates example.com
    python3 waybackurls.py -get-versions https://example.com/robots.txt
  
