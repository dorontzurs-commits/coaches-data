# PowerShell script to initialize git and push to GitHub
# Run this script in PowerShell

Write-Host "Initializing Git repository..." -ForegroundColor Green
git init

Write-Host "Adding all files..." -ForegroundColor Green
git add .

Write-Host "Creating initial commit..." -ForegroundColor Green
git commit -m "Initial commit: Coach Scraper application"

Write-Host "Adding remote repository..." -ForegroundColor Green
git remote add origin https://github.com/dorontzurs-commits/coaches-data.git

Write-Host "Setting main branch..." -ForegroundColor Green
git branch -M main

Write-Host "Pushing to GitHub..." -ForegroundColor Green
Write-Host "You may be prompted for GitHub credentials" -ForegroundColor Yellow
git push -u origin main

Write-Host "Done! Your code is now on GitHub." -ForegroundColor Green

