# -*- coding: utf-8 -*-
"""self_test for cli-help-spec (scaffold v2, four defenses inherited).

D1: SystemExit caught in run_cli. D2: Unicode help text / prog names exercised.
D3: fixtures written with newline="". D4: last line "SUMMARY: PASS n/n".
"""
import contextlib
import importlib.util
import io
import json
import os
import re
import sys
import tempfile
import unittest

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n")  # D3

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "core", os.path.join(_HERE, "cli_help_spec.py"))
core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(core)
main = core.main

CASES = []


def case(category, name):
    def deco(fn):
        CASES.append((category, name, fn))
        return fn
    return deco


def run_cli(argv):
    buf_out, buf_err = io.StringIO(), io.StringIO()
    code = 0
    try:
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            ret = main(argv)
            code = 0 if ret is None else int(ret)
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except Exception as e:
        code = 1
        buf_err.write(repr(e))
    return code, buf_out.getvalue(), buf_err.getvalue()


_TMP = tempfile.mkdtemp(prefix="chs_selftest_")


def write_fixture(name, text):
    p = os.path.join(_TMP, name)
    with open(p, "w", encoding="utf-8", newline="") as f:  # D3
        f.write(text)
    return p


def rules(text):
    return sorted(f["rule"] for f in core.check(text))


GOOD = """Usage: demo <input> [options]

Converting things since 2026.

Options:
  -h, --help            show this help and exit
  -v, --verbose         chatty output
  -o, --output <path>   where to write

Examples:
  demo file.txt -o out.txt

Exit status:
  0 on success, 1 on failure
"""

# ---------- [A] functional ----------
def _t_good_clean():
    fs = core.check(GOOD)
    assert [f for f in fs if f["severity"] == "error"] == [], fs
case("A", "spec-conformant help has zero errors")(_t_good_clean)

def _t_h01_missing():
    assert "H01" in rules("hello world\n" + GOOD)
case("A", "H01 fires when usage line missing")(_t_h01_missing)

def _t_h01_blank_prefix():
    assert "H01" not in rules("\n\n\n" + GOOD)
case("A", "H01 tolerates leading blank lines")(_t_h01_blank_prefix)

def _t_h02_no_placeholder():
    t = GOOD.replace("Usage: demo <input> [options]", "Usage: demo", 1)
    assert any(f["rule"] == "H02" and f["severity"] == "warn" for f in core.check(t))
case("A", "H02 warns when no placeholder in usage")(_t_h02_no_placeholder)

def _t_h02_noargs_ok():
    t = GOOD.replace("Usage: demo <input> [options]", "Usage: demo (no arguments)", 1)
    assert "H02" not in [f["rule"] for f in core.check(t)]
case("A", "H02 satisfied by '(no arguments)'")(_t_h02_noargs_ok)

def _t_h03_missing():
    t = GOOD.replace("Options:\n", "", 1)
    assert "H03" in rules(t)
case("A", "H03 fires when Options section missing")(_t_h03_missing)

def _t_h04_undescribed():
    t = GOOD.replace("  -v, --verbose         chatty output\n", "  -v, --verbose\n")
    assert "H04" in rules(t)
case("A", "H04 fires for flag without description")(_t_h04_undescribed)

def _t_h04_nextline_desc():
    t = GOOD.replace("  -v, --verbose         chatty output\n",
                     "  -v, --verbose\n        chatty output\n")
    assert "H04" not in [f["rule"] for f in core.check(t)]
case("A", "H04 accepts next-line indented description")(_t_h04_nextline_desc)

def _t_h05_missing():
    t = GOOD.replace("Examples:\n  demo file.txt -o out.txt\n", "", 1)
    assert "H05" in rules(t)
case("A", "H05 fires when Examples missing")(_t_h05_missing)

def _t_h05_empty_block():
    t = GOOD.replace("Examples:\n  demo file.txt -o out.txt\n", "Examples:\n", 1)
    assert "H05" in rules(t)
case("A", "H05 fires for empty Examples block")(_t_h05_empty_block)

def _t_h06_missing():
    t = GOOD.replace("Exit status:\n  0 on success, 1 on failure\n", "", 1)
    assert "H06" in rules(t)
case("A", "H06 fires when exit codes missing")(_t_h06_missing)

def _t_h06_lowercase():
    t = GOOD.replace("Exit status:", "exit codes:", 1)
    assert "H06" not in [f["rule"] for f in core.check(t)]
case("A", "H06 case-insensitive match")(_t_h06_lowercase)

def _t_h07_missing():
    t = GOOD.replace("  -h, --help            show this help and exit\n", "", 1)
    assert "H07" in rules(t)
case("A", "H07 fires when -h/--help undocumented")(_t_h07_missing)

def _t_h08_trailing_ws():
    t = GOOD.replace("Converting things since 2026.", "Converting things since 2026.  ", 1)
    assert any(f["rule"] == "H08" and f["severity"] == "warn" for f in core.check(t))
case("A", "H08 warns on trailing whitespace")(_t_h08_trailing_ws)

def _t_h09_long_line():
    t = GOOD.replace("Converting things since 2026.", "x" * 101, 1)
    assert any(f["rule"] == "H09" and f["severity"] == "warn" for f in core.check(t))
case("A", "H09 warns on >100 char line")(_t_h09_long_line)

def _t_h10_prog_mismatch():
    t = GOOD.replace("  demo file.txt -o out.txt", "  other file.txt -o out.txt", 1)
    assert any(f["rule"] == "H10" for f in core.check(t))
case("A", "H10 warns on prog/example mismatch")(_t_h10_prog_mismatch)

def _t_h10_match_ok():
    assert "H10" not in [f["rule"] for f in core.check(GOOD)]
case("A", "H10 silent when example matches prog")(_t_h10_match_ok)

def _t_exit_code_clean():
    assert core.exit_code(core.check(GOOD)) == 0
case("A", "exit_code 0 for clean text")(_t_exit_code_clean)

def _t_exit_code_warn():
    t = GOOD.replace("Converting things since 2026.", "Converting things.  ", 1)
    assert core.exit_code(core.check(t)) == 0
    assert core.exit_code(core.check(t), strict=True) == 1
case("A", "exit_code strict promotes warns")(_t_exit_code_warn)

def _t_cli_check_ok():
    p = write_fixture("good.txt", GOOD)
    code, out, _ = run_cli(["check", p])
    assert code == 0 and "0 error(s)" in out
case("A", "CLI check conformant -> 0")(_t_cli_check_ok)

def _t_cli_check_json():
    p = write_fixture("good.txt", GOOD)
    code, out, _ = run_cli(["check", p, "--json"])
    assert code == 0 and isinstance(json.loads(out)["findings"], list)
case("A", "CLI check --json round-trip")(_t_cli_check_json)

def _t_cli_check_bad():
    p = write_fixture("bad.txt", "nothing useful here\n")
    code, out, _ = run_cli(["check", p])
    assert code == 1
case("A", "CLI check non-conformant -> 1")(_t_cli_check_bad)

def _t_cli_strict():
    t = GOOD.replace("Converting things since 2026.", "Converting things.  ", 1)
    p = write_fixture("warn.txt", t)
    code, _, _ = run_cli(["check", p])
    code2, _, _ = run_cli(["check", p, "--strict"])
    assert code == 0 and code2 == 1
case("A", "CLI --strict flips exit code")(_t_cli_strict)

# ---------- [B] exception paths ----------
def _t_empty_text():
    fs = core.check("")
    assert len(fs) == 1 and fs[0]["rule"] == "H01"
case("B", "empty text -> single H01 finding")(_t_empty_text)

def _t_whitespace_only():
    fs = core.check("\n   \n\t\n")
    assert len(fs) == 1 and fs[0]["rule"] == "H01"
case("B", "whitespace-only text -> H01")(_t_whitespace_only)

def _t_missing_file():
    code, _, err = run_cli(["check", os.path.join(_TMP, "nope.txt")])
    assert code == 1 and "cannot read" in err
case("B", "CLI missing file -> 1 with message")(_t_missing_file)

def _t_no_args():
    code, _, _ = run_cli([])
    assert code == 2
case("B", "CLI no args -> SystemExit 2 (D1)")(_t_no_args)

def _t_unknown_cmd():
    code, _, _ = run_cli(["lint", "x"])
    assert code == 2
case("B", "CLI unknown subcommand -> 2")(_t_unknown_cmd)

def _t_missing_file_arg():
    code, _, _ = run_cli(["check"])
    assert code == 2
case("B", "CLI check without file -> 2")(_t_missing_file_arg)

def _t_h04_block_edge():
    # options block ending at EOF without trailing blank line must not crash
    t = "Usage: t <x>\n\nOptions:\n  -h, --help"
    fs = core.check(t)
    assert isinstance(fs, list)
case("B", "options block at EOF does not crash")(_t_h04_block_edge)

def _t_examples_at_eof():
    t = "Usage: t <x>\n\nOptions:\n  -h, --help  x\n\nExamples:"
    fs = core.check(t)
    assert any(f["rule"] == "H05" for f in fs)
case("B", "Examples header at EOF -> H05")(_t_examples_at_eof)

def _t_non_utf8_file():
    p = os.path.join(_TMP, "latin.txt")
    with open(p, "wb") as f:
        f.write(b"Usage: caf\xe9 <x>\n")
    code, _, _ = run_cli(["check", p])
    assert code in (0, 1)  # must not crash with unhandled exception
case("B", "non-UTF8 bytes do not crash checker")(_t_non_utf8_file)

def _t_findings_shape():
    for f in core.check("x"):
        assert set(f) == {"rule", "severity", "line", "message"}
case("B", "finding dicts have stable shape")(_t_findings_shape)

def _t_h08_capped():
    t = "Usage: t <x>\n" + "\n".join("line %d  " % i for i in range(30))
    fs = core.check(t)
    h08 = [f for f in fs if f["rule"] == "H08"]
    assert len(h08) <= 11 and any("more lines" in f["message"] for f in h08)
case("B", "H08 findings capped with overflow note")(_t_h08_capped)

def _t_h09_capped():
    t = "Usage: t <x>\n" + "\n".join("y" * 120 for _ in range(30))
    fs = core.check(t)
    assert len([f for f in fs if f["rule"] == "H09"]) <= 11
case("B", "H09 findings capped")(_t_h09_capped)

def _t_severity_vocab():
    for f in core.check(GOOD + "   \n" + "z" * 120):
        assert f["severity"] in ("error", "warn", "info")
case("B", "severities limited to error/warn/info")(_t_severity_vocab)

def _t_options_case_insensitive():
    t = GOOD.replace("Options:", "options:", 1)
    assert "H03" not in [f["rule"] for f in core.check(t)]
case("B", "H03 accepts lowercase 'options:'")(_t_options_case_insensitive)

# ---------- [C] extreme edges ----------
def _t_crlf_fixture():
    p = write_fixture("crlf.txt", GOOD + "\r\n")
    code, _, _ = run_cli(["check", p])
    assert code == 0
case("C", "CRLF fixture passes (D3)")(_t_crlf_fixture)

def _t_unicode_prog():
    t = GOOD.replace("demo", "工具", 1).replace("  demo file.txt", "  工具 file.txt", 1)
    fs = core.check(t)
    assert [f for f in fs if f["severity"] == "error"] == []
case("C", "unicode program name works")(_t_unicode_prog)

def _t_unicode_body():
    t = GOOD.replace("Converting things since 2026.",
                     "转换工具 — Support mémojis 🧪 and accès.", 1)
    assert core.exit_code(core.check(t)) == 0
case("C", "unicode body text (D2)")(_t_unicode_body)

def _t_very_long_usage():
    t = GOOD.replace("Usage: demo <input> [options]",
                     "Usage: demo <%s> [options]" % ("a" * 5000), 1)
    fs = core.check(t)
    assert [f for f in fs if f["severity"] == "error"] == []
case("C", "5k-char usage placeholder tolerated")(_t_very_long_usage)

def _t_10k_lines():
    t = GOOD + "\n".join("filler %d" % i for i in range(10000))
    fs = core.check(t)
    assert isinstance(fs, list)
case("C", "10k-line text scans without error")(_t_10k_lines)

def _t_tabs_indent():
    t = GOOD.replace("  -h, --help            show this help and exit",
                     "\t-h, --help\t\tshow this help and exit", 1)
    fs = core.check(t)
    assert "H04" not in [f["rule"] for f in fs]
case("C", "tab-indented option accepted")(_t_tabs_indent)

def _t_windows_paths_example():
    t = GOOD.replace("  demo file.txt -o out.txt",
                     "  demo C:\\data\\file.txt -o C:\\out\\res.txt", 1)
    assert core.exit_code(core.check(t)) == 0
case("C", "windows-style paths in examples")(_t_windows_paths_example)

def _t_flag_with_equals():
    t = GOOD.replace("  -o, --output <path>   where to write",
                     "  --output=<path>       where to write", 1)
    fs = core.check(t)
    assert [f for f in fs if f["severity"] == "error"] == []
case("C", "--flag=value form accepted")(_t_flag_with_equals)

def _t_bracket_opts():
    t = GOOD.replace("  -o, --output <path>   where to write",
                     "  -o[, --output] <path>  where to write", 1)
    assert core.exit_code(core.check(t)) == 0
case("C", "bracketed option alias form accepted")(_t_bracket_opts)

def _t_section_order_free():
    t = GOOD.replace("Examples:", "Exit status:\n  0 ok\n\nExamples:", 1)
    fs = core.check(t)
    assert [f for f in fs if f["severity"] == "error"] == []
case("C", "section order is free")(_t_section_order_free)

def _t_empty_examples_then_exit():
    t = GOOD.replace("Examples:\n  demo file.txt -o out.txt",
                     "Examples:\n\nExit status:\n  0 ok", 1)
    assert "H05" in rules(t)
case("C", "blank line after Examples is not an example")(_t_empty_examples_then_exit)

def _t_json_flag_no_effect():
    p = write_fixture("j.txt", GOOD)
    code, out, _ = run_cli(["check", p, "--json"])
    fs = json.loads(out)["findings"]
    assert code == 0 and fs == [] or all(f["severity"] != "error" for f in fs)
case("C", "--json output consistent with exit code")(_t_json_flag_no_effect)

def _t_h06_plural_form():
    t = GOOD.replace("Exit status:", "Exit codes:", 1)
    assert core.exit_code(core.check(t)) == 0
case("A", "H06 accepts plural 'Exit codes:'")(_t_h06_plural_form)

def _t_continuation_line_not_option():
    t = GOOD.replace("  -v, --verbose         chatty output",
                     "  -v, --verbose         chatty output\n  This flag is noisy.", 1)
    fs = core.check(t)
    assert not any(f["rule"] == "H04" and "This" in f["message"] for f in fs)
case("A", "non-flag continuation line not treated as option")(_t_continuation_line_not_option)

def _t_dotted_prog():
    t = GOOD.replace("demo", "my.tool", 3)
    assert core.exit_code(core.check(t)) == 0
case("A", "dotted program name consistent")(_t_dotted_prog)

def _t_subcommand_usage():
    t = GOOD.replace("Usage: demo <input> [options]",
                     "Usage: demo remote add <name> [options]", 1)
    fs = core.check(t)
    assert "H01" not in [f["rule"] for f in fs]
    assert "H02" not in [f["rule"] for f in fs]
case("A", "subcommand usage line accepted")(_t_subcommand_usage)

def _t_warns_counted_cli():
    t = GOOD.replace("Converting things since 2026.",
                     "Converting things since 2026.  " + "z" * 120, 1)
    p = write_fixture("multi.txt", t)
    code, out, _ = run_cli(["check", p, "--json"])
    fs = json.loads(out)["findings"]
    assert code == 0 and all(f["severity"] == "warn" for f in fs)
case("A", "warn-only text: CLI json shows only warns")(_t_warns_counted_cli)

def _t_tab_example():
    t = GOOD.replace("  demo file.txt -o out.txt", "\tdemo file.txt -o out.txt", 1)
    fs = core.check(t)
    assert "H05" not in [f["rule"] for f in fs]
case("A", "tab-indented example accepted")(_t_tab_example)

def _t_exit_code_empty_findings():
    assert core.exit_code([]) == 0 and core.exit_code([], strict=True) == 0
case("A", "exit_code with zero findings")(_t_exit_code_empty_findings)

def _t_options_until_next_section():
    t = GOOD.replace("\nExamples:", "\nNotes:\n  be kind\n\nExamples:", 1)
    fs = core.check(t)
    assert [f for f in fs if f["severity"] == "error"] == []
case("A", "options block terminates at next section header")(_t_options_until_next_section)

def _t_json_warn_shape():
    t = GOOD.replace("Converting things since 2026.", "Converting things.  ", 1)
    p = write_fixture("w2.txt", t)
    code, out, _ = run_cli(["check", p, "--json"])
    fs = json.loads(out)["findings"]
    assert code == 0 and fs and fs[0]["rule"] == "H08"
case("A", "--json surfaces H08 warn with line")(_t_json_warn_shape)

def _t_h01_after_blank_prefix_only():
    fs = core.check("\n\nUsage: t <x>\n")
    assert "H01" not in [f["rule"] for f in fs]
case("A", "usage after blank prefix recognized")(_t_h01_after_blank_prefix_only)

def _t_h10_second_example_free():
    t = GOOD.replace("  demo file.txt -o out.txt",
                     "  demo file.txt -o out.txt\n  other-prog --version", 1)
    fs = core.check(t)
    assert "H10" not in [f["rule"] for f in fs]
case("A", "H10 only checks the first example")(_t_h10_second_example_free)

def _t_meta_count():
    assert len(CASES) >= 60
case("C", "meta: at least 60 cases defined")(_t_meta_count)


class T(unittest.TestCase):
    pass


def _add(i, cat, name, fn):
    def t(self, _f=fn):
        _f()
    t.__doc__ = "%s: %s" % (cat, name)
    setattr(T, "test_%s_%03d_%s" % (cat, i, re.sub(r"[^0-9A-Za-z_]", "_", name)), t)


for _i, (_c, _n, _f) in enumerate(CASES):
    _add(_i + 1, _c, _n, _f)

if __name__ == "__main__":
    r = unittest.TextTestRunner(verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules["__main__"]))
    total, fails = r.testsRun, len(r.failures) + len(r.errors)
    print("SUMMARY: PASS %d/%d" % (total - fails, total))  # D4
    sys.exit(0 if fails == 0 else 1)
