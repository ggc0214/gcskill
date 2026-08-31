# Standard-status SQLite cache

Use `scripts/standard_cache.py` to avoid repeating authoritative status lookups while preserving freshness and full-report coverage. This cache belongs to this Skill; it is independent of the 8787 application's cache.

## Required workflow

1. Finish the complete canonical standard inventory first. The cache must never determine which standards are in scope.
2. Run `prepare-run` on that full inventory. Use its canonical, deduplicated list as the one-per-audit lookup set.
3. Run `get` once for each canonical standard.
4. Reuse only `decision: fresh`.
5. For `miss` or `refresh_required`, query the authoritative online source.
6. After an authoritative exact hit, run `put` with all available dates, replacement number, official link, verification time, and a concise summary.
7. If the official source times out or has no exact hit, run `record-failure`. Never store that failure as a reusable status result.
8. Reconcile the complete report inventory with final status rows exactly as required by `audit-rules.md`.

## Reuse and refresh policy

- National and industry standards: reuse authoritative cache records for 30 days.
- Enterprise and group standards: reuse authoritative cache records for 7 days.
- If an effective, abolishment, or replacement event is within 60 days, force an online refresh even when the normal TTL has not expired.
- If an event date passed after the cached verification date, force refresh.
- Expired cache records require an online refresh before they can be presented as current.
- `官方接口超时/未命中` is an attempt outcome, not a cacheable current-status result; query it again in the next audit.
- The same canonical standard number is queried at most once during one audit.

## Network-failure fallback

When a live lookup fails and an older authoritative record exists, it may be used only as a stale fallback. Display both:

- the cached status;
- `网络查询失败；使用历史缓存，缓存核验日期：YYYY-MM-DD。`

Do not call the cached status the latest result. If no prior authoritative cache exists, output `官方接口超时/未命中` and retain manual verification.

## Stored fields

The SQLite record stores: canonical standard number, type, current status, publication date, effective date, abolishment or replacement date, replacement standard number, official source URL, last verification time, result summary, and internal update time. Failed lookup attempts are recorded separately and never overwrite an authoritative record.

## CLI examples

The default database is `%CODEX_HOME%\state\product-compliance-review\standard_status.sqlite3`, or `%USERPROFILE%\.codex\state\product-compliance-review\standard_status.sqlite3` when `CODEX_HOME` is unset. Use `--db` before the subcommand to select another file.

```powershell
python scripts/standard_cache.py prepare-run --standards-json '["GB/T8629-2017","GB/T 8629-2017"]'
python scripts/standard_cache.py get --standard "GB/T 8629-2017" --now "2026-08-28T00:00:00Z"
python scripts/standard_cache.py put --standard "GB/T 8629-2017" --type national --status "现行" --publish-date "2017-12-29" --effective-date "2018-07-01" --source-url "https://std.samr.gov.cn/..." --checked-at "2026-08-28T00:00:00Z" --summary "官方精确命中"
python scripts/standard_cache.py record-failure --standard "GB/T 8629-2017" --type national --attempted-at "2026-08-28T00:00:00Z" --summary "官方接口超时/未命中"
```

The assistant must use actual current timestamps, not the example dates above.

