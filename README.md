# kfood-journal
Korean food journal website

## Quality and revenue-safe monitoring

Run `python3 scripts/verify_site.py` before deployment. Recurring availability checks must read `audit-manifest.json` and use HTTP-only requests such as `curl`; they should not open live pages in a JavaScript browser because doing so can pollute AdSense and Analytics traffic.

Analytics separates a plain page load from an `engaged_reader`. The latter is sent only after a visible visitor interacts, stays for at least 20 seconds, and reaches 50% scroll depth. Language switches and outbound clicks are also tracked without collecting link text or personal data.
