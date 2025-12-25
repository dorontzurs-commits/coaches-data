#!/usr/bin/env node

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const FRONTEND_PACKAGE_JSON = path.join(__dirname, '../frontend/package.json');
const type = process.argv[2] || 'patch';

function bumpVersion(type) {
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
  
  console.log(`Version bumped: ${currentVersion} → ${newVersion}`);
  return newVersion;
}

bumpVersion(type);

