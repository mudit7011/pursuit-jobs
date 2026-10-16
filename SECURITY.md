# Security policy

Pursuit handles credentials and logged-in sessions for job sites, so security reports are taken seriously.

## Reporting a vulnerability

Please don't open a public issue. Use GitHub's [private vulnerability reporting](https://github.com/mudit7011/pursuit-jobs/security/advisories/new) instead, with steps to reproduce and the impact you expect. You'll get a reply within a week.

## Keeping your own setup safe

- `.env`, `config/`, `sessions/` and `data/` hold your keys, cookies and application history. Never commit or share them.
- The dashboard API listens on `127.0.0.1` only and has no login. Don't expose it to a network.
- Use a Gmail app password, not your real password.
