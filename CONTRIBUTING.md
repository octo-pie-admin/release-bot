# Contributing to Octo-Pie-Release-Bot 🐙🥧

Thanks for your interest in contributing! Contributions, whether big or small, help make this project better.

## How to Contribute

### 1. Reporting Bugs
- Use the **Bug Report template** (auto-loaded when you create a new issue).
- Clearly describe the problem, expected behavior, and steps to reproduce.

### 2. Requesting Features
- Use the **Feature Request template**.
- Explain the problem your feature solves, not just the feature itself.

### 3. Submitting Code
- Fork the repo and create a new branch from `main`.
- Follow existing code style and naming conventions.
- Include tests if adding new functionality.
- Submit a pull request with a clear description.

### 4. Pull Request Guidelines
- Keep PRs focused (1 feature or fix per PR).
- Link the related issue(s).
- Be ready for friendly review comments!

---

## Development Setup
1. Clone your fork:
   ```bash
   git clone https://github.com/<your-username>/OctoPieReleaseBot.git
   cd OctoPieReleaseBot
   ```
2. Install [act](https://github.com/nektos/act)
3. Install and run [Ollama](https://ollama.com/) locally
4. Copy .secrets.example and update accordingly
    ```bash
    cp .secrets.example .secrets
    ```
5. Create venv
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```
6. Make changes and run
    ```bash
    act release -e tests/release_event.json --secret-file .secrets -v -b
    ```

# Code of Conduct

Be respectful, welcoming, and constructive. Treat others as you’d want to be treated.