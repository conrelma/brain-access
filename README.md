# Brain access requests

Ask for access to one of the owner's private Brains: shared notebooks that AI assistants read and
grow together.

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
| `/remove their-github-name finance` | Removes them from those Brains, including open invitations |

Only the owner's commands count, and only in an open request or in an open issue the owner opened
(use one of your own for a `/remove` after the request is closed). The robot refuses an approval
when the name does not match the person who opened the request. If any step fails, the reply says
what was done and the workflow run turns red. Brain names map to repositories in the repository
variable `BRAINS`, which is not public. Never forward a request email: replying from the forwarded
copy would post as the owner.

The owner's assistant runs an access review once a quarter in its daily round: who has access to
which Brain, with ready-made `/remove` lines for anyone who no longer needs it.
