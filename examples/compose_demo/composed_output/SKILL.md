<!-- PRECEDENCE: default -->
<!-- The following content is from the default-level skill -->

# Additional Context

This is the default code review configuration used across all projects.

---
name: code-reviewer
description: Default code review skill
version: 1.0.0
---

# Code Review Skill

## Overview

This skill helps review code for quality and best practices.

## Instructions

When reviewing code:
1. Check for proper error handling
2. Verify code style consistency
3. Look for potential bugs
4. Suggest improvements

## Default Settings

- Language: Python
- Max file size: 1000 lines
- Review depth: Standard



<!-- PRECEDENCE: user (overrides default) -->
<!-- The following content is from the user-level skill and takes priority -->
<!-- When conflicts exist, follow the user-level instructions below -->

---
name: code-reviewer-custom
description: User customization for code review
version: 1.1.0
---

# Custom Review Settings

## User Override Instructions

For this project, use these CUSTOM rules instead:

1. Focus heavily on security vulnerabilities
2. Enforce strict type hints
3. Require docstrings on all public functions
4. Use Google style for docstrings (not NumPy style)

## Custom Settings

- Language: Python 3.12+
- Max file size: 500 lines (stricter than default)
- Review depth: Deep
- Security focus: High priority

