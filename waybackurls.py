#!/usr/bin/env python3

"""waybackurls.py - pure-Python (stdlib only) take on waybackurls.

Fetch all URLs the Wayback Machine (and optionally Common Crawl) knows about
for a domain.

Usage:
    python3 waybackurls.py example.com
    cat domains.txt | python3 waybackurls.py
    python3 waybackurls.py -no-subs -dates example.com
    python3 waybackurls.py -get-versions https://example.com/robots.txt
"""
import argparse
import json
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

UA = "Mozilla/5.0 (compatible; waybackurls.py)"
TIMEOUT = 60


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fmt_date(ts):
    try:
        return datetime.strptime(ts, "%Y%m%d%H%M%S").strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return ts


def get_wayback(domain, no_subs):
    """Return list of (timestamp, url) from the Wayback CDX API."""
    target = domain if no_subs else "*." + domain
    q = urllib.parse.urlencode(
        {"url": target + "/*", "output": "json", "collapse": "urlkey",
         "fl": "timestamp,original"}
    )
    try:
        rows = json.loads(http_get("https://web.archive.org/cdx/search/cdx?" + q))
    except Exception as e:
        print(f"[wayback] {domain}: {e}", file=sys.stderr)
        return []
    return [(r[0], r[1]) for r in rows[1:]]  # skip header row


def get_commoncrawl(domain, no_subs):
    """Return list of (timestamp, url) from the latest Common Crawl index."""
    target = domain if no_subs else "*." + domain
    try:
        indexes = json.loads(http_get("https://index.commoncrawl.org/collinfo.json"))
        api = indexes[0]["cdx-api"]
        q = urllib.parse.urlencode({"url": target + "/*", "output": "json"})
        out = []
        for line in http_get(api + "?" + q).splitlines():
            try:
                d = json.loads(line)
                out.append((d.get("timestamp", ""), d["url"]))
            except (ValueError, KeyError):
                continue
        return out
    except Exception as e:
        print(f"[commoncrawl] {domain}: {e}", file=sys.stderr)
        return []


def get_versions(url):
    """Return Wayback snapshot URLs of distinct versions of a single URL."""
    q = urllib.parse.urlencode(
        {"url": url, "output": "json", "fl": "timestamp,original",
         "filter": "statuscode:200", "collapse": "digest"}
    )
    try:
        rows = json.loads(http_get("https://web.archive.org/cdx/search/cdx?" + q))
    except Exception as e:
        print(f"[versions] {url}: {e}", file=sys.stderr)
        return []
    return [f"https://web.archive.org/web/{r[0]}if_/{r[1]}" for r in rows[1:]]


def process(domain, args):
    if args.get_versions:
        return [(None, u) for u in get_versions(domain)]
    results = get_wayback(domain, args.no_subs)
    if not args.skip_commoncrawl:
        results += get_commoncrawl(domain, args.no_subs)
    return results


def main():
    p = argparse.ArgumentParser(description="Fetch known URLs from the Wayback Machine")
    p.add_argument("domains", nargs="*", help="domains (or URLs with -get-versions); stdin if omitted")
    p.add_argument("-dates", "--dates", action="store_true", help="show snapshot date next to each URL")
    p.add_argument("-no-subs", "--no-subs", action="store_true", help="don't include subdomains")
    p.add_argument("-get-versions", "--get-versions", action="store_true",
                   help="list distinct archived versions of the given URL(s)")
    p.add_argument("-skip-commoncrawl", "--skip-commoncrawl", action="store_true",
                   help="only query the Wayback Machine")
    p.add_argument("-t", "--threads", type=int, default=4, help="concurrent domains (default 4)")
    args = p.parse_args()

    targets = args.domains or [l.strip() for l in sys.stdin if l.strip()]
    if not targets:
        p.print_usage(sys.stderr)
        sys.exit(1)

    seen = set()
    with ThreadPoolExecutor(max_workers=max(1, args.threads)) as ex:
        for results in ex.map(lambda d: process(d, args), targets):
            for ts, url in results:
                if url in seen:
                    continue
                seen.add(url)
                print(f"{fmt_date(ts)} {url}" if args.dates and ts else url)


if __name__ == "__main__":
    main()
