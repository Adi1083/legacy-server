# Contributing to IND PROJECT Control Center & Free Fire 2019 Restoration

Thank you for your interest in contributing to the IND PROJECT. To ensure smooth development and avoid merge conflicts, please review the branching strategy and workflow guidelines below before opening a Pull Request.

---

## 1. Branching Strategy

Our repository uses an isolated two-tier branching structure:

- **`main` (Production / Protected)**:
  - Stable release branch.
  - **Direct pushes are strictly restricted to the project owner (`@Adi1083`).**
  - No pull requests should target `main` directly from outside contributors.
- **`develop` (Active Contribution / Staging)**:
  - This is the primary branch for all contributors.
  - All new features, bug fixes, protocol research, and UI improvements must branch off `develop` and target `develop` in your Pull Request.

```
       [ main ] (Protected, Owner Direct Only)
           ▲
           │ (Owner fast-forwards/merges tested milestones)
           │
     [ develop ] (Community Staging Branch)
        ▲     ▲
        │     │
[ feature/* ] [ fix/* ] (Contributor Branches)
```

---

## 2. Step-by-Step Contribution Workflow

To avoid merge conflicts, follow this exact workflow:

### Step 1: Fork and Clone
Fork the repository on GitHub, then clone your fork:
```bash
git clone https://github.com/<your-username>/legacy-server.git
cd legacy-server
```

### Step 2: Checkout the `develop` Branch
Never branch off `main`. Always base your work on `develop`:
```bash
git checkout develop
git pull origin develop
```

### Step 3: Create a Descriptive Topic Branch
Create a new branch with a clean prefix (`feature/`, `fix/`, `docs/`):
```bash
# Examples:
git checkout -b feature/chat-protocol
git checkout -b fix/gold-royale-balance
git checkout -b docs/clarify-udp-timing
```

### Step 4: Keep Changes Focused & Atomic
- Keep each Pull Request small and dedicated to one single feature or bug fix.
- Do **NOT** combine unrelated refactors, UI tweaks, and protocol changes in one PR. This eliminates merge conflicts.

### Step 5: Sync with Latest `develop` Before Pushing
To avoid merge conflicts, always keep your local fork synced with the upstream repository before opening or updating a Pull Request.

#### Option A: Via Command Line (Recommended)
Add upstream remote once:
```bash
git remote add upstream https://github.com/Adi1083/legacy-server.git
```

Fetch and rebase your topic branch onto the latest `upstream/develop`:
```bash
git fetch upstream
git checkout develop
git merge upstream/develop --ff-only
git checkout feature/your-feature-name
git rebase develop
```

If conflicts arise during rebase:
1. Open the conflicting files and resolve markers.
2. Stage the resolved files: `git add <file>`.
3. Continue rebase: `git rebase --continue`.
4. Never create a messy merge commit on your topic branch.

#### Option B: Via GitHub Web Interface
1. Navigate to your fork repository on GitHub.
2. Click **Sync fork** -> **Update branch**.
3. In your local terminal, pull the changes: `git checkout develop && git pull origin develop`.

### Step 6: Submit a Pull Request
1. Push your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
2. Open a Pull Request on GitHub.
3. **Verify the Base Branch:** Ensure the base branch is strictly set to **`develop`** (PRs from forks targeting `main` will be automatically rejected by CI).
4. Fill out the Pull Request template completely. All pre-flight CI checks (syntax compilation, file cleanliness, forbidden file checks) must pass before review.

---

## 3. Fork Merging & Versioning Policy

- **Target Branch:** All community pull requests must target `develop`. Only the project owner (`@Adi1083`) pushes to or merges into `main`.
- **Merge Method:** Pull requests merged into `develop` use Squash and Merge to keep commit history clean and atomic.
- **Auto-Branch Deletion:** Upon merging a PR, head branches on the upstream repository are automatically deleted.
- **Automated Dependency Updates:** Dependabot runs weekly against `develop` for Python packages and GitHub Action versions.
- **Official Releases:** Tags matching `v*.*.*` pushed by the maintainer automatically trigger the GitHub Actions release packager to create sanitized production tarballs with automated changelogs.

---

## 4. Repository Cleanliness & OPSEC Rules

- **Zero Test Script Clutter:** Do not push temporary test scripts (`test_*.py`), raw packet burst dumps, or personal scratch files to the repository. The `.gitignore` enforces this.
- **Zero Raw Dumps:** Never commit decompiled APK folders, raw unity asset bundles, or multimegabyte dumps.
- **Branding Standard:** The project is strictly named **IND PROJECT**. Do not use legacy placeholder names.
- **UDP Combat Subsystem Note:** UDP combat networking is actively in development and currently experimental / not yet mechanically accurate. When working on UDP, document findings and verify against the opcode specs in `docs/combat/`.

---

## 4. Code Style & Standards

- **Python (Server Engine):** Python 3.10+, PEP 8 compliance, explicit type hints where feasible.
- **Frontend (Dashboard):** Apple dark glass design tokens (`tokens.css`), Lucide SVG icons only (zero emojis), no external heavy JS frameworks.
- **Git Commits:** Conventional Commit syntax (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`).
