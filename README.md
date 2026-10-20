# Brain access requests

Ask for access to one of the owner's private Brains: shared notebooks that AI assistants read and
grow together.

## Join in two steps

**Step 1. Ask for access.** Sign in to GitHub (a free account is fine), open
[the request form](https://github.com/conrelma/brain-access/issues/new?template=request-access.yml),
tick what fits your work, and write your first name. The owner decides which Brains you get.

**Step 2. When GitHub emails you that you are approved,** open Claude Code or Codex on your own
computer and paste this:

> Install my new Brains for me: accept my pending GitHub invitations from conrelma for these
> Brains, then follow INSTALL.md in each one. Ask me only for what you cannot do yourself.

Your assistant accepts the invitations, installs each Brain and asks a few questions. You need
Claude Code or Codex on your own computer; the chat websites alone are not enough.

## Which Brain?

| Brain | What it holds |
|---|---|
| `finance` | Company finance recipes (X3 connection, statements, cash flow, dashboards) |
| `fleet` | Running AI assistants at home, plus a Start here track for setting up your own assistant (personal Brain) |
| `yield` | Revenue management recipes (competitor fare tracking, yield and load factor methods) |
| `data` | Company data sources (lakehouse, FlightAware, adsb.lol, QlikView, airport statistics, Reporting Data): how to connect, what is there, which source wins, reconciliation |
| `general` | How the company makes things (brand, documents and decks, meetings and polls, Microsoft 365 and Asana with an assistant, IT and Innovation, company laptop setup) |

When a Brain is added, add its line here and its short name to the BRAINS secret (Brain Kit Recipe 1).
Add the same line to the request form, `.github/ISSUE_TEMPLATE/request-access.yml`.

## How to ask

1. Sign in to GitHub. (No account? Create one first at github.com.)
2. Open **Issues → New issue → Request access** in this repository.
3. Tick the Brains you need and type your first name.
4. The owner gets an email and replies. A robot then sends you a GitHub invitation for each Brain
   approved. Accept it from your email or from github.com/notifications.
5. Then give your AI assistant the install sentence from the Brain's front page.

**This page is public, and your request stays visible.** Write only your first name and tick the
notebooks you need. Never write personal details, company details or anything private. GitHub keeps
the edit history of a public issue, so editing it later does not hide anything. After the owner
decides, the request is closed and locked, and its text stays as it is.

## For the owner

Reply to the request email, or comment on the request, with one of these as the first line. Check
the requester's GitHub name in the email's sender line, not the name they typed.

| Command | What happens |
|---|---|
| `/approve @their-github-name finance fleet` | Invites them to those Brains with write access (the normal choice: their assistant can open issues and pull requests) |
| `/approve @their-github-name fleet read` | Invites them with read-only access. Works only for a Brain owned by an organization. For a Brain on a personal account the robot refuses, because GitHub gives every collaborator there write access |
| `/deny` (optional reason) | Closes the request politely |
| `/remove their-github-name finance` | Removes them from those Brains, including open invitations (a leading `@` is fine) |

Only the owner's commands count, and only in an open request or in an open issue the owner opened
(use one of your own for a `/remove` after the request is closed). The robot refuses an approval
when the name does not match the person who opened the request. Name each Brain: there is no
`all`. If any step fails, the workflow run turns red. The reply lists the invitations and removals
done; a red run after a normal reply means a later step, such as closing or locking, failed.

Brain names map to repositories in the repository secret `BRAINS`. The secret keeps the value out
of the step's settings list in the public run log, and the robot never prints GitHub's answers or
the `BRAINS` value. Never forward a request email: replying from the forwarded copy would post as
the owner.

The owner's assistant runs an access review once a quarter in its daily round: who has access to
which Brain, with ready-made `/remove` lines for anyone who no longer needs it.
