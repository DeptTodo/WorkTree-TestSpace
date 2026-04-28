# Shared Test Repository Fixture

## Setup

```bash
# Create bare origin repo
git init --bare /tmp/wt-test-origin.git

# Clone as "main" working copy, seed initial content
git clone /tmp/wt-test-origin.git /tmp/wt-main
cd /tmp/wt-main
git config user.email "main@test"
git config user.name "Main"

# Seed files
cat > src/app.py << 'PY'
"""Main application module."""

VERSION = "1.0.0"

def greet(name: str) -> str:
    """Return a greeting message."""
    return f"Hello, {name}!"

def farewell(name: str) -> str:
    """Return a farewell message."""
    return f"Goodbye, {name}!"

def calculate(a: int, b: int) -> int:
    """Return sum of two numbers."""
    return a + b

if __name__ == "__main__":
    print(greet("World"))
PY

cat > README.md << 'MD'
# Test Project

A sample project for worktree testing.

## Features
- Greeting
- Farewell
- Calculator
MD

cat > config.json << 'JSON'
{
  "name": "test-project",
  "version": "1.0.0",
  "settings": {
    "debug": false,
    "log_level": "info"
  }
}
JSON

git add .
git commit -m "Initial commit"
git push origin main
```

## Worktree Creation (per user)

```bash
# User A worktree
git clone /tmp/wt-test-origin.git /tmp/wt-user-a
cd /tmp/wt-user-a
git config user.email "user-a@test"
git config user.name "UserA"
git checkout -b feat/user-a-task

# User B worktree
git clone /tmp/wt-test-origin.git /tmp/wt-user-b
cd /tmp/wt-user-b
git config user.email "user-b@test"
git config user.name "UserB"
git checkout -b feat/user-b-task
```

## File Layout

```
src/app.py        -- main module (shared editing target)
README.md         -- documentation
config.json       -- configuration
```
