# -*- coding: utf-8 -*-
"""cli-help-spec: conventions for CLI help text + consistency checker.

Pure standard library. CLI via argparse.
Exit codes: 0 no errors (warnings allowed), 1 errors found (or --strict warnings),
2 usage error (argparse).
"""
import argparse
import json
import re
import sys

RULES_DOC = {
    "H01": "first non-empty line must be 'Usage: <prog> ...'",
    "H02": "usage line should contain a <placeholder> or '(no arguments)'",
    "H03": "must contain an 'Options:' section",
    "H04": "every option line must have a description (same line after 2+ spaces, "
           "or on the following deeper-indented line)",
    "H05": "must contain an 'Examples:' block with at least one indented example",
    "H06": "must document exit codes ('Exit status' or 'Exit codes')",
    "H07": "must document -h/--help inside the Options section",
    "H08": "no trailing whitespace on any line",
    "H09": "lines should not exceed 100 characters",
    "H10": "program name from the usage line should appear in the first example",
}

FLAG_RE = re.compile(r"^\s*(-{1,2}[^\s\[,=]+)", re.UNICODE)
USAGE_RE = re.compile(r"^Usage:\s+\S+", re.UNICODE)
PROG_RE = re.compile(r"^Usage:\s+([^\s<]+)", re.UNICODE)


def check(text):
    """Check help text against the spec. Returns list of findings
    {rule, severity, line, message}; severity in {error, warn, info}."""
    findings = []
    lines = text.splitlines()

    def add(rule, sev, line_no, msg):
        findings.append({"rule": rule, "severity": sev, "line": line_no, "message": msg})

    first = next((i for i, l in enumerate(lines) if l.strip()), None)
    if first is None:
        add("H01", "error", None, "help text is empty")
        return findings

    if not USAGE_RE.match(lines[first]):
        add("H01", "error", first + 1,
            "first non-empty line must start with 'Usage: <prog>'")
    usage_line = lines[first]
    if "<" not in usage_line and "(no arguments)" not in usage_line:
        add("H02", "warn", first + 1,
            "usage line has no <placeholder> and no '(no arguments)' note")
    mprog = PROG_RE.match(usage_line)
    prog = mprog.group(1) if mprog else None

    opt_i = next((i for i, l in enumerate(lines) if l.strip().lower() == "options:"), None)
    if opt_i is None:
        add("H03", "error", None, "missing 'Options:' section")
        has_help = False
    else:
        block = []  # (index, line) until blank or next section header
        i = opt_i + 1
        while i < len(lines) and lines[i].strip() and not lines[i].strip().endswith(":"):
            block.append((i, lines[i]))
            i += 1
        has_help = False
        for pos, (ln, l) in enumerate(block):
            if not FLAG_RE.match(l):
                continue
            pos_after = 0
            for m2 in re.finditer(r"\S+", l):
                tok = m2.group(0)
                if tok.startswith("-"):
                    pos_after = m2.end()
                    if tok.rstrip(",") in ("-h", "--help"):
                        has_help = True
                else:
                    break
            rest = l[pos_after:]
            same_line_desc = re.search(r"[ \t]{2,}\S", rest) is not None
            next_desc = False
            if not same_line_desc and pos + 1 < len(block):
                nl = block[pos + 1][1]
                if nl[:1] in (" ", "\t") and nl.strip() and not FLAG_RE.match(nl):
                    next_desc = True
            if not (same_line_desc or next_desc):
                add("H04", "error", ln + 1,
                    "option %s has no description" % l.strip().split()[0])
        if not has_help:
            add("H07", "error", None, "-h/--help not documented in Options section")

    ex_i = next((i for i, l in enumerate(lines) if l.strip() == "Examples:"), None)
    if ex_i is None:
        add("H05", "error", None, "missing 'Examples:' block")
    else:
        ex_lines = []
        j = ex_i + 1
        while j < len(lines) and (lines[j].startswith((" ", "\t")) or not lines[j].strip()):
            if lines[j].strip():
                ex_lines.append((j, lines[j]))
            j += 1
            if lines[j - 1].strip() and not lines[j - 1].startswith((" ", "\t")):
                break
        if not ex_lines:
            add("H05", "error", ex_i + 1, "'Examples:' block has no indented example")
        elif prog and prog not in ex_lines[0][1]:
            add("H10", "warn", ex_lines[0][0] + 1,
                "program name %r not present in first example" % prog)

    if not re.search(r"exit\s+(status|codes?)", text, re.IGNORECASE):
        add("H06", "error", None, "exit codes not documented ('Exit status'/'Exit codes')")

    tw = [i + 1 for i, l in enumerate(lines) if l != l.rstrip()]
    for ln in tw[:10]:
        add("H08", "warn", ln, "trailing whitespace")
    if len(tw) > 10:
        add("H08", "warn", None, "trailing whitespace on %d more lines" % (len(tw) - 10))

    long_lines = [i + 1 for i, l in enumerate(lines) if len(l) > 100]
    for ln in long_lines[:10]:
        add("H09", "warn", ln, "line is >100 chars")
    if len(long_lines) > 10:
        add("H09", "warn", None, "over-long lines on %d more lines" % (len(long_lines) - 10))

    return findings


def exit_code(findings, strict=False):
    has_err = any(f["severity"] == "error" for f in findings)
    has_warn = any(f["severity"] == "warn" for f in findings)
    if has_err or (strict and has_warn):
        return 1
    return 0


def cmd_check(args):
    try:
        with open(args.file, "r", encoding="utf-8", newline="") as f:
            text = f.read()
    except OSError as e:
        print("cannot read %s: %s" % (args.file, e), file=sys.stderr)
        return 1
    findings = check(text)
    if args.json:
        print(json.dumps({"findings": findings, "strict": args.strict},
                         ensure_ascii=False, indent=2))
    else:
        for f in findings:
            print("%s %s line=%s: %s" % (f["severity"], f["rule"], f["line"], f["message"]))
        n_err = sum(1 for f in findings if f["severity"] == "error")
        n_warn = sum(1 for f in findings if f["severity"] == "warn")
        print("%d error(s), %d warn(s)" % (n_err, n_warn))
    return exit_code(findings, strict=args.strict)


def _synthetic_help(prog, body_lines):
    return "\n".join([
        "Usage: %s <input> [options]" % prog,
        "",
        "Demo tool used for benchmarking the help-spec checker.",
        "",
        "Options:",
        "  -h, --help            show this help and exit",
        "  -v, --verbose         increase verbosity",
        "  -o, --output <path>   write result to path",
    ] + body_lines)


def cmd_bench(args):
    import time
    text = _synthetic_help("benchprog", [
        "",
        "Examples:",
        "  benchprog in.txt -o out.txt",
        "",
        "Exit status:",
        "  0 success, 1 failure",
    ])
    t0 = time.perf_counter()
    n = 0
    for _ in range(args.files):
        n += len(check(text))
    dt = time.perf_counter() - t0
    print("bench: %d help texts (%d chars each) checked in %.3fs "
          "(%.0f texts/s, %d findings)" % (args.files, len(text), dt,
                                           args.files / dt if dt > 0 else 0, n))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="cli-help-spec",
        description="CLI help-text conventions (usage/options/examples/exit codes) "
                    "plus a consistency checker.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="check a help-text file against the spec")
    c.add_argument("file")
    c.add_argument("--strict", action="store_true", help="warnings also fail")
    c.add_argument("--json", action="store_true")
    c.set_defaults(fn=cmd_check)
    b = sub.add_parser("bench", help="synthetic benchmark")
    b.add_argument("--files", type=int, default=500)
    b.set_defaults(fn=cmd_bench)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
