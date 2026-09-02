const path = require('path');

const skillDir = __dirname;
const skillFile = path.join(skillDir, 'SKILL.md');
const scriptsDir = path.join(skillDir, 'scripts');
const referencesDir = path.join(skillDir, 'references');
const examplesDir = path.join(skillDir, 'examples');

module.exports = {
  skillDir,
  skillFile,
  scriptsDir,
  referencesDir,
  examplesDir,
};
