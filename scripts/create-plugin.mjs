#!/usr/bin/env node

import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const TEMPLATE_ID = 'agent-template';
const TEMPLATE_NAME = 'Agent Template';
const TEMPLATE_PACKAGE = 'openclaw-agent-plugin-template';
const TEMPLATE_DOT_DIR = '.agent-template';
const TOOL_NAMES = [
    'start_session',
    'run_agent',
    'get_session_status',
    'stop_run',
    'reset_all',
    'end_session',
];

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const templateRoot = path.resolve(scriptDir, '..');

function usage(exitCode = 0) {
    const stream = exitCode === 0 ? process.stdout : process.stderr;
    stream.write(`Create a new OpenClaw agent plugin from this template.

Usage:
  npm run create:plugin -- <target-dir> --id <plugin-id> --name "<Plugin Name>" [options]

Options:
  --package <name>        package.json name. Defaults to <plugin-id>.
  --tool-prefix <prefix>  Prefix tool names, e.g. "research" -> "research_run_agent".
  --init-git             Initialize a fresh git repository in the new plugin.
  --install              Run npm install in the new plugin.
  --force                Allow target dir to exist if it is empty.
  -h, --help             Show this help.

Example:
  npm run create:plugin -- ../weather-agent --id weather-agent --name "Weather Agent" --tool-prefix weather --init-git
`);
    process.exit(exitCode);
}

function parseArgs(argv) {
    const args = {
        targetDir: '',
        id: '',
        name: '',
        packageName: '',
        toolPrefix: '',
        initGit: false,
        install: false,
        force: false,
    };

    const rest = [...argv];
    while (rest.length) {
        const token = rest.shift();
        if (!token) continue;
        if (token === '-h' || token === '--help') usage(0);
        if (!token.startsWith('-') && !args.targetDir) {
            args.targetDir = token;
            continue;
        }

        switch (token) {
            case '--id':
                args.id = rest.shift() ?? '';
                break;
            case '--name':
                args.name = rest.shift() ?? '';
                break;
            case '--package':
                args.packageName = rest.shift() ?? '';
                break;
            case '--tool-prefix':
                args.toolPrefix = rest.shift() ?? '';
                break;
            case '--init-git':
                args.initGit = true;
                break;
            case '--install':
                args.install = true;
                break;
            case '--force':
                args.force = true;
                break;
            default:
                throw new Error(`Unknown argument: ${token}`);
        }
    }

    return args;
}

function validateSlug(value, label) {
    if (!/^[a-z][a-z0-9-]*$/.test(value)) {
        throw new Error(`${label} must use lowercase letters, numbers, and hyphens, starting with a letter.`);
    }
}

function validateToolPrefix(value) {
    if (!value) return;
    if (!/^[a-z][a-z0-9_]*$/.test(value)) {
        throw new Error('--tool-prefix must use lowercase letters, numbers, and underscores, starting with a letter.');
    }
}

function ensureTarget(targetDir, force) {
    if (!fs.existsSync(targetDir)) return;
    const contents = fs.readdirSync(targetDir).filter((name) => name !== '.DS_Store');
    if (contents.length === 0 && force) return;
    throw new Error(`Target directory already exists and is not empty: ${targetDir}`);
}

function shouldCopy(src) {
    const rel = path.relative(templateRoot, src);
    const parts = rel.split(path.sep);
    if (rel === path.join('scripts', 'create-plugin.mjs')) return false;
    if (parts.includes('.git')) return false;
    if (parts.includes('node_modules')) return false;
    if (parts.includes('dist')) return false;
    if (parts.includes('.agent-template')) return false;
    return true;
}

function walkFiles(dir) {
    const out = [];
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory()) {
            out.push(...walkFiles(fullPath));
        } else if (entry.isFile()) {
            out.push(fullPath);
        }
    }
    return out;
}

function isTextFile(file) {
    const textExtensions = new Set([
        '.json',
        '.md',
        '.mjs',
        '.js',
        '.ts',
        '.yml',
        '.yaml',
        '.txt',
        '',
    ]);
    return textExtensions.has(path.extname(file));
}

function replaceAll(input, from, to) {
    return input.split(from).join(to);
}

function rewriteFiles(targetRoot, replacements) {
    for (const file of walkFiles(targetRoot)) {
        if (!isTextFile(file)) continue;
        let text = fs.readFileSync(file, 'utf8');
        let next = text;
        for (const [from, to] of replacements) {
            next = replaceAll(next, from, to);
        }
        if (next !== text) {
            fs.writeFileSync(file, next, 'utf8');
        }
    }
}

function renameSkillDir(targetRoot, pluginId) {
    const oldDir = path.join(targetRoot, 'skills', TEMPLATE_ID);
    const newDir = path.join(targetRoot, 'skills', pluginId);
    if (oldDir === newDir || !fs.existsSync(oldDir)) return;
    fs.mkdirSync(path.dirname(newDir), { recursive: true });
    fs.renameSync(oldDir, newDir);
}

function removeTemplateOnlyFiles(targetRoot) {
    const packageJsonPath = path.join(targetRoot, 'package.json');
    const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
    if (packageJson.scripts) {
        delete packageJson.scripts['create:plugin'];
    }
    fs.writeFileSync(packageJsonPath, `${JSON.stringify(packageJson, null, 2)}\n`, 'utf8');

    const readmePath = path.join(targetRoot, 'README.md');
    let readme = fs.readFileSync(readmePath, 'utf8');
    readme = readme.replace(
        /\n## Creating Plugins From This Template\n[\s\S]*?(?=\n## How To Turn This Into A Real Plugin)/,
        ''
    );
    readme = readme.replace(/^  create-plugin\.mjs\s+# Scaffold a new plugin from this template\n/m, '');
    fs.writeFileSync(readmePath, readme, 'utf8');
}

function run(command, args, cwd) {
    const result = spawnSync(command, args, {
        cwd,
        stdio: 'inherit',
    });
    if (result.status !== 0) {
        throw new Error(`${command} ${args.join(' ')} failed`);
    }
}

function main() {
    const args = parseArgs(process.argv.slice(2));
    if (!args.targetDir || !args.id || !args.name) usage(1);

    validateSlug(args.id, '--id');
    validateToolPrefix(args.toolPrefix);

    const targetRoot = path.resolve(process.cwd(), args.targetDir);
    const packageName = args.packageName || args.id;
    const dotDir = `.${args.id}`;
    const toolPrefix = args.toolPrefix.trim();

    ensureTarget(targetRoot, args.force);
    fs.cpSync(templateRoot, targetRoot, {
        recursive: true,
        filter: shouldCopy,
    });

    renameSkillDir(targetRoot, args.id);
    removeTemplateOnlyFiles(targetRoot);

    const replacements = [
        [TEMPLATE_PACKAGE, packageName],
        [TEMPLATE_NAME, args.name],
        [TEMPLATE_ID, args.id],
        [TEMPLATE_DOT_DIR, dotDir],
    ];

    if (toolPrefix) {
        for (const toolName of TOOL_NAMES) {
            replacements.push([toolName, `${toolPrefix}_${toolName}`]);
        }
    }

    rewriteFiles(targetRoot, replacements);

    if (args.initGit) {
        run('git', ['init'], targetRoot);
    }

    if (args.install) {
        run('npm', ['install'], targetRoot);
    }

    console.log(`Created ${args.name} at ${targetRoot}`);
    console.log('');
    console.log('Next steps:');
    console.log(`  cd ${targetRoot}`);
    if (!args.install) console.log('  npm install');
    console.log('  npm run typecheck');
    console.log('  npm run lint');
    console.log('  npm run test:plugin');
}

try {
    main();
} catch (err) {
    console.error(err instanceof Error ? err.message : String(err));
    process.exit(1);
}
