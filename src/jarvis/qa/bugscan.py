"""Antibug: deterministic bug detection for this codebase.

Every rule here exists because it caught a real, shipped bug - not because it
sounds like good practice. The classes came out of actually hunting:

  1. UNDEFINED_NAME   - a bare name with no binding. Caught `model_name` in the
     final-synthesis call, `np` in the audio RMS path, and `Any` in registry
     annotations. The first was masked by a bare `except Exception`, so it
     silently produced a fabricated "success" string on every run.
  2. IMPORT_ERROR     - a module imported at runtime but never declared as a
     dependency. Caught the AI subsystem: `openai` and `groq` are imported in
     `jarvis_voice._resolve` and declared in neither pyproject nor the lockfile,
     so every provider branch raised ModuleNotFoundError into a bare `except:
     pass` and the engine silently degraded to "offline".
  3. SWALLOWED_ERROR  - an `except` that discards the exception with no logging
     and no re-raise, on a path where the caller would otherwise think the work
     succeeded.
  4. FALSE_CLAIM      - a string asserting a security property ("pinned
     sha256", "strict path jailing") that no code enforces. Caught the
     write-only content pin: `jarvis skill admit` printed "pinned sha256" and
     nothing ever read it.
  5. COMPILE_ERROR    - a file that does not parse. Caught a line truncated
     mid-token by a concurrent writer.
  6. DEAD_RESULT      - a value recorded for a caller that no code reads. Caught
     `SkillExecutionResult.audit_errors`, which was the only trace of a failed
     audit write.

The design constraint that matters: these are all *deterministic*. The AI triage
layer in `triage.py` can explain and propose, but it never gates what is
detected - an LLM that is silently broken (as it was here) must not be able to
silently disable bug detection.

Deliberately NOT included: enforcing "no unused imports" or "no docstring on
every module". Both produce hundreds of hits on pre-existing code and would
bury the five rules that actually catch defects. Precision over recall.
"""

from __future__ import annotations

import ast
import builtins
import json
import re
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator, Sequence

BUILTIN_NAMES = frozenset(dir(builtins)) | {
    "__file__",
    "__name__",
    "__doc__",
    "__package__",
    "__spec__",
    "__loader__",
    "__builtins__",
    "__debug__",
    "WindowsError",
    "__class__",
}


@dataclass(frozen=True)
class Finding:
    """One defect, with enough context to fix it without rerunning the scan."""

    rule: str
    severity: str  # "critical" | "high" | "medium" | "low"
    file: str
    line: int
    message: str
    snippet: str = ""
    #: Short, stable key used to reference this finding in `jarvis bugfix`.
    finding_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "rule": self.rule,
            "severity": self.severity,
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "snippet": self.snippet,
        }


SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _finding_id(file: str, line: int, rule: str, extra: str = "") -> str:
    """Deterministic short id so a finding can be referenced from the CLI.

    `extra` disambiguates findings that share a file and line. `import a, b`
    yields one node with two module names, so line alone produced colliding ids
    and made two distinct findings share one CLI handle.
    """
    import hashlib

    digest = hashlib.sha256(f"{file}:{line}:{rule}:{extra}".encode("utf-8")).hexdigest()
    return f"{rule.lower()}-{digest[:10]}"


# ---------------------------------------------------------------------------
# rule 1: undefined names
# ---------------------------------------------------------------------------


def _declared_names(tree: ast.AST) -> set[str]:
    """Names bound anywhere in the module: imports, defs, classes, assignments."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
            names.update(_arg_names(node.args))
        elif isinstance(node, ast.ClassDef):
            # ClassDef has no `args`; only the name is bound here.
            names.add(node.name)
        elif isinstance(node, ast.Lambda):
            # Lambda parameters are the single largest source of false
            # positives in this rule; `key=lambda x: x.id` is extremely common.
            names.update(_arg_names(node.args))
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            names.add(node.id)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            names.update(node.names)
    return names


def _arg_names(args: ast.arguments) -> set[str]:
    out: set[str] = set()
    for a in (
        list(getattr(args, "posonlyargs", []))
        + list(args.args)
        + list(args.kwonlyargs)
        + [args.vararg, args.kwarg]
    ):
        if a is not None:
            out.add(a.arg)
    return out


def _loads_not_bound(tree: ast.AST) -> Iterator[tuple[int, str]]:
    """Yield (lineno, name) for loads that resolve to nothing in the module.

    This is a deliberately conservative approximation of pyflakes' F821: it
    unions every binding in the file, so it cannot prove a name is truly
    unbound in all cases (a name bound in one function and loaded in another is
    not reported, which is the safe direction). It needs no third-party
    dependency, which matters because the whole point is to work when the
    environment is broken.
    """
    declared = _declared_names(tree)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Name):
            continue
        if not isinstance(node.ctx, ast.Load):
            continue
        name = node.id
        if name in declared or name in BUILTIN_NAMES:
            continue
        # A comprehension/lambda target is bound inside its own scope.
        yield node.lineno, name


def rule_undefined_name(
    path: Path, tree: ast.AST, source: str, rel: str
) -> list[Finding]:
    out: list[Finding] = []
    lines = source.splitlines()
    for lineno, name in _loads_not_bound(tree):
        snippet = lines[lineno - 1].strip() if 0 < lineno <= len(lines) else ""
        out.append(
            Finding(
                rule="UNDEFINED_NAME",
                severity="critical",
                file=rel,
                line=lineno,
                message=(
                    f"name '{name}' is used but never bound or imported. "
                    f"This raises NameError at runtime."
                ),
                snippet=snippet[:200],
                finding_id=_finding_id(rel, lineno, "UNDEFINED_NAME"),
            )
        )
    return out


# ---------------------------------------------------------------------------
# rule 2: undeclared third-party imports
# ---------------------------------------------------------------------------

#: Modules the project is allowed to import that are NOT in pyproject: the
#: stdlib, and JARVIS itself.
#:
#: Sourced from `sys.stdlib_module_names` (authoritative, Python 3.10+) unioned
#: with the hand-written list below. A hand-written list alone was already wrong
#: within a day of being written: it omitted `ctypes`, so a legitimate
#: `import ctypes, ctypes.wintypes` was reported as a missing dependency.
_STDLIB = frozenset(
    set(getattr(sys, "stdlib_module_names", ()))
    | set(
        """abc argparse ast asyncio base64 binascii bisect calendar cmath collections
    concurrent configparser contextlib copy csv ctypes dataclasses datetime decimal
    difflib enum errno fnmatch fractions ftplib functools gc getpass gettext glob
    gzip hashlib heapq hmac html http imaplib importlib inspect io ipaddress
    itertools json keyword linecache locale logging lzma mailbox math mimetypes
    multiprocessing netrc numbers operator os pathlib pickle platform pkgutil
    posixpath pprint queue quopri random re reprlib resource secrets select
    selectors shelve shlex shutil signal site smtplib socket socketserver
    sqlite3 ssl stat statistics string stringprep struct subprocess sys tarfile
    tempfile textwrap threading time timeit token tokenize tomllib traceback
    types typing unicodedata unittest urllib uuid venv wave weakref webbrowser
    xml xmlrpc zipfile zipimport zlib zoneinfo""".split()
    )
    | {
        # Windows / platform-provided, which are not in stdlib_module_names.
        "winsound", "msvcrt", "winreg", "msilib", "nt",
    }
)


def _find_pyproject(start: Path) -> Path | None:
    """Locate the governing pyproject.toml by walking up from a source file.

    Looking only at `path.parent` is wrong for a `src/` layout: for
    `src/jarvis/skills/admission.py` that is `src/jarvis/skills`, which has no
    pyproject. The rule then saw an empty declared set and returned early, so
    IMPORT_ERROR never actually evaluated anything.
    """
    for candidate in (start, *start.parents):
        pyproject = candidate / "pyproject.toml"
        if pyproject.is_file():
            return pyproject
    return None


@lru_cache(maxsize=1)
def _declared_dependencies(pyproject: Path | None) -> set[str]:
    """Distribution names that look declared in pyproject, best effort.

    Parsed with a regex rather than a TOML library so the scanner has no
    dependency of its own.

    Two earlier attempts were wrong in instructive ways:
      * `^\\s*(\\w+)\\s*[><=~!]` captured the *key* (`dependencies=`) rather
        than the package names, so the declared set was meaningless.
      * requiring the quoted name to be the whole line worked for this repo's
        multi-line arrays but silently missed single-line ones.

    This matches any bare quoted token (`"pydantic>=2.5,<3"`, `"pytest"`), which
    handles both layouts. A structural key such as `name = "jarvis2.0"` can be
    picked up as a false entry; that only risks whitelisting a package whose
    name collides with a project field, which is preferable to whitelisting
    nothing.
    """
    if pyproject is None or not pyproject.is_file():
        return set()
    text = pyproject.read_text(encoding="utf-8", errors="replace")
    names: set[str] = set()
    for match in re.finditer(
        r"""["']([A-Za-z0-9][A-Za-z0-9._-]*)      # bare distribution name
            (?:\s*[><=~!][^"']*)?                # optional version specifier
            ["']""",
        text,
        re.VERBOSE,
    ):
        names.add(match.group(1).lower().replace("_", "-"))
    names -= _PYPROJECT_NON_DEPS
    return names


#: Quoted keys that appear in a pyproject but never denote a distribution.
_PYPROJECT_NON_DEPS = frozenset(
    {"dependencies", "dependency-groups", "dev", "true", "false", "utf-8"}
)


def _parent_map(tree: ast.AST) -> dict[int, ast.AST]:
    """Map each node's id() to its parent, so we can inspect guard context."""
    parents: dict[int, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[id(child)] = node
    return parents


def _import_guard(
    node: ast.AST, parents: dict[int, ast.AST]
) -> tuple[str, str]:
    """Classify how an import's failure would surface.

    Returns (severity, why). The distinction matters a lot for honesty: a
    properly guarded optional import is a packaging gap, whereas the same
    import swallowed by a bare `except: pass` is the silent-death pattern that
    disabled the AI subsystem without any diagnostic.
    """
    child: ast.AST | None = node
    while child is not None:
        parent = parents.get(id(child))
        if parent is None:
            break
        if isinstance(parent, ast.Try):
            caught: set[str] = set()
            silent = False
            for handler in parent.handlers:
                exc = handler.type
                if exc is None:
                    caught.add("BaseException")
                    silent = silent or _is_silent_handler(handler)
                elif isinstance(exc, ast.Name):
                    caught.add(exc.id)
                    silent = silent or _is_silent_handler(handler)
                elif isinstance(exc, ast.Tuple):
                    for elt in exc.elts:
                        if isinstance(elt, ast.Name):
                            caught.add(elt.id)
                    silent = silent or _is_silent_handler(handler)
            narrow = bool(caught) and caught <= {
                "ImportError",
                "ModuleNotFoundError",
                "OSError",
            }
            if narrow and not silent:
                return (
                    "low",
                    "optional import guarded by a narrow handler; failure is "
                    "reported, so this is a packaging gap rather than a defect",
                )
            if silent:
                return (
                    "critical",
                    "failure swallowed by a handler that does nothing, so the "
                    "feature disappears with no diagnostic",
                )
            return (
                "critical",
                f"failure caught by broad handler ({sorted(caught)}) and not "
                "re-raised; the caller cannot tell the import failed",
            )
        child = parent
    return (
        "critical",
        "unguarded import: raises ModuleNotFoundError wherever the path executes",
    )


def _is_silent_handler(handler: ast.ExceptHandler) -> bool:
    """True when a handler discards the error without reporting or re-raising."""
    if not handler.body:
        return True
    if len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass):
        return True
    for stmt in handler.body:
        if isinstance(stmt, ast.Raise):
            return False
    return False


def _is_declared_root(top: str, declared: set[str]) -> bool:
    """True when `top` is a declared distribution or a namespace of one.

    `from opentelemetry.sdk.trace import Span` is covered by declaring
    `opentelemetry-sdk`. The import's root is `opentelemetry`, which is a
    namespace shared by that distribution rather than a distribution name
    itself, so an exact match is not enough.
    """
    normalized = top.replace("_", "-")
    if normalized in declared or top in declared:
        return True
    for name in declared:
        flat = name.replace("-", "_")
        if flat == normalized:
            return True
        if name.replace("-", ".") == normalized:
            return True
        # Namespace contribution: opentelemetry-sdk -> opentelemetry
        for sep in ("-", "."):
            head = name.split(sep)[0]
            if head == normalized or head == top:
                return True
    return False


def _is_local_module(top: str, path: Path) -> bool:
    """True when `top` is a project file rather than a PyPI distribution.

    Covers two layouts seen here:
      * a sibling of the importing module, and
      * a module made importable by a runtime `sys.path.insert`, as
        `cli.py` does for `scripts/install_startup.py`.
    """
    for parent in path.parents:
        if (parent / f"{top}.py").is_file():
            return True
        if (parent / top / "__init__.py").is_file():
            return True
    # Runtime sys.path additions: look for the module anywhere in the repo.
    # Cached because this runs once per undeclared-import candidate and an
    # uncached rglob over the tree dominated total scan time.
    if top in _repo_module_names():
        return True
    return False


@lru_cache(maxsize=1)
def _repo_module_names() -> frozenset[str]:
    """Stems of every .py file in the repo, for local-module resolution."""
    names: set[str] = set()
    for candidate in _repo_root().rglob("*.py"):
        parts = candidate.parts
        if any(p in {"site-packages", ".venv", "venv", "__pycache__"} for p in parts):
            continue
        names.add(candidate.stem)
    return frozenset(names)


#: Modules that ship with Windows/CPython rather than needing a declaration.
_PLATFORM_STDLIB = frozenset(
    """winsound msvcrt winreg win32api win32con win32process pywintypes
    java javax""".split()
)


def rule_undeclared_import(
    path: Path, tree: ast.AST, source: str, rel: str
) -> list[Finding]:
    """Flag a runtime `import X` / `from X import` where X is neither stdlib
    nor a declared dependency, when the import is inside a function or method.

    A missing dependency is invisible until the code path runs. In this project
    it silently killed the entire AI subsystem: `from openai import OpenAI`
    inside `_resolve`, swallowed by a bare `except: pass`, so the engine
    degraded to "offline" and every caller fell back to rule-based guessing
    without a word of diagnostics.
    """
    declared = _declared_dependencies(_find_pyproject(path))
    if not declared:
        return []
    installed = _installed_distributions()
    if not installed:
        return []

    out: list[Finding] = []
    lines = source.splitlines()
    parents = _parent_map(tree)

    # Only consider imports nested inside a def/class body: top-level imports
    # fail loudly at import time, so they cannot be a silent runtime trap.
    #
    # These must be the import statements that are *directly* in the module
    # body. Walking each top-level node instead (ast.walk on a FunctionDef)
    # descends into the function and records its nested imports as top-level,
    # which silently excluded the exact lazy-import pattern this rule exists to
    # catch, making it dead code.
    top_level_lines: set[int] = set()
    for node in tree.body:  # type: ignore[attr-defined]
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            top_level_lines.add(node.lineno)

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if node.lineno in top_level_lines:
            continue
        if isinstance(node, ast.Import):
            roots = [a.name for a in node.names]
        else:
            if node.level:  # relative import within the package
                continue
            roots = [node.module or ""]
        for root in roots:
            top = root.split(".")[0].lower()
            if not top or top in _STDLIB or top == "jarvis":
                continue
            if top in _PLATFORM_STDLIB:
                continue
            if _is_declared_root(top, declared):
                continue
            if _is_local_module(top, path):
                continue
            snippet = (
                lines[node.lineno - 1].strip() if 0 < node.lineno <= len(lines) else ""
            )
            if top in installed:
                # Present here but undeclared. Still a defect: it works on this
                # machine only because something installed it out of band, and
                # breaks for everyone on a clean environment. Skipping these
                # outright would hide exactly the class of bug that left this
                # project claiming AI support with no declared provider SDK.
                out.append(
                    Finding(
                        rule="IMPORT_ERROR",
                        severity="low",
                        file=rel,
                        line=node.lineno,
                        message=(
                            f"imports '{root}' at runtime, but '{top}' is not a declared "
                            f"dependency in pyproject.toml. It happens to be installed in "
                            f"this environment, so the failure will not show up locally "
                            f"but will occur on a clean install."
                        ),
                        snippet=snippet[:200],
                        finding_id=_finding_id(rel, node.lineno, "IMPORT_ERROR", top),
                    )
                )
                continue
            severity, why = _import_guard(node, parents)
            out.append(
                Finding(
                    rule="IMPORT_ERROR",
                    severity=severity,
                    file=rel,
                    line=node.lineno,
                    message=(
                        f"imports '{root}' at runtime, but '{top}' is not a declared "
                        f"dependency in pyproject.toml and is not installed. {why}."
                    ),
                    snippet=snippet[:200],
                    finding_id=_finding_id(rel, node.lineno, "IMPORT_ERROR", top),
                )
            )
    return out


@lru_cache(maxsize=1)
def _installed_distributions() -> set[str]:
    """Top-level importable module names currently available in this env."""
    mods: set[str] = set()
    for entry in sys.path:
        p = Path(entry)
        if not p.is_dir():
            continue
        try:
            for child in p.iterdir():
                if child.suffix == ".py" and child.stem != "__init__":
                    mods.add(child.stem.lower())
                elif child.is_dir() and (child / "__init__.py").is_file():
                    mods.add(child.name.lower())
        except OSError:
            continue
    return mods


# ---------------------------------------------------------------------------
# rule 3: swallowed exceptions
# ---------------------------------------------------------------------------


def _handler_discards(only: ast.stmt) -> bool:
    """True if this single statement throws the exception away."""
    if isinstance(only, ast.Pass):
        return True
    if isinstance(only, ast.Continue):
        return True
    if isinstance(only, ast.Expr) and isinstance(only.value, ast.Constant):
        return True
    if isinstance(only, ast.Expr) and isinstance(only.value, ast.Call):
        func = only.value.func
        if isinstance(func, ast.Attribute) and func.attr in {
            "warning", "error", "exception", "info", "debug", "critical",
        }:
            return False
    return False


def rule_swallowed_error(
    path: Path, tree: ast.AST, source: str, rel: str
) -> list[Finding]:
    """Handlers that discard an exception, graded by how deliberate it looks.

    Two real bugs motivated this:

    - The final LLM synthesis referenced an undefined `model_name`; the
      `NameError` landed in a broad handler and the handler returned a
      hardcoded "Executed N system actions successfully" string. The agent
      reported success forever while doing nothing.
    - `_resolve()` caught every provider branch with `except: pass`, so a
      missing `openai` dependency produced a silent "offline" engine.

    Grading, because most `except OSError: pass` in this tree is legitimate
    best-effort cleanup and flagging all of it would be noise:

      * bare `except:`                    -> high   (almost always a bug)
      * `except T as name:` then discard  -> high   (the name proves intent)
      * `except T:` then discard          -> low    (often deliberate)
    """
    out: list[Finding] = []
    lines = source.splitlines()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if len(node.body) != 1 or not _handler_discards(node.body[0]):
            continue
        snippet = lines[node.lineno - 1].strip() if 0 < node.lineno <= len(lines) else ""
        if node.type is None:
            severity, why = "high", "bare `except:` swallows every error, including KeyboardInterrupt and SystemExit"
        elif node.name:
            severity, why = "high", f"binds '{node.name}' and then discards it without logging or re-raising"
        else:
            severity, why = "low", "typed handler discards the exception (often deliberate best-effort, but confirm the caller does not assume success)"
        out.append(
            Finding(
                rule="SWALLOWED_ERROR",
                severity=severity,
                file=rel,
                line=node.lineno,
                message=f"exception discarded: {why}.",
                snippet=snippet[:200],
                finding_id=_finding_id(rel, node.lineno, "SWALLOWED_ERROR"),
            )
        )
    return out


# ---------------------------------------------------------------------------
# rule 6: fabricated success
# ---------------------------------------------------------------------------

#: A handler that assigns a hardcoded success string is asserting an outcome it
#: never observed. This is the exact shape of the `model_name` bug.
_SUCCESS_WORDS = re.compile(
    r"\b(success(fully)?|succeeded|completed|done|ok|works? (fine|now))\b", re.I
)


def _static_string(node: ast.AST | None) -> str | None:
    """Best-effort literal text of a Constant or an f-string.

    The real `model_name` bug used an f-string
    (`f"Executed {n} system actions successfully, sir."`), which parses as
    `JoinedStr` and NOT `Constant`. Matching only `Constant` therefore missed
    the exact case this rule was written for.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            else:
                parts.append("{…}")
        return "".join(parts)
    return None


def rule_fabricated_success(
    path: Path, tree: ast.AST, source: str, rel: str
) -> list[Finding]:
    """An `except` handler whose only action is to assign a hardcoded string
    claiming the work succeeded.

    Found in the wild: `except Exception: final_text = "Executed N system
    actions successfully, sir."` - a response string asserting success while
    the underlying call had in fact raised NameError every single time.
    """
    out: list[Finding] = []
    lines = source.splitlines()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler) or len(node.body) != 1:
            continue
        stmt = node.body[0]
        if not isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            continue
        text = _static_string(stmt.value)
        if text is None:
            continue
        if not _SUCCESS_WORDS.search(text):
            continue
        lineno = stmt.lineno
        snippet = lines[lineno - 1].strip() if 0 < lineno <= len(lines) else ""
        out.append(
            Finding(
                rule="FABRICATED_SUCCESS",
                severity="high",
                file=rel,
                line=lineno,
                message=(
                    "exception handler assigns a hardcoded string claiming success "
                    f"({text[:60]!r}) without reporting the failure. If this branch is "
                    "taken, the caller believes the work succeeded."
                ),
                snippet=snippet[:200],
                finding_id=_finding_id(rel, lineno, "FABRICATED_SUCCESS"),
            )
        )
    return out


# ---------------------------------------------------------------------------
# rule 4: security claims that nothing enforces
# ---------------------------------------------------------------------------

#: Phrases that assert a *specific verifiable* property. Generic words like
#: "guarantee" or "fail-closed" are deliberately excluded: they appear ~60
#: times across this tree in prose and comments, which buries the one real
#: instance (`pinned sha256` printed by a command that enforced nothing).
#:
#: Each rule reports the CLAIM and asks for confirmation. It cannot see whether
#: the claim is honoured - `pinned sha256` is now genuinely enforced by
#: `SkillAdmissionPolicy.check_content`, and the rule still fires, because a
#: regex cannot read the call graph. Acknowledge reviewed claims in
#: `.qa_acknowledged.json` to stop the nagging.
CLAIM_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (r"pinned\s+sha256", "UNENFORCED_CLAIM",
     "asserts a content pin. Verify the stored digest is actually compared at "
     "execution time; `SkillAdmissionPolicy.check_content` is what does it."),
    (r"strict\s+path\s+jail", "UNENFORCED_CLAIM",
     "asserts path jailing. There is no filesystem sandbox in this codebase; "
     "confirm the surrounding text says so."),
    (r"\bexactly\s+once\b", "UNENFORCED_CLAIM",
     "asserts exactly-once semantics; confirm there is no replay path."),
    (r"\bnever\s+aborts?\b", "UNENFORCED_CLAIM",
     "asserts an operation cannot abort; confirm no path can raise."),
)


def rule_unenforced_claim(
    path: Path, tree: ast.AST, source: str, rel: str
) -> list[Finding]:
    """Flag security-sounding claims that no code backs.

    Reports the *claim*, not a proven lie, so severity is `low`. Exists to
    force a human to confirm rather than to be a gate.
    """
    out: list[Finding] = []
    lines = source.splitlines()
    # Docstrings are prose and may legitimately use these words; the real bug
    # was in a printed string. Collect docstring line spans to exclude.
    doc_lines: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", [])
        if not body:
            continue
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
            end = getattr(first, "end_lineno", first.lineno) or first.lineno
            doc_lines.update(range(first.lineno, end + 1))

    for idx, line in enumerate(lines, start=1):
        lowered = line.lower()
        stripped = line.strip()
        is_comment = stripped.startswith("#")
        if is_comment or idx in doc_lines or len(stripped) > 400:
            continue
        for pattern, rule, why in CLAIM_PATTERNS:
            if not re.search(pattern, lowered):
                continue
            out.append(
                Finding(
                    rule=rule,
                    severity="low",
                    file=rel,
                    line=idx,
                    message=f"security claim {pattern!r}: {why}",
                    snippet=stripped[:200],
                    finding_id=_finding_id(rel, idx, rule),
                )
            )
            break
    return out


# ---------------------------------------------------------------------------
# acknowledgement of reviewed findings
# ---------------------------------------------------------------------------

ACK_FILENAME = ".qa_acknowledged.json"


def load_acknowledgements(path: Path | str | None = None) -> dict[str, str]:
    """Reviewed findings, mapped to the reason a human gave.

    Keeps the scanner usable: a claim that has been checked once should not
    reappear on every run, or people stop reading the output. A malformed file
    yields no acknowledgements (fail to nag, never fail to scan).
    """
    target = Path(path) if path is not None else _repo_root() / ACK_FILENAME
    if not target.is_file():
        return {}
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    acked = raw.get("acknowledged")
    if not isinstance(acked, dict):
        return {}
    return {k: str(v) for k, v in acked.items()}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def find_by_id(report: ScanReport, finding_id: str) -> Finding | None:
    """Resolve a short finding id back to its finding, or None."""
    for f in report.findings:
        if f.finding_id == finding_id:
            return f
    return None


# ---------------------------------------------------------------------------
# rule 5: files that do not compile
# ---------------------------------------------------------------------------


def rule_compile_error(path: Path, source: str, rel: str) -> list[Finding]:
    try:
        compile(source, str(path), "exec")
    except SyntaxError as exc:
        return [
            Finding(
                rule="COMPILE_ERROR",
                severity="critical",
                file=rel,
                line=exc.lineno or 0,
                message=f"file does not parse: {exc.msg}",
                snippet=(exc.text or "").strip()[:200],
                finding_id=_finding_id(rel, exc.lineno or 0, "COMPILE_ERROR"),
            )
        ]
    return []


# ---------------------------------------------------------------------------
# scanner
# ---------------------------------------------------------------------------

RULE_UNDEFINED_NAME = "UNDEFINED_NAME"
RULE_IMPORT_ERROR = "IMPORT_ERROR"
RULE_SWALLOWED_ERROR = "SWALLOWED_ERROR"
RULE_FABRICATED_SUCCESS = "FABRICATED_SUCCESS"
RULE_UNENFORCED_CLAIM = "UNENFORCED_CLAIM"
RULE_COMPILE_ERROR = "COMPILE_ERROR"

RULES = {
    RULE_UNDEFINED_NAME: rule_undefined_name,
    RULE_IMPORT_ERROR: rule_undeclared_import,
    RULE_SWALLOWED_ERROR: rule_swallowed_error,
    RULE_FABRICATED_SUCCESS: rule_fabricated_success,
    RULE_UNENFORCED_CLAIM: rule_unenforced_claim,
    RULE_COMPILE_ERROR: rule_compile_error,
}


@dataclass
class ScanReport:
    findings: list[Finding] = field(default_factory=list)
    scanned_files: int = 0
    scanner_errors: list[str] = field(default_factory=list)
    acknowledged: int = 0

    def by_rule(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in self.findings:
            counts[f.rule] = counts.get(f.rule, 0) + 1
        return counts

    def by_severity(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in self.findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
        return counts

    def worst(self) -> str | None:
        if not self.findings:
            return None
        return min(
            self.findings,
            key=lambda f: SEVERITY_ORDER.get(f.severity, 9),
        ).severity

    def to_dict(self) -> dict[str, Any]:
        return {
            "scanned_files": self.scanned_files,
            "total": len(self.findings),
            "by_severity": self.by_severity(),
            "by_rule": self.by_rule(),
            "findings": [f.to_dict() for f in self.findings],
            "scanner_errors": self.scanner_errors,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def _iter_python_files(root: Path) -> Iterator[Path]:
    for p in sorted(root.rglob("*.py")):
        parts = set(p.parts)
        if ".venv" in parts or "__pycache__" in parts or ".git" in parts:
            continue
        yield p


def scan(
    root: Path | str = "src/jarvis",
    *,
    rules: Sequence[str] | None = None,
    severities: Sequence[str] | None = None,
    include_acknowledged: bool = False,
    ack_file: Path | str | None = None,
) -> ScanReport:
    """Scan a package for the defect classes above.

    `root` defaults to the installed `src/jarvis` package, so this works from
    any working directory.

    Findings already acknowledged in `.qa_acknowledged.json` are filtered out
    unless `include_acknowledged=True`.
    """
    base = Path(root)
    if not base.is_absolute() and not base.is_dir():
        base = Path(__file__).resolve().parents[1] / base.name
    base = base.resolve()

    # Finding paths must be repo-relative so `jarvis bugfix` can resolve them
    # against the repo root. Stripping three parent levels from
    # <repo>/src/jarvis yields the drive root on Windows, producing paths like
    # `JARVIS2.0\src\...` that resolve nowhere.
    repo_root = _find_pyproject(base)
    repo_root = repo_root.parent if repo_root else _repo_root()

    selected = {r.upper() for r in rules} if rules else set(RULES)
    report = ScanReport()

    for path in _iter_python_files(base):
        report.scanned_files += 1
        try:
            rel = path.relative_to(repo_root).as_posix()
        except ValueError:
            rel = path.name
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            report.scanner_errors.append(f"{path}: cannot read: {exc}")
            continue

        report.findings.extend(rule_compile_error(path, source, rel))
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue  # already reported by COMPILE_ERROR

        for name, rule_fn in RULES.items():
            if name not in selected or name == "COMPILE_ERROR":
                continue
            try:
                if name == "COMPILE_ERROR":
                    continue
                report.findings.extend(rule_fn(path, tree, source, rel))  # type: ignore[arg-type]
            except Exception as exc:  # a broken rule must not hide the scan
                report.scanner_errors.append(
                    f"{name} failed on {rel}: {type(exc).__name__}: {exc}"
                )

    if severities:
        keep = {s.lower() for s in severities}
        report.findings = [f for f in report.findings if f.severity in keep]

    if not include_acknowledged:
        acked = load_acknowledgements(ack_file)
        if acked:
            report.findings = [f for f in report.findings if f.finding_id not in acked]

    report.findings.sort(
        key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.file, f.line)
    )
    return report
