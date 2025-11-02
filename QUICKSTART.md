# Quick Start - Pushing to GitHub

## Steps to push this project to GitHub:

1. **Create a new repository on GitHub**:
   - Go to https://github.com/new
   - Name it (e.g., `Tracker_Testing`)
   - Don't initialize with README, .gitignore, or license
   - Click "Create repository"

2. **Add the remote and push**:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git
   git branch -M main
   git push -u origin main
   ```

3. **Or if you already created the repo with a README**:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git
   git pull origin main --allow-unrelated-histories
   git push -u origin main
   ```

Replace `YOUR_USERNAME` and `REPO_NAME` with your actual GitHub username and repository name.

