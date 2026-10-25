"""Windows-friendly command line. Only the transcribe command can call Gemini."""
import argparse
import json
from pathlib import Path
import sys
from . import __version__
from .config import load_config
from .discovery import discover
from .execution import transcribe
from .exports import export_all
from .images import prepare_request
from .profiles import load_profile, register_profile
from .prompt import known_correspondents
from .provider import Gemini, api_key
from .relationships import match
from .review import apply_review, current_records, people
from .storage import Store, identity, lock, read_json
from .usage import aggregate, read_usage
from .publication import publication_state, publish_text
from .relocation import reconcile_paths


def parser():
    p = argparse.ArgumentParser(description="Historical museum correspondence: local inventory, transcription, review and export.")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--store", default="local/collection", help="Durable local store (outside input root)")
    p.add_argument("--config", help="JSON operational settings; defaults require no file")
    commands = p.add_subparsers(dest="command", required=True)
    for name in ("inventory", "dry-run"):
        sub = commands.add_parser(name, help="Discover scans and save inventory" if name == "inventory"
                                  else "Read-only discovery, integrity, grouping and payload checks")
        sub.add_argument("--input", default="test/inputs")
        sub.add_argument("--overrides", help="Reviewed grouping/order JSON")
        if name == "dry-run":
            sub.add_argument("--profile")
        else:
            sub.add_argument("--output", default="local/exports")
    sub = commands.add_parser("transcribe", help="Explicit Gemini requests or eligible 48-hour cache reuse")
    scope = sub.add_mutually_exclusive_group(required=True)
    scope.add_argument("--all", action="store_true")
    scope.add_argument("--pending", action="store_true", help="Only letters without a current complete result, regardless of cache age")
    scope.add_argument("--letter", action="append", help="Stable letter ID; repeat for multiple letters")
    sub.add_argument("--fresh", action="store_true", help="Bypass completed cache; retain all history")
    sub.add_argument("--retry-interrupted", action="store_true", help="Accept possible repeat charges after unknown outcome")
    sub.add_argument("--env-file", help="Explicit credential file; otherwise environment only")
    sub.add_argument("--profile", help="Explicit approved handwriting context, frozen for this batch")
    sub.add_argument("--output", default="local/exports")
    sub.add_argument("--publish-text", action="store_true", help="Enable managed text copies beside source scans for this store")
    sub = commands.add_parser("export", help="Regenerate all reports/CSV/viewer from saved records; zero requests")
    sub.add_argument("--output", default="local/exports")
    sub.add_argument("--mapping", help="Reviewed image-ID to Drive-file-ID mapping")
    sub.add_argument("--publish-text", action="store_true", help="Enable managed text copies beside source scans for this store")
    sub = commands.add_parser("reconcile-paths", help="Record explicitly mapped external scan renames after verifying unchanged bytes")
    sub.add_argument("--file", required=True, help="Local JSON with version, source and paths")
    commands.add_parser("match", help="Local relationship candidates across all saved letters")
    sub = commands.add_parser("review", help="Append a human correction, person identity, or link decision")
    sub.add_argument("--file", required=True)
    sub = commands.add_parser("show", help="Inspect saved inventory/current record; zero requests")
    sub.add_argument("--letter")
    return p


def print_inventory(inventory):
    images = {i["image_id"]: i for i in inventory["images"]}
    for letter in inventory["letters"]:
        print(f"{letter['letter_id']}  {letter['grouping']}  {len(letter['image_ids'])} page(s)")
        for iid in letter["image_ids"]:
            print(f"  {iid}  {images[iid]['path']}  [{images[iid]['status']}]")
        for reason in letter["review_reasons"]:
            print(f"  REVIEW: {reason}")


def require_inventory(store):
    inventory = store.latest("inventory")
    if inventory is None:
        raise ValueError("No inventory. Run inventory --input PATH first.")
    return inventory


def safe_destinations(inventory, *paths):
    root = Path(inventory["input_root"]).resolve()
    for path in paths:
        if Path(path).resolve().is_relative_to(root):
            raise ValueError("Store, exports and quota must be outside source scans")


def refresh_exports(store, inventory, args):
    count = export_all(store, inventory, args.output, read_json(args.mapping) if getattr(args, "mapping", None) else None)
    if getattr(args, "publish_text", False) or publication_state(store, inventory):
        total = publish_text(store, inventory, args.output)
        print(f"Saved {total} reader/viewer files beside scans in {inventory['input_root']}")
    return count


def run(args):
    config = load_config(args.config)
    store = Store(args.store)
    if args.command in {"dry-run", "inventory"}:
        previous = store.latest("inventory")
        override = read_json(args.overrides) if args.overrides else (previous or {}).get("overrides")
        if args.overrides and override is None:
            raise ValueError("Override file not found")
        state = publication_state(store, previous) if previous else {}
        inventory = discover(args.input, previous, override, state.get("files", {}))
        safe_destinations(inventory, store.root, config.quota_file)
        if args.command == "dry-run":
            profile = load_profile(args.profile)
            correspondents = known_correspondents(people(store))
            print_inventory(inventory)
            failures = 0
            for letter in inventory["letters"]:
                if not letter["active"]:
                    continue
                try:
                    request = prepare_request(inventory, letter, config, profile, correspondents=correspondents)
                    print(f"READY {letter['letter_id']}: {request['estimated_bytes']:,} estimated bytes; "
                          f"fingerprint {request['fingerprint']}")
                except (ValueError, OSError) as exc:
                    failures += 1
                    print(f"BLOCKED {letter['letter_id']}: {exc}")
            print("Read-only dry run: zero requests; no reports, journal changes, or quota reservations.")
            return int(bool(failures))
        safe_destinations(inventory, args.output)
        with lock(store.root / "store.lock"):
            # Refuse to overwrite a concurrent inventory computed before acquiring the lock.
            if store.latest("inventory") != previous:
                raise ValueError("Inventory changed concurrently; rerun")
            store.append("inventory", inventory)
            refresh_exports(store, inventory, args)
        print_inventory(inventory)
        print(f"Saved inventory and offline exports to {args.output}")
        return 0
    inventory = require_inventory(store)
    safe_destinations(inventory, store.root, config.quota_file)
    if args.command == "show":
        if args.letter:
            value = next((r for r in current_records(store, inventory) if r["letter_id"] == args.letter), None)
            if value is None:
                raise ValueError("Unknown letter ID")
            print(json.dumps(value, ensure_ascii=False, indent=2))
        else:
            print_inventory(inventory)
        return 0
    with lock(store.root / "store.lock"):
        inventory = require_inventory(store)
        if args.command == "reconcile-paths":
            updated = reconcile_paths(inventory, read_json(args.file))
            store.append("inventory", updated)
            print("Recorded verified source path changes. Scan bytes, IDs, prior responses and reviews are preserved.")
        elif args.command == "export":
            if args.mapping and not Path(args.mapping).exists():
                raise ValueError("Mapping file not found")
            count = refresh_exports(store, inventory, args)
            print(f"Exported {count} records to {args.output}; zero requests.")
        elif args.command == "review":
            patch = read_json(args.file)
            if not isinstance(patch, dict):
                raise ValueError("Review JSON file not found or invalid")
            event = apply_review(store, inventory, patch)
            print(json.dumps(event, ensure_ascii=False, indent=2))
        elif args.command == "match":
            matching = match(current_records(store, inventory))
            store.append("matching", matching)
            print(f"{len(matching['candidates'])} proposed links; {len(matching['unresolved'])} unresolved references. "
                  "No automatic confirmations; run export to refresh the viewer.")
        elif args.command == "transcribe":
            safe_destinations(inventory, args.output)
            complete = {r["letter_id"] for r in current_records(store, inventory) if r["execution"] == "complete"}
            selected = [l for l in inventory["letters"] if l["active"]
                        and (args.all or (args.pending and l["letter_id"] not in complete)
                             or (args.letter and l["letter_id"] in args.letter))]
            if args.letter and set(args.letter) != {l["letter_id"] for l in selected}:
                raise ValueError("Unknown or retired selected letter ID")
            profile = load_profile(args.profile)  # One frozen copy for the whole batch.
            correspondents = known_correspondents(people(store))
            register_profile(store, profile)
            run_id, failures, reused = identity("run_"), 0, 0
            store.append("run_start", dict(run_id=run_id, letter_ids=[l["letter_id"] for l in selected],
                                          fresh=args.fresh, settings=config.public()))
            try:
                for letter in selected:
                    print(f"Processing {letter['letter_id']}: {len(letter['image_ids'])} page(s); {config.model}")
                    try:
                        request = prepare_request(inventory, letter, config, profile, correspondents=correspondents)
                    except (ValueError, OSError) as exc:
                        failures += 1
                        print(f"BLOCKED {letter['letter_id']}: {exc}")
                        continue
                    result, cached = transcribe(store, letter, request, config,
                        lambda: Gemini(config, api_key(args.env_file)), fresh=args.fresh,
                        retry_interrupted=args.retry_interrupted, run_id=run_id)
                    reused += int(cached)
                    failures += int(result["execution"] != "complete")
                    print(f"{letter['letter_id']}: {result['execution']}" + (" (reused; zero new requests)" if cached else ""))
                    # Canonical results were already checkpointed; this may safely fail.
                    refresh_exports(store, inventory, args)
                    if result.get("stop_batch"):
                        break
                # Also refresh status reports when every selected letter was blocked/skipped.
                refresh_exports(store, inventory, args)
            finally:
                starts = {e["data"]["attempt_id"] for e in store.events()
                          if e["kind"] == "attempt_start" and e["data"]["run_id"] == run_id}
                calls = [e["data"] for e in store.events()
                         if e["kind"] == "attempt_end" and e["data"]["attempt_id"] in starts]
                summary = dict(run_id=run_id, new_attempts=len(starts), reused_results=reused,
                               known_outcomes=len(calls), usage=aggregate(
                                   calls + [{"usage": read_usage(None)}] * (len(starts) - len(calls))),
                               failures=failures, costs=[c["cost"] for c in calls])
                store.append("run_end", summary)
                print(json.dumps(summary))
            return int(bool(failures))
    return 0


def main(argv=None):
    try:
        return run(parser().parse_args(argv))
    except KeyboardInterrupt:
        print("Interrupted. Saved work is retained. Inspect show/export before retrying.", file=sys.stderr)
        return 130
    except (OSError, ValueError, RuntimeError, ImportError, TypeError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
