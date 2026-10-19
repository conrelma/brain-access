# Brain access requests

Ask for access to one of the owner's private Brains: shared notebooks that AI assistants read and
grow together.

## How to ask

1. Sign in to GitHub. (No account? Create one first at github.com.)
2. Open **Issues → New issue → Request access** in this repository.
3. Tick the Brains you need and say in one line why.
4. The owner gets an email and replies. A robot then sends you a GitHub invitation for each Brain
   approved. Accept it from your email or from github.com/notifications.
5. Then give your AI assistant the install sentence from the Brain's front page.

**This page is public, and your request stays visible.** Write only your name and which notebook
you need. Never write personal details, company details or anything private. After the owner
decides, the request is closed and locked.

## For the owner

Reply to the request email, or comment on the request, with one of these as the first line. Check
the requester's GitHub name in the email's sender line, not the name they typed.

| Command | What happens |
|---|---|
| `/approve @their-github-name finance fleet` | Invites them to those Brains with write access |
| `/approve @their-github-name fleet read` | Invites them with read-only access |
| `/deny` (optional reason) | Closes the request politely |
| `/remove their-github-name finance` | Removes them from those Brains, including open invitations |

Only the owner's commands count. The robot refuses an approval when the name does not match the
person who opened the request. Brain names map to repositories in the repository variable
`BRAINS`, which is not public. Never forward a request email: replying from the forwarded copy
would post as the owner.

The owner's assistant runs an access review once a quarter in its daily round: who has access to
which Brain, with ready-made `/remove` lines for anyone who no longer needs it.
