"""Act on the owner's access commands.

Commands (first non-empty line of the owner's comment on an access request):
  /approve @login finance fleet invite the requester (@login must be the request's author) with
                                write access to those Brains (the normal choice)
  /approve @login finance read  invite with read-only access; only for Brains owned by an
                                organization (GitHub ignores the permission on a personal-account
                                repository and every collaborator can write, so it is refused there)
  /deny [reason]                close the request politely
  /remove [@]<github-name> finance  remove that person from those Brains (and cancel invitations)
Brains are always named one by one: there is no "all", so a reply never lists every Brain.

Commands act only on an open issue with the access-request label, or an open issue the owner
opened. The workflow runs this only for comments by the owner, and it is checked again here. Brain
names map to repositories in the BRAINS repository secret, e.g. {"finance": "conrelma/repo"}. The
secret keeps the value out of the step's env listing in the public run log, and this script never
prints gh output or BRAINS values. Repository names are never written into this public repository.
If BRAINS is unset or malformed, no command acts.

Error replies and log lines never include GitHub's error text (it can name a private repository):
only the Brain name and the HTTP status. Any failed gh step makes the run exit 1 (red).

Env: GH_TOKEN (this repo's issues), ADMIN_TOKEN (adds/removes collaborators), REPO, ISSUE,
ISSUE_STATE, ISSUE_LABELS (JSON list of names), ISSUE_AUTHOR, ISSUE_AUTHOR_ID, ISSUE_AUTHOR_TYPE,
COMMENT_AUTHOR_ID, COMMENT_AUTHOR_ASSOCIATION, BODY, BRAINS.
Usage: access.py command | access.py --selftest
"""
import json
import os
import re
import subprocess
import sys

OWNER_ID = "6285991"
USER = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
BRAIN = re.compile(r"[a-z0-9-]{1,30}")
FORM = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ISSUE_TEMPLATE", "request-access.yml")
BRAIN_REPO = re.compile(r"conrelma/[A-Za-z0-9._-]{1,100}")
FAILED = []  # gh steps that failed (Brain name and HTTP status only); any one makes the run red


def first_words(body):
    return next((l.split() for l in (body or "").splitlines() if l.strip()), [])


def parse(body, keys):
    """Return (command, info) or (None, error). keys: allowed Brain names."""
    words = first_words(body)
    if not words or not words[0].startswith("/"):
        return None, "not a command"
    cmd, rest = words[0].lower(), words[1:]
    if cmd == "/deny":
        return "deny", {"reason": " ".join(rest)[:200]}
    if cmd == "/approve":
        if not rest or not rest[0].startswith("@") or not USER.fullmatch(rest[0][1:]):
            return None, "use: /approve @<github-name> <brain> [<brain> ...] [read]"
        login, rest = rest[0][1:], rest[1:]
        perm = "pull" if rest and rest[-1].lower() == "read" else "push"
        names = [w.lower() for w in (rest[:-1] if perm == "pull" else rest)]
        bad = [n for n in names if n not in keys]
        if not names or bad:
            return None, "unknown or missing Brain name: " + ", ".join(bad or ["(none)"])
        return "approve", {"login": login, "brains": names, "perm": perm}
    if cmd == "/remove":
        user = rest[0][1:] if rest and rest[0].startswith("@") else (rest[0] if rest else "")
        if len(rest) < 2 or not USER.fullmatch(user):
            return None, "use: /remove <github-name> <brain> [<brain> ...]"
        names = [w.lower() for w in rest[1:]]
        bad = [n for n in names if n not in keys]
        if bad:
            return None, "unknown Brain name: " + ", ".join(bad)
        return "remove", {"user": user, "brains": names}
    return None, "unknown command"


def load_brains(raw):
    """The BRAINS mapping {name: "conrelma/repo"}, or None if it is unset or malformed."""
    try:
        brains = json.loads(raw or "")
    except ValueError:
        return None
    if not isinstance(brains, dict) or not brains:
        return None
    for name, repo in brains.items():
        if not (isinstance(repo, str) and BRAIN.fullmatch(name) and BRAIN_REPO.fullmatch(repo)
                and repo.split("/")[1] not in (".", "..")):
            return None
    return brains


def is_access_request(state, labels_json, author_id):
    """Open, and labelled access-request (set by the request form) or opened by the owner."""
    try:
        labels = json.loads(labels_json or "[]")
    except ValueError:
        labels = []
    labelled = isinstance(labels, list) and "access-request" in labels
    return state == "open" and (labelled or author_id == OWNER_ID)


def status(err):
    """Only the HTTP status from a gh error, never the text (it can name a private repository)."""
    m = re.search(r"HTTP \d{3}", err or "")
    return m.group(0) if m else "error"


def gh(step, *args, token=None, ok404=False):
    """Run gh; return (ok, stdout, status). A failure is noted as `step`, which names no repository."""
    env = dict(os.environ)
    if token:
        env["GH_TOKEN"] = token
    r = subprocess.run(["gh", *args], capture_output=True, text=True, env=env)
    err = status(r.stderr)
    ok = r.returncode == 0 or (ok404 and err == "HTTP 404")
    if not ok:
        FAILED.append(f"{step} ({err})")
    return ok, r.stdout, err


def reply(text):
    gh("reply", "issue", "comment", os.environ["ISSUE"], "-R", os.environ["REPO"], "--body", text)


def finish(reason):
    """Close and lock the request. Its text is left alone: GitHub keeps the edit history of a public
    issue, so editing it would hide nothing."""
    n, repo = os.environ["ISSUE"], os.environ["REPO"]
    gh("close", "issue", "close", n, "-R", repo, "--reason", reason)
    gh("lock", "issue", "lock", n, "-R", repo, "--reason", "resolved")


def command():
    if (os.environ.get("COMMENT_AUTHOR_ID") != OWNER_ID
            or os.environ.get("COMMENT_AUTHOR_ASSOCIATION") != "OWNER"):
        print("Ignored: not the owner's comment.")
        return
    body = os.environ.get("BODY", "")
    words = first_words(body)
    if not words or not words[0].startswith("/"):
        return
    if not is_access_request(os.environ.get("ISSUE_STATE"), os.environ.get("ISSUE_LABELS"),
                             os.environ.get("ISSUE_AUTHOR_ID")):
        reply("Command not done: not an open access request.")
        return
    brains = load_brains(os.environ.get("BRAINS"))
    if brains is None:
        reply("Command not done: the BRAINS setting is invalid.")
        return
    cmd, info = parse(body, set(brains))
    if cmd is None:
        reply(f"Command not done: {info}.")
        return
    if cmd == "deny":
        reply("Thank you for asking. This request is not approved." +
              (f" Reason: {info['reason']}" if info["reason"] else ""))
        finish("not planned")
        return
    admin = os.environ.get("ADMIN_TOKEN", "")
    if not admin:
        reply("Command not done: the robot has no access token yet (the owner must set BRAIN_ADMIN_TOKEN).")
        return
    if cmd == "approve":
        who = os.environ.get("ISSUE_AUTHOR", "")
        if os.environ.get("ISSUE_AUTHOR_TYPE") != "User" or not USER.fullmatch(who):
            reply("Command not done: the requester is not a normal GitHub user.")
            return
        if info["login"].lower() != who.lower():
            reply(f"Command not done: @{info['login']} did not open this request (@{who} did).")
            return
        if info["perm"] == "pull":  # GitHub honours the permission only on organization repositories
            for name in info["brains"]:
                ok, out, err = gh(f"owner type {name}", "api", f"repos/{brains[name]}", "--jq",
                                  ".owner.type", token=admin)
                if not ok:
                    reply(f"Command not done: could not check {name} ({err}).")
                    return
                if out.strip() != "Organization":
                    reply("Command not done: read-only access needs the Brain to be in an organization;"
                          " approve without 'read' for normal access.")
                    return
        done, failed = [], []
        for name in info["brains"]:
            ok, _, err = gh(f"invite {name}", "api", "-X", "PUT", f"repos/{brains[name]}/collaborators/{who}",
                            "-f", f"permission={info['perm']}", "--silent", token=admin)
            (done if ok else failed).append(name if ok else f"{name} ({err})")
        level = "read-only" if info["perm"] == "pull" else "write"
        msg = f"Approved for @{who} ({level}): {', '.join(done) or 'none'}."
        if failed:
            msg += f" Could not add: {', '.join(failed)}."
        msg += " Check your email or github.com/notifications for the invitation(s), then give your" \
               " assistant the install sentence from each Brain's front page."
        reply(msg)
        if done and not failed:
            finish("completed")
        return
    if cmd == "remove":
        user, done, failed = info["user"], [], []
        for name in info["brains"]:
            repo, errs = brains[name], []
            ok, _, err = gh(f"remove {name}", "api", "-X", "DELETE", f"repos/{repo}/collaborators/{user}",
                            "--silent", token=admin, ok404=True)  # 404: was not a collaborator
            errs += [] if ok else [err]
            ok, out, err = gh(f"list invitations {name}", "api", "--paginate", f"repos/{repo}/invitations",
                              "--jq", f'.[] | select((.invitee.login|ascii_downcase) == "{user.lower()}") | .id',
                              token=admin)
            errs += [] if ok else [err]
            for inv in (out.split() if ok else []):
                if not inv.isdigit():
                    continue
                ok, _, err = gh(f"cancel invitation {name}", "api", "-X", "DELETE",
                                f"repos/{repo}/invitations/{inv}", "--silent", token=admin)
                errs += [] if ok else [err]
            (failed if errs else done).append(f"{name} ({errs[0]})" if errs else name)
        msg = f"Removed {user} from: {', '.join(done) or 'none'} (access and any open invitation)."
        if failed:
            msg += f" Could NOT remove from: {', '.join(failed)}. Check by hand."
        reply(msg)


def run_fake(env, body, answers=()):
    """Run command() against a stand-in for gh. answers: [(text in the gh call, exit code, stdout)].
    Returns the gh calls made, each as one string."""
    calls, real = [], subprocess.run

    def fake(argv, **_):
        line = " ".join(argv[1:])
        calls.append(line)
        rc, out = next(((rc, out) for key, rc, out in answers if key in line), (0, ""))
        return subprocess.CompletedProcess(argv, rc, out, "gh: failed (HTTP 500)" if rc else "")

    os.environ.update({
        "COMMENT_AUTHOR_ID": OWNER_ID, "COMMENT_AUTHOR_ASSOCIATION": "OWNER", "REPO": "o/r",
        "ISSUE": "7", "ISSUE_STATE": "open", "ISSUE_LABELS": '["access-request"]',
        "ISSUE_AUTHOR": "bob", "ISSUE_AUTHOR_ID": "1", "ISSUE_AUTHOR_TYPE": "User", "ADMIN_TOKEN": "t",
        "BRAINS": '{"finance": "conrelma/x-brain", "fleet": "conrelma/y-brain"}', **env, "BODY": body})
    del FAILED[:]
    subprocess.run = fake
    try:
        command()
    finally:
        subprocess.run = real
    return calls


def selftest():
    keys = {"finance", "fleet", "kit"}
    # 1: write access by default, a last word "read" asks for read-only
    assert parse("/approve @Bob finance fleet", keys) == \
        ("approve", {"login": "Bob", "brains": ["finance", "fleet"], "perm": "push"})
    assert parse("/approve @bob finance read", keys)[1]["perm"] == "pull"
    assert parse("/approve @bob fleet READ", keys)[1] == {"login": "bob", "brains": ["fleet"], "perm": "pull"}
    assert parse("/approve @bob read", keys)[0] is None                  # read alone names no Brain
    assert parse("/Approve @bob FINANCE", keys)[1]["brains"] == ["finance"]
    assert parse("/approve @bob all", keys)[0] is None                   # no "all": names one by one
    assert parse("/remove bob all", keys)[0] is None
    assert parse("/approve finance", keys)[0] is None                    # @login required
    assert parse("/approve @bob", keys)[0] is None
    assert parse("/approve @bob payroll", keys)[0] is None
    assert parse("/approve @bob finance; rm -rf /", keys)[0] is None
    assert parse("/approve @bad\nname finance", keys)[0] is None
    assert parse("\n\n/approve @bob fleet\n> quoted email", keys)[1]["brains"] == ["fleet"]  # blank first
    assert parse("/deny not now", keys) == ("deny", {"reason": "not now"})
    assert parse("/remove 949BFN fleet", keys) == ("remove", {"user": "949BFN", "brains": ["fleet"]})
    assert parse("/remove @949BFN fleet", keys) == ("remove", {"user": "949BFN", "brains": ["fleet"]})
    assert parse("/remove @ fleet", keys)[0] is None
    assert parse("/remove", keys)[0] is None
    assert parse("/remove bad$user fleet", keys)[0] is None
    assert parse("/remove someone", keys)[0] is None
    assert parse("thanks!", keys)[0] is None
    assert parse("", keys)[0] is None
    assert parse("/approve @bob fleet\nsecond line ignored /approve @bob finance", keys)[1]["brains"] == ["fleet"]
    assert status('HTTP 404: Not Found (https://api.github.com/repos/o/secret-repo/x)') == "HTTP 404"
    assert status("dial tcp: lookup api.github.com/repos/o/secret-repo") == "error"

    # 3: BRAINS must be a non-empty map of short names to conrelma repositories
    assert load_brains('{"finance": "conrelma/x-brain", "my-fleet2": "conrelma/Y.brain_2"}') == \
        {"finance": "conrelma/x-brain", "my-fleet2": "conrelma/Y.brain_2"}
    for bad in ("", None, "not json", "[]", "{}", "null", '{"Finance": "conrelma/x"}',
                '{"finance\\n": "conrelma/x"}', '{"a b": "conrelma/x"}', '{"' + "a" * 31 + '": "conrelma/x"}',
                '{"finance": "someone/x"}', '{"finance": "conrelma/x/y"}', '{"finance": "conrelma/.."}',
                '{"finance": "conrelma/"}', '{"finance": "conrelma/x\\n"}', '{"finance": 5}',
                '{"finance": "conrelma/' + "x" * 101 + '"}', '{"ok": "conrelma/x", "bad": "other/y"}'):
        assert load_brains(bad) is None, bad

    # 4: only an open issue with the access-request label, or an open issue the owner opened
    assert is_access_request("open", '[\n  "access-request"\n]', "1")
    assert is_access_request("open", "[]", OWNER_ID)
    assert not is_access_request("closed", '["access-request"]', OWNER_ID)
    assert not is_access_request("open", '["bug"]', "1")
    assert not is_access_request("open", "not json", "1")
    assert not is_access_request(None, None, None)

    # command() end to end, against a stand-in for gh
    assert run_fake({"COMMENT_AUTHOR_ID": "1"}, "/deny") == []           # not the owner: silent
    assert run_fake({}, "thanks, looks good") == []                      # not a command: silent
    c = run_fake({"ISSUE_STATE": "closed"}, "/approve @bob finance")       # 4
    assert len(c) == 1 and "not an open access request." in c[0]
    c = run_fake({"ISSUE_LABELS": "[]"}, "/deny")                        # 4
    assert len(c) == 1 and "not an open access request." in c[0]
    c = run_fake({"BRAINS": '{"finance": "evil/x"}'}, "/deny")           # 3: acts on nothing
    assert len(c) == 1 and "the BRAINS setting is invalid." in c[0]
    c = run_fake({}, "/approve @bob finance read", [(".owner.type", 0, "User\n")])  # 1: personal repo
    assert len(c) == 2 and "read-only access needs the Brain to be in an organization" in c[1]
    c = run_fake({}, "/approve @bob finance fleet read", [(".owner.type", 0, "Organization\n")])
    assert sum("permission=pull" in x for x in c) == 2 and not FAILED
    c = run_fake({}, "/approve @bob finance", [("issue lock", 1, "")])     # 5: lock fails after invite
    assert any("permission=push" in x for x in c) and any("issue comment" in x for x in c)
    assert not any("issue edit" in x for x in c) and FAILED == ["lock (HTTP 500)"]
    c = run_fake({}, "/remove bob fleet", [("collaborators/bob", 1, "")])  # 5: removal fails
    assert "Could NOT remove from: fleet (HTTP 500)" in c[-1] and FAILED == ["remove fleet (HTTP 500)"]
    c = run_fake({}, "/remove @bob fleet", [("invitations --jq", 0, "123\nnot-an-id\n456\n")])
    assert any("--paginate repos/conrelma/y-brain/invitations --jq" in x for x in c)
    assert [x.split()[3] for x in c if "/invitations/" in x] == \
        ["repos/conrelma/y-brain/invitations/123", "repos/conrelma/y-brain/invitations/456"]
    assert "Removed bob from: fleet" in c[-1] and not FAILED
    c = run_fake({}, "/approve @alice finance")                          # not the requester
    assert len(c) == 1 and "@alice did not open this request (@bob did)" in c[0]
    c = run_fake({"ISSUE_AUTHOR_TYPE": "Bot"}, "/approve @bob finance")
    assert len(c) == 1 and "not a normal GitHub user" in c[0]
    c = run_fake({"ADMIN_TOKEN": ""}, "/approve @bob finance")
    assert len(c) == 1 and "no access token" in c[0]
    c = run_fake({}, "/approve @bob finance fleet", [("y-brain/collaborators", 1, "")])  # partial approve
    assert "Approved for @bob (write): finance. Could not add: fleet (HTTP 500)." in c[-1]
    assert not any(x.startswith(("issue close", "issue lock")) for x in c)   # request stays open
    assert FAILED == ["invite fleet (HTTP 500)"]
    del FAILED[:]
    # the request form's checkboxes start with a valid short name and a colon, e.g. "finance: ..."
    with open(FORM) as f:
        labels = re.findall(r'^\s*- label:\s*"?([^"\n]*)', f.read(), re.M)
    assert labels, "no checkboxes found in the request form"
    for label in labels:
        assert BRAIN.fullmatch(label.split(":", 1)[0]), "bad Brain short name in the request form: " + label
    print("selftest ok")


if __name__ == "__main__":
    {"--selftest": selftest, "command": command}[sys.argv[1]]()
    if FAILED:
        sys.exit("Failed steps: " + "; ".join(FAILED))
