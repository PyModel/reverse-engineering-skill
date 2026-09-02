#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const skillDir = path.resolve(__dirname, '..');
const pkg = require(path.join(skillDir, 'package.json'));

const args = process.argv.slice(2);
const command = args[0];

function showHelp() {
  console.log(`
reverse-engineering-skill v${pkg.version}
Deterministic binary analysis & reverse engineering agent skill.

Usage:
  npx reverse-engineering-skill <command> [options]

Commands:
  path                 Print the absolute filesystem path to this skill directory
  install [dir]        Install/copy skill files to a destination directory
                       (default: .agent/skills/reverse-engineering)
  triage <file>        Run triage_binary.py (container, arch, entropy, compiler hints)
  entropy <file>       Run calculate_entropy.py (section-by-section Shannon entropy)
  gopcln <file>        Run extract_go_metadata.py (recover Go symbols from .gopclntab)
  validate <file>      Run validate_struct.py (validate struct offsets and padding)
  --version, -v        Show package version
  --help, -h           Show this help message
`);
}

if (!command || command === '--help' || command === '-h') {
  showHelp();
  process.exit(0);
}

if (command === '--version' || command === '-v') {
  console.log(pkg.version);
  process.exit(0);
}

if (command === 'path') {
  console.log(skillDir);
  process.exit(0);
}

if (command === 'install') {
  const destDir = path.resolve(process.cwd(), args[1] || path.join('.agent', 'skills', 'reverse-engineering'));
  console.log(`Installing reverse-engineering skill to: ${destDir}`);
  
  fs.mkdirSync(destDir, { recursive: true });

  const itemsToCopy = ['SKILL.md', 'scripts', 'references', 'examples'];
  for (const item of itemsToCopy) {
    const src = path.join(skillDir, item);
    const dst = path.join(destDir, item);
    if (fs.existsSync(src)) {
      fs.cpSync(src, dst, { recursive: true });
    }
  }

  console.log('Skill installed successfully.');
  process.exit(0);
}

const scriptMap = {
  triage: path.join(skillDir, 'scripts', 'triage_binary.py'),
  entropy: path.join(skillDir, 'scripts', 'calculate_entropy.py'),
  gopcln: path.join(skillDir, 'scripts', 'extract_go_metadata.py'),
  validate: path.join(skillDir, 'scripts', 'validate_struct.py'),
};

if (scriptMap[command]) {
  const targetFile = args[1];
  if (!targetFile) {
    console.error(`Error: Missing target file for command "${command}".`);
    console.error(`Usage: reverse-engineering-skill ${command} <target_file>`);
    process.exit(1);
  }

  const scriptPath = scriptMap[command];
  const pyArgs = [scriptPath, ...args.slice(1)];
  const result = spawnSync('python3', pyArgs, { stdio: 'inherit' });
  process.exit(result.status || 0);
}

console.error(`Unknown command: "${command}"\n`);
showHelp();
process.exit(1);
