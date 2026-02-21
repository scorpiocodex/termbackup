Remove-Item .git -Recurse -Force -ErrorAction SilentlyContinue

git init -b main
git config user.name "ScorpioCodeX"
git config user.email "scorpiocodex0@gmail.com"

git add .
git commit -m "chore: V6 Nexus - Zero Trust UI Overhaul & Plugin System"

# In some cases, to force GitHub to drop old associated data, we link
# and push without preserving any old refs.
git remote add origin https://github.com/scorpiocodex/Termbackup.git
git push -u origin main --force
