# Contributing to JEE Question Generator

Thank you for your interest in contributing to the JEE Question Generator! 🎉

## 🚀 Quick Start for Contributors

### 1. Fork & Clone

```bash
# Fork the repo on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/JEE-Question-Generator.git
cd JEE-Question-Generator

# Add upstream remote to stay synced with main repo
git remote add upstream https://github.com/ORIGINAL_OWNER/JEE-Question-Generator.git
```

### 2. Set Up Development Environment

```bash
# Create and activate virtual environment
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with your API keys
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 3. Verify Setup

```bash
# Test the pipeline
python -m src.pipeline.predict_pipeline

# Start the API server
uvicorn app:app --reload
# Visit http://localhost:8000/docs
```

## 🌿 Branching Strategy

We use **Git Flow** for branch management:

### Main Branches
- `main` - Production-ready code (protected)
- `develop` - Integration branch for features

### Supporting Branches
- `feature/*` - New features (branch from `develop`)
- `fix/*` - Bug fixes (branch from `develop` or `main`)
- `hotfix/*` - Urgent production fixes (branch from `main`)
- `release/*` - Release preparation (branch from `develop`)

### Branch Naming Examples
```
feature/pdf-export
feature/question-validation
fix/faiss-indexing-bug
fix/api-response-format
hotfix/critical-security-patch
docs/api-documentation
refactor/data-pipeline
test/integration-tests
```

## 📝 Commit Message Convention

We follow **Conventional Commits** for clear history:

### Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code formatting (no logic change)
- `refactor`: Code restructuring (no feature change)
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `ci`: CI/CD changes

### Examples
```bash
feat(api): add PDF export endpoint

Implements new /export/pdf endpoint that generates
question papers in PDF format using ReportLab.

Closes #23

---

fix(data): resolve Unicode parsing errors in PDFs

PDFs with special characters were failing to parse.
Added encoding detection using chardet library.

Fixes #45

---

docs(readme): update installation instructions

Added Windows-specific setup steps and troubleshooting
section for common virtual environment issues.

---

refactor(pipeline): extract LLM calls into utils

Moved all Groq API calls to utils.py for better
code reusability and easier mocking in tests.
```

## 🔄 Workflow

### For New Features

1. **Sync with upstream**
   ```bash
   git checkout develop
   git pull upstream develop
   ```

2. **Create feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make changes and commit**
   ```bash
   git add .
   git commit -m "feat(component): add new feature"
   ```

4. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Create Pull Request**
   - Go to GitHub and create PR from your branch to `develop`
   - Fill in the PR template
   - Request review from team members

### For Bug Fixes

```bash
git checkout develop
git pull upstream develop
git checkout -b fix/bug-description
# Make fixes
git commit -m "fix(component): resolve bug"
git push origin fix/bug-description
# Create PR to develop
```

### For Hotfixes (Urgent Production Bugs)

```bash
git checkout main
git pull upstream main
git checkout -b hotfix/critical-issue
# Fix the issue
git commit -m "hotfix: resolve critical bug"
git push origin hotfix/critical-issue
# Create PR to BOTH main and develop
```

## 📋 Pull Request Guidelines

### Before Submitting

- [ ] Code follows project style guidelines
- [ ] All tests pass
- [ ] Added tests for new features
- [ ] Updated documentation
- [ ] No merge conflicts with target branch
- [ ] Commit messages follow convention

### PR Title Format

```
<type>(<scope>): <description>
```

Examples:
- `feat(api): add question filtering by difficulty`
- `fix(vector-store): resolve FAISS indexing error`
- `docs(readme): add contributor guidelines`

### PR Description Template

```markdown
## Description
Brief description of what this PR does

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Changes Made
- List key changes
- Highlight important modifications

## Testing
How was this tested?
- [ ] Unit tests
- [ ] Manual testing
- [ ] Integration tests

## Screenshots (if applicable)
Add screenshots for UI changes

## Related Issues
Closes #XX
Fixes #YY

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings
```

## 🧪 Testing

### Run Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_pipeline.py

# Run with coverage
pytest --cov=src tests/
```

### Writing Tests
- Place tests in `tests/` directory
- Mirror the structure of `src/`
- Use descriptive test names
- Include docstrings
- Test edge cases

Example:
```python
def test_parse_question_extracts_options():
    """Test that parse_question_and_options correctly extracts 4 options"""
    question_text = "Q1. What is 2+2?\n1. 3\n2. 4\n3. 5\n4. 6"
    result = parse_question_and_options(question_text)
    assert len(result['options']) == 4
    assert result['options'][1]['text'] == '4'
```

## 💻 Code Style

### Python Style Guide
- Follow **PEP 8**
- Maximum line length: 100 characters
- Use **type hints** for function parameters and returns
- Add **docstrings** to all public functions/classes

### Example
```python
def generate_question(
    query: str,
    subject: str,
    difficulty: str = "Medium"
) -> Dict[str, Any]:
    """
    Generate a new question based on query parameters.
    
    Args:
        query: Search query for retrieving similar questions
        subject: Subject area (Physics, Chemistry, Math)
        difficulty: Difficulty level (Easy, Medium, Hard)
    
    Returns:
        Dictionary containing generated question with metadata
    
    Raises:
        ValueError: If subject is not valid
        APIError: If LLM call fails
    """
    # Implementation
    pass
```

### Linting
```bash
# Install linting tools
pip install black flake8 mypy

# Format code
black src/

# Check for issues
flake8 src/
mypy src/
```

## 📁 Project Areas to Contribute

### 🔴 High Priority
- [ ] PDF export functionality
- [ ] Question validation (SymPy for math)
- [ ] Complete dataset processing
- [ ] Unit test coverage
- [ ] Error handling improvements

### 🟡 Medium Priority
- [ ] Frontend UI (React/Streamlit)
- [ ] Database integration
- [ ] User authentication
- [ ] Answer key generation
- [ ] API rate limiting

### 🟢 Nice to Have
- [ ] Question difficulty tuning
- [ ] Multi-language support
- [ ] Docker containerization
- [ ] CI/CD pipeline
- [ ] Performance optimizations

## 🐛 Reporting Bugs

### Before Reporting
1. Check if the bug is already reported in Issues
2. Ensure you're using the latest version
3. Try to reproduce with minimal code

### Bug Report Template
```markdown
**Describe the bug**
Clear description of what went wrong

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What should have happened

**Screenshots**
If applicable

**Environment:**
- OS: [e.g., Windows 11]
- Python Version: [e.g., 3.13.5]
- Package Versions: [run pip list]

**Additional context**
Any other information
```

## 💡 Suggesting Features

### Feature Request Template
```markdown
**Feature Description**
Clear description of the proposed feature

**Problem It Solves**
What problem does this address?

**Proposed Solution**
How should it work?

**Alternatives Considered**
Other approaches you've thought about

**Additional Context**
Mockups, examples, or references
```

## 📞 Communication

### Channels
- **GitHub Issues**: Bug reports and feature requests
- **Pull Requests**: Code contributions and discussions
- **Discussions**: General questions and ideas

### Response Time
- Bug reports: 24-48 hours
- Feature requests: 3-5 days
- Pull requests: 2-3 days for initial review

## 🏆 Recognition

Contributors will be:
- Listed in README.md
- Credited in release notes
- Mentioned in project documentation

## ❓ Questions?

If you have questions:
1. Check existing documentation
2. Search closed issues
3. Ask in GitHub Discussions
4. Open a new issue with `question` label

---

**Thank you for contributing!** Every contribution, no matter how small, helps make this project better. 🙏
