"""Act on the owner's access commands.

Commands (first non-empty line of the owner's comment on an access request):
  /approve @login finance fleet invite the requester (@login must be the request's author) with
                                write access to those Brains
  /approve @login finance read  invite with read-only access
  /deny [reason]                close the request politely
  /remove <github-name> finance remove that person from those Brains (and cancel invitations)

The workflow runs this only for comments by the owner (checked again here). Brain names map to
repositories in the BRAINS repository variable, e.g. {"finance": "owner/repo", ...}; repository
names are never written into this public repository.

Error replies never include GitHub's error text (it can name a private repository): only the
Brain name and the HTTP status.

Env: GH_TOKEN (this repo's issues), ADMIN_TOKEN (adds/removes collaborators), REPO, ISSUE,
ISSUE_AUTHOR, ISSUE_AUTHOR_TYPE, BODY, BRAINS.
Usage: access.py command | access.py --selftest
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

USER = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")


def parse(body, keys):
    """Return (command, info) or (None, error). keys: allowed Brain names."""
    line = next((l.strip() for l in (body or "").splitlines() if l.strip()), "")
    words = line.split()
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
        names = sorted(keys) if names == ["all"] else names
        bad = [n for n in names if n not in keys]
        if not names or bad:
            return None, "unknown or missing Brain name: " + ", ".join(bad or ["(none)"])
        return "approve", {"login": login, "brains": names, "perm": perm}
    if cmd == "/remove":
        if len(rest) < 2 or not USER.fullmatch(rest[0]):
            return None, "use: /remove <github-name> <brain> [<brain> ...]"
        names = [w.lower() for w in rest[1:]]
        names = sorted(keys) if names == ["all"] else names
        bad = [n for n in names if n not in keys]
        if bad:
            return None, "unknown Brain name: " + ", ".join(bad)
        return "remove", {"user": rest[0], "brains": names}
    return None, "unknown command"


def status(err):
    """Only the HTTP status from a gh error, never the text (it can name a private repository)."""
    m = re.search(r"HTTP \d{3}", err or "")
    return m.group(0) if m else "error"


def gh(*args, token=None):
    env = dict(os.environ)
    if token:
        env["GH_TOKEN"] = token
    r = subprocess.run(["gh", *args], capture_output=True, text=True, env=env)
    return r.returncode, r.stdout, status(r.stderr)


def reply(text):
    gh("issue", "comment", os.environ["ISSUE"], "-R", os.environ["REPO"], "--body", text)


def finish(summary, reason):
    """Replace the public request text with a one-line outcome, close and lock it."""
    n, repo = os.environ["ISSUE"], os.environ["REPO"]
    gh("issue", "edit", n, "-R", repo, "--body", summary)
    gh("issue", "close", n, "-R", repo, "--reason", reason)
    gh("issue", "lock", n, "-R", repo, "--reason", "resolved")


def command():
    brains = json.loads(os.environ.get("BRAINS") or "{}")
    admin = os.environ.get("ADMIN_TOKEN", "")
    cmd, info = parse(os.environ.get("BODY", ""), set(brains))
    if cmd is None:
        if info != "not a command":
            reply(f"Command not done: {info}.")
        return
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if cmd == "deny":
        reply("Thank you for asking. This request is not approved." +
              (f" Reason: {info['reason']}" if info["reason"] else ""))
        finish(f"Processed on {today}: not approved.", "not planned")
        return
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
        done, failed = [], []
        for name in info["brains"]:
            code, _, err = gh("api", "-X", "PUT", f"repos/{brains[name]}/collaborators/{who}",
                              "-f", f"permission={info['perm']}", "--silent", token=admin)
            (done if code == 0 else failed).append(name if code == 0 else f"{name} ({err})")
        level = "read-only" if info["perm"] == "pull" else "write"
        msg = f"Approved for @{who} ({level}): {', '.join(done) or 'none'}."
        if failed:
            msg += f" Could not add: {', '.join(failed)}."
        msg += " Check your email or github.com/notifications for the invitation(s), then give your" \
               " assistant the install sentence from each Brain's front page."
        reply(msg)
        if done and not failed:
            finish(f"Processed on {today}: @{who} approved for {', '.join(done)} ({level}).", "completed")
        return
    if cmd == "remove":
        user, done, failed = info["user"], [], []
        for name in info["brains"]:
            repo = brains[name]
            code, _, err = gh("api", "-X", "DELETE", f"repos/{repo}/collaborators/{user}", "--silent",
                              token=admin)
            ok = code == 0 or err == "HTTP 404"  # 404: was not a collaborator
            code2, out, err2 = gh("api", f"repos/{repo}/invitations", "--jq",
                                  f'.[] | select((.invitee.login|ascii_downcase) == "{user.lower()}") | .id', token=admin)
            ok = ok and code2 == 0
            for inv in out.split():
                c3, _, _ = gh("api", "-X", "DELETE", f"repos/{repo}/invitations/{inv}", "--silent",
                              token=admin)
                ok = ok and c3 == 0
            (done if ok else failed).append(name if ok else f"{name} ({err if code else err2})")
        msg = f"Removed {user} from: {', '.join(done) or 'none'} (access and any open invitation)."
        if failed:
            msg += f" Could NOT remove from: {', '.join(failed)}. Check by hand."
        reply(msg)


def selftest():
    keys = {"finance", "fleet", "kit"}
    assert parse("/approve @Bob finance fleet", keys) == \
        ("approve", {"login": "Bob", "brains": ["finance", "fleet"], "perm": "push"})
    assert parse("/approve @bob finance read", keys)[1]["perm"] == "pull"
    assert parse("/Approve @bob ALL", keys)[1]["brains"] == ["finance", "fleet", "kit"]
    assert parse("/approve finance", keys)[0] is None                    # @login required
    assert parse("/approve @bob", keys)[0] is None
    assert parse("/approve @bob payroll", keys)[0] is None
    assert parse("/approve @bob finance; rm -rf /", keys)[0] is None
    assert parse("/approve @bad\nname finance", keys)[0] is None
    assert parse("\n\n/approve @bob fleet\n> quoted email", keys)[1]["brains"] == ["fleet"]  # blank first
    assert parse("/deny not now", keys) == ("deny", {"reason": "not now"})
    assert parse("/remove 949BFN fleet", keys) == ("remove", {"user": "949BFN", "brains": ["fleet"]})
    assert parse("/remove bad$user fleet", keys)[0] is None
    assert parse("/remove someone", keys)[0] is None
    assert parse("thanks!", keys)[0] is None
    assert parse("", keys)[0] is None
    assert parse("/approve @bob fleet\nsecond line ignored /approve @bob finance", keys)[1]["brains"] == ["fleet"]
    assert status('HTTP 404: Not Found (https://api.github.com/repos/o/secret-repo/x)') == "HTTP 404"
    assert status("dial tcp: lookup api.github.com/repos/o/secret-repo") == "error"
    print("selftest ok")


if __name__ == "__main__":
    {"--selftest": selftest, "command": command}[sys.argv[1]]()
