#!/usr/bin/env node

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const FRONTEND_PACKAGE_JSON = path.join(__dirname, '../frontend/package.json');

function runCommand(command, cwd = process.cwd()) {
  console.log(`\n📦 Running: ${command}`);
  try {
    execSync(command, { 
      cwd, 
      stdio: 'inherit',
      shell: true 
    });
    return true;
  } catch (error) {
    console.error(`\n❌ Error running: ${command}`);
    process.exit(1);
  }
}

function bumpVersion(type = 'patch') {
  console.log(`\n🔄 Bumping version (${type})...`);
  
  const packageJson = JSON.parse(fs.readFileSync(FRONTEND_PACKAGE_JSON, 'utf8'));
  const currentVersion = packageJson.version;
  
  const [major, minor, patch] = currentVersion.split('.').map(Number);
  let newVersion;
  
  switch (type) {
    case 'major':
      newVersion = `${major + 1}.0.0`;
      break;
    case 'minor':
      newVersion = `${major}.${minor + 1}.0`;
      break;
    case 'patch':
    default:
      newVersion = `${major}.${minor}.${patch + 1}`;
      break;
  }
  
  packageJson.version = newVersion;
  fs.writeFileSync(FRONTEND_PACKAGE_JSON, JSON.stringify(packageJson, null, 2) + '\n');
  
  console.log(`✅ Version bumped: ${currentVersion} → ${newVersion}`);
  return newVersion;
}

function gitCommitAndPush(version) {
  console.log(`\n📝 Checking git status...`);
  
  // Check git status first
  try {
    const statusOutput = execSync('git status --porcelain', { 
      encoding: 'utf-8',
      stdio: 'pipe'
    });
    
    if (statusOutput.trim()) {
      console.log('\n📋 Files with changes:');
      console.log(statusOutput);
      
      // Add all modified and new files (excluding debug/test files)
      console.log('\n📦 Adding relevant files...');
      runCommand('git add backend/app.py backend/scraper/scraper.py frontend/src/App.jsx frontend/package.json');
      
      // Add other modified files if they exist
      if (statusOutput.includes('README.md')) {
        runCommand('git add README.md');
      }
      if (statusOutput.includes('DEPLOYMENT.md')) {
        runCommand('git add DEPLOYMENT.md');
      }
      if (statusOutput.includes('.gitignore')) {
        runCommand('git add .gitignore');
      }
      if (statusOutput.includes('package.json')) {
        runCommand('git add package.json');
      }
      if (statusOutput.includes('package-lock.json')) {
        runCommand('git add package-lock.json');
      }
      if (statusOutput.includes('scripts/')) {
        runCommand('git add scripts/');
      }
    } else {
      console.log('No changes to commit');
      return;
    }
  } catch (error) {
    console.error('Error checking git status:', error.message);
    process.exit(1);
  }
  
  console.log(`\n📝 Committing changes...`);
  runCommand(`git commit -m "chore: bump version to ${version} and add player scraping features"`);
  
  console.log(`\n🚀 Pushing to repository...`);
  runCommand('git push');
  
  console.log(`\n✅ Successfully pushed version ${version} to repository!`);
}

// Main execution
console.log('🚀 Starting automated version bump and push process...\n');

// Step 1: Build
console.log('📦 Step 1: Building frontend...');
runCommand('npm run build', path.join(__dirname, '../frontend'));

// Step 2: Bump version
console.log('\n📦 Step 2: Bumping version...');
const newVersion = bumpVersion('patch'); // Default to patch, can be made configurable

// Step 3: Commit and push
console.log('\n📦 Step 3: Committing and pushing...');
gitCommitAndPush(newVersion);

console.log('\n🎉 All done!');

