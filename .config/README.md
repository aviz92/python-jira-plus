# Configuration Files

This directory contains all the linter and code quality configuration files for the project.

## Files Overview

- **`black.toml`** - Black code formatter configuration
  - Line length: 120 characters
  - Target Python version: 3.12+
  - Excludes common build/cache directories

- **`flake8.cfg`** - Flake8 linter configuration
  - Line length: 120 characters
  - Ignores specific style rules (E203, E501, W503)
  - Focuses on blank line rules (E302, E303, E305)

- **`isort.cfg`** - Import sorting configuration
  - Uses Black profile for compatibility
  - Line length: 120 characters
  - Multi-line output with trailing commas

- **`pylintrc`** - Pylint linter configuration
  - Line length: 120 characters
  - Disables common warnings for cleaner output
  - Focuses on meaningful code quality issues

- **`ruff.toml`** - Ruff linter configuration
  - Fast Python linter and formatter
  - Line length: 120 characters
  - Selects comprehensive rule sets (E, W, F, I, B, C4, UP, ANN, T20)
  - Ignores specific rules for better developer experience

## Usage

These configurations are automatically used by:
- Pre-commit hooks (see `.pre-commit-config.yaml`)
- IDE/editor integrations
- Command-line tools when run from project root

## Customization

To modify any configuration:
1. Edit the relevant file in this directory
2. Test with: `pre-commit run --all-files`
3. Commit the changes

All tools will automatically pick up the new configuration.
