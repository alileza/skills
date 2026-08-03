#!/usr/bin/env python3
"""Prune bloat out of a Claude Code session transcript to cut future token spend.

Claude Code stores each session as a JSONL file under
~/.claude/projects/<project>/<session-id>.jsonl and replays it as context when you
resume the session (--continue / --resume). Anything fat in that file — pasted
screenshots, giant tool results — is re-sent on every turn after it appears. This
tool finds that bloat and, on --apply, writes a pruned copy so a *resumed* session
sends far less.

Mechanics this respects:
  * Images live in a `user` message content array -> the image block is replaced
    with a small "[image pruned]" text stub. No pairing constraints.
  * A tool_result must keep its matching tool_use (the API rejects an orphan), so
    its *content* is shrunk to a stub; the line is never deleted.
  * It only helps on RESUME. It does not refund tokens already billed.

Safety:
  * Dry-run by default — prints what it would strip and the estimated savings.
  * --apply writes to <name>.pruned.jsonl and leaves the original untouched unless
    you also pass --in-place (which keeps a .bak).
  * Refuses to touch a file modified in the last 120s (likely an open session)
    unless --force. Never edit a session that is currently open in Claude Code.

Usage:
  prune-session.py SESSION.jsonl                 # dry-run report
  prune-session.py SESSION.jsonl --apply         # write SESSION.pruned.jsonl
  prune-session.py SESSION.jsonl --apply --in-place   # replace, keep .bak
  prune-session.py ~/.claude/projects/<proj>/    # scan every session in a project
  prune-session.py <dir> --tool-results 20000    # also stub tool_results > 20 KB
"""
import argparse
import json
import os
import struct
import sys
import time
from base64 import b64decode
from glob import glob

IMG_STUB = "[image pruned to save context]"
TR_STUB = "[tool result pruned to save context]"


def img_dims(media_type, data_b64):
    """Best-effort (width, height) from a base64 image, or None."""
    try:
        raw = b64decode(data_b64[:4096] + "==")  # header is enough
    except Exception:
        return None
    try:
        if "png" in media_type and raw[:8] == b"\x89PNG\r\n\x1a\n":
            w, h = struct.unpack(">II", raw[16:24])
            return w, h
        if "jpeg" in media_type or "jpg" in media_type:
            i = 2
            while i < len(raw) - 9:
                if raw[i] != 0xFF:
                    i += 1
                    continue
                m = raw[i + 1]
                if m in (0xC0, 0xC1, 0xC2, 0xC3):
                    h, w = struct.unpack(">HH", raw[i + 5:i + 9])
                    return w, h
                seg = struct.unpack(">H", raw[i + 2:i + 4])[0]
                i += 2 + seg
    except Exception:
        return None
    return None


def img_tokens(media_type, data_b64):
    """Approximate Anthropic image token cost: ~(w*h)/750, capped like the API."""
    dims = img_dims(media_type, data_b64)
    if not dims:
        return 1400  # typical screenshot fallback
    w, h = dims
    long_edge = max(w, h)
    if long_edge > 1568:  # API downscales the long edge to 1568
        scale = 1568 / long_edge
        w, h = w * scale, h * scale
    return int((w * h) / 750)


def blocks(obj):
    c = obj.get("message", {}).get("content")
    return c if isinstance(c, list) else []


def prune_line(obj, tr_threshold):
    """Return (changed, image_hits, tr_hits) after stubbing in place."""
    changed = False
    img_hits = []
    tr_hits = 0
    for b in blocks(obj):
        if not isinstance(b, dict):
            continue
        if b.get("type") == "image":
            src = b.get("source", {})
            data = src.get("data", "")
            if data:
                img_hits.append(img_tokens(src.get("media_type", ""), data))
                b.clear()
                b["type"] = "text"
                b["text"] = IMG_STUB
                changed = True
        elif b.get("type") == "tool_result" and tr_threshold:
            content = b.get("content")
            size = len(json.dumps(content)) if content is not None else 0
            if size > tr_threshold:
                b["content"] = TR_STUB
                tr_hits += 1
                changed = True
    return changed, img_hits, tr_hits


def turn_count_after(lines, idx):
    """How many message turns follow this line = how many times it was re-sent."""
    n = 0
    for line in lines[idx + 1:]:
        if '"role"' in line:
            n += 1
    return n


def process(path, args):
    with open(path) as fh:
        lines = fh.read().splitlines()

    total_img = 0
    total_tr = 0
    token_turns = 0
    out = []
    for idx, line in enumerate(lines):
        try:
            obj = json.loads(line)
        except Exception:
            out.append(line)
            continue
        changed, img_hits, tr_hits = prune_line(obj, args.tool_results)
        if changed and img_hits:
            reps = turn_count_after(lines, idx)
            token_turns += sum(t * max(reps, 1) for t in img_hits)
        total_img += len(img_hits)
        total_tr += tr_hits
        out.append(json.dumps(obj) if changed else line)

    before = os.path.getsize(path)
    new_text = "\n".join(out) + ("\n" if lines else "")
    after = len(new_text.encode())

    name = os.path.basename(path)
    if total_img == 0 and total_tr == 0:
        print(f"  {name}: nothing to prune")
        return
    print(f"  {name}")
    print(f"    images stubbed:       {total_img}")
    if args.tool_results:
        print(f"    tool_results stubbed: {total_tr} (> {args.tool_results} B)")
    print(f"    file size:            {before/1e6:.2f} MB -> {after/1e6:.2f} MB")
    print(f"    est. tokens saved per resume, summed over turns re-sent: "
          f"~{token_turns/1000:.0f}k token-reads")

    if not args.apply:
        return

    if not args.force and (time.time() - os.path.getmtime(path)) < 120:
        print("    SKIPPED --apply: modified < 120s ago (session may be open). "
              "Use --force to override.")
        return

    if args.in_place:
        bak = path + ".bak"
        if not os.path.exists(bak):
            os.rename(path, bak)
        else:
            os.replace(path, bak)
        with open(path, "w") as fh:
            fh.write(new_text)
        print(f"    WROTE pruned transcript in place; original saved to {os.path.basename(bak)}")
    else:
        dest = path.rsplit(".jsonl", 1)[0] + ".pruned.jsonl"
        with open(dest, "w") as fh:
            fh.write(new_text)
        print(f"    WROTE {os.path.basename(dest)} (original untouched)")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="a .jsonl session file or a project directory")
    ap.add_argument("--apply", action="store_true",
                    help="write the pruned transcript (default: dry-run report only)")
    ap.add_argument("--in-place", action="store_true",
                    help="with --apply, replace the original and keep a .bak")
    ap.add_argument("--tool-results", type=int, default=0, metavar="BYTES",
                    help="also stub tool_result content larger than BYTES (default: off)")
    ap.add_argument("--force", action="store_true",
                    help="apply even to a recently-modified (possibly open) session")
    args = ap.parse_args()

    if os.path.isdir(args.target):
        files = sorted(glob(os.path.join(args.target, "*.jsonl")))
        if not files:
            sys.exit(f"no .jsonl sessions in {args.target}")
    elif os.path.isfile(args.target):
        files = [args.target]
    else:
        sys.exit(f"not found: {args.target}")

    print(f"{'DRY-RUN — no files changed' if not args.apply else 'APPLYING'}\n")
    for f in files:
        process(f, args)
    if not args.apply:
        print("\nRe-run with --apply to write pruned copies. "
              "Never prune a session that is currently open in Claude Code.")


if __name__ == "__main__":
    main()
