# Contribution Guide

**Last Updated:** 2026-01-01

---

## Getting started

1. Read the [Development Guide](DEVELOPMENT_GUIDE.md) to set up your local environment.
2. Browse open issues labelled `good first issue` or `help wanted`.
3. Comment on the issue you'd like to work on to avoid duplicate effort.

---

## Branching strategy

| Branch | Purpose |
|--------|---------|
| `main` | Stable, deployable at all times |
| `feat/<topic>` | New features |
| `fix/<topic>` | Bug fixes |
| `chore/<topic>` | Tooling, dependency, or configuration changes |
| `docs/<topic>` | Documentation-only changes |

Branch from `main` and open a pull request back into `main`.

---

## Commit messages

Follow **Conventional Commits**:

```
<type>(<optional scope>): <subject>

[optional body]

[optional footer: Closes #123]
```

Common types: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`, `perf`.

---

## Pull request checklist

Before requesting review, verify:

- [ ] `ruff check .` passes (backend)
- [ ] `npm run lint` passes (frontend)
- [ ] All existing tests pass (`pytest -q`)
- [ ] New behaviour has test coverage
- [ ] Public-facing API changes are reflected in `docs/02_api/API.md`
- [ ] PR title follows Conventional Commits format
- [ ] Breaking changes (if any) are noted in `CHANGELOG.md`

---

## Code review SLO

Maintainers aim to review pull requests within **2 business days**.  
Stale PRs (no activity for 14 days) may be closed with a `stale` label.

---

## Reporting security issues

Do **not** open a public GitHub issue for security vulnerabilities.  
Email `security@your-org.com` and follow the process in [SECURITY.md](../../docs/04_security/SECURITY.md).

---

## License

By contributing you agree that your changes will be licensed under the project's [LICENSE](../../LICENSE).
