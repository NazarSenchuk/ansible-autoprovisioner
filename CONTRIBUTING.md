# Contributing to Ansible AutoProvisioner

Thanks for wanting to help! Here's how to contribute:

## Quick Start

1. **Find something to work on**:
   - Look for issues labeled `good-first-issue`
   - Check the roadmap in README.md
   - Or suggest your own improvement

2. **Set up your environment**:
   ```bash
   # Fork and clone
   git clone https://github.com/YOUR-USERNAME/ansible-autoprovisioner.git
   cd ansible-autoprovisioner
   
   # Create virtual environment
   python -m venv .venv
   source .venv/bin/activate  # On Mac/Linux
   # .venv\Scripts\activate   # On Windows
   
   # Install
   pip install -e .
   ```

3. **Make your changes** and test them:
   ```bash
   # Run tests
   pytest
   
   # Format code
   black src/ansible_autoprovisioner/ tests/
   ```

4. **Submit a Pull Request**

## How to 

### Create Detectors
1. Determine what detection you need 
2. Write detector class like AWS
3. After testing we will add created detector and you to list of contributors

### 🐛 Report Bugs
1. Check if the bug already exists in Issues
2. Create a new issue with:
   - What happened
   - Steps to reproduce
   - Expected vs actual behavior

### 💡 Suggest Features
1. Search existing issues first
2. Create a new issue with your idea
3. Explain why it would be useful

### 🔧 Fix Bugs or Add Features
1. Comment on the issue to say you're working on it
2. Create a branch: `git checkout -b fix/thing`
3. Make your changes
4. Add tests if possible
5. Submit a Pull Request

## Code Guidelines

- Use meaningful variable names
- Add comments for complex logic
- Keep functions small and focused
- Write simple, readable code
- Update documentation when needed

## Pull Request Checklist

Before submitting:
- [ ] Tests pass
- [ ] Code is formatted (use `black`)
- [ ] Documentation updated
- [ ] No broken functionality
- [ ] Follows existing code style

## Need Help?

- Ask in GitHub Discussions
- Open an issue
- Check existing documentation

---

**All contributions are welcome!** Even small fixes or documentation improvements help. ✨

*Thank you for contributing!*