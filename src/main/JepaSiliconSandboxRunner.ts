import { spawn } from 'node:child_process';
import fs from 'node:fs';
import fsp from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import type { AgentSession } from '../core/AgentSession.js';
import { type AgentRunResult, type AgentRunner, throwIfAborted } from './AgentRunner.js';

export interface MarketSimulationInput {
    currentMarket: string;
    companyType: string;
    strategicAction: string;
    simulationStyle?: string;
    objective?: string;
    industry?: string;
}

interface ProcessResult {
    stdout: string;
    stderr: string;
    reportPath: string | null;
}

function resolveRepoRoot(): string {
    let current = path.dirname(fileURLToPath(import.meta.url));
    while (true) {
        if (fs.existsSync(path.join(current, 'agent', 'simulation.py'))) {
            return current;
        }
        const parent = path.dirname(current);
        if (parent === current) {
            throw new Error('Could not locate repository root containing agent/simulation.py.');
        }
        current = parent;
    }
}

export class JepaSiliconSandboxRunner implements AgentRunner<MarketSimulationInput> {
    private readonly repoRoot = resolveRepoRoot();

    constructor(private readonly session: AgentSession) {}

    async run(input: MarketSimulationInput, signal: AbortSignal): Promise<AgentRunResult> {
        const startedAt = Date.now();
        this.session.events.emit('run-started', {
            current_market: input.currentMarket,
            company_type: input.companyType,
            strategic_action: input.strategicAction,
            simulation_style: input.simulationStyle ?? null,
        });

        try {
            throwIfAborted(signal);
            this.session.events.emit('run-phase', { phase: 'python-simulation' });

            const reportsDir = path.join(this.session.outputDir, 'market-vision');
            await fsp.mkdir(reportsDir, { recursive: true });
            const processResult = await this.runPythonSimulation(input, reportsDir, signal);
            const reportPath = processResult.reportPath ?? await this.findNewestReport(reportsDir);
            if (!reportPath) {
                throw new Error('Python simulation completed but no Market Vision report was written.');
            }

            const reportText = await fsp.readFile(reportPath, 'utf8');
            const figures = await this.findDiagnosticFigures();
            const summary = this.summaryFromStdout(processResult.stdout);

            const result: AgentRunResult = {
                title: `${this.session.runConfig.agentName}: Market Vision`,
                summary,
                artifactPath: reportPath,
                data: {
                    reportPath,
                    figures,
                    stdout: processResult.stdout,
                    stderr: processResult.stderr,
                    preview: reportText.slice(0, 1200),
                    elapsedMs: Date.now() - startedAt,
                },
            };

            this.session.events.emit('run-complete', {
                artifactPath: result.artifactPath,
                figures,
                elapsedMs: Date.now() - startedAt,
            });
            return result;
        } catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            this.session.events.emit('run-error', { message });
            throw err;
        }
    }

    private async runPythonSimulation(
        input: MarketSimulationInput,
        reportsDir: string,
        signal: AbortSignal
    ): Promise<ProcessResult> {
        const python = process.env.PYTHON ?? 'python3';
        const configPath = await this.writeGeneratedConfig(input, reportsDir);
        const args = [
            '-m',
            'agent.simulation',
            '--current-market',
            input.currentMarket,
            '--strategic-action',
            input.strategicAction,
            '--format',
            'markdown',
            '--json-progress',
            '--output-dir',
            reportsDir,
        ];
        if (input.companyType) {
            args.push('--company-type', input.companyType);
        }
        if (configPath) {
            args.push('--config', configPath);
        }
        return new Promise((resolve, reject) => {
            const child = spawn(python, args, {
                cwd: this.repoRoot,
                env: {
                    ...process.env,
                    PYTHONUNBUFFERED: '1',
                    PYTHONPATH: [
                        this.repoRoot,
                        process.env.PYTHONPATH,
                    ].filter(Boolean).join(path.delimiter),
                },
                stdio: ['ignore', 'pipe', 'pipe'],
            });

            let stdout = '';
            let stderr = '';
            let reportPath: string | null = null;

            const onAbort = () => {
                child.kill('SIGTERM');
                reject(new Error('RUN_ABORTED'));
            };
            if (signal.aborted) {
                onAbort();
                return;
            }
            signal.addEventListener('abort', onAbort, { once: true });

            const emitLine = (stream: 'stdout' | 'stderr', line: string) => {
                if (!line.trim()) return;
                this.session.events.emit('run-progress', {
                    stream,
                    message: line,
                    payload: this.parseProgressLine(line),
                });
                const match = line.match(/Wrote markdown Market Vision report to (.+)$/);
                if (match?.[1]) reportPath = match[1].trim();
            };

            child.stdout.setEncoding('utf8');
            child.stdout.on('data', (chunk: string) => {
                stdout += chunk;
                for (const line of chunk.split(/\r?\n/)) emitLine('stdout', line);
            });
            child.stderr.setEncoding('utf8');
            child.stderr.on('data', (chunk: string) => {
                stderr += chunk;
                for (const line of chunk.split(/\r?\n/)) emitLine('stderr', line);
            });
            child.on('error', (err) => {
                signal.removeEventListener('abort', onAbort);
                reject(err);
            });
            child.on('close', (code) => {
                signal.removeEventListener('abort', onAbort);
                if (signal.aborted) {
                    reject(new Error('RUN_ABORTED'));
                    return;
                }
                if (code !== 0) {
                    reject(new Error(`Python simulator exited with code ${code}: ${stderr || stdout}`));
                    return;
                }
                resolve({ stdout, stderr, reportPath });
            });
        });
    }

    private async writeGeneratedConfig(
        input: MarketSimulationInput,
        reportsDir: string
    ): Promise<string | null> {
        const config: Record<string, unknown> = {};
        if (input.simulationStyle) config.simulation_style = input.simulationStyle;
        if (input.objective) config.objective = input.objective;
        if (input.industry) config.industry = input.industry;

        if (Object.keys(config).length === 0) return null;

        const configPath = path.join(reportsDir, `generated-simulation-config-${Date.now()}.json`);
        await fsp.writeFile(configPath, JSON.stringify(config, null, 2), 'utf8');
        return configPath;
    }

    private async findNewestReport(reportsDir: string): Promise<string | null> {
        const entries = await fsp.readdir(reportsDir).catch(() => []);
        const reports = entries
            .filter((entry) => entry.endsWith('.md') || entry.endsWith('.json'))
            .map((entry) => path.join(reportsDir, entry))
            .filter((entry) => fs.existsSync(entry))
            .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
        return reports[0] ?? null;
    }

    private async findDiagnosticFigures(): Promise<string[]> {
        const plotsDir = path.join(this.repoRoot, 'agent', 'artifacts', 'plots');
        const names = ['latent_trajectory.png', 'effective_rank.png', 'collapse_comparison.png'];
        return names
            .map((name) => path.join(plotsDir, name))
            .filter((candidate) => fs.existsSync(candidate));
    }

    private parseProgressLine(line: string): unknown {
        try {
            return JSON.parse(line);
        } catch {
            return null;
        }
    }

    private summaryFromStdout(stdout: string): string {
        for (const line of stdout.split(/\r?\n/)) {
            const payload = this.parseProgressLine(line);
            if (
                typeof payload === 'object' &&
                payload !== null &&
                (payload as { type?: unknown }).type === 'final' &&
                typeof (payload as { final_market_vision?: unknown }).final_market_vision === 'string'
            ) {
                return (payload as { final_market_vision: string }).final_market_vision;
            }
        }
        const firstLine = stdout
            .split(/\r?\n/)
            .find((line) => line.trim() && !line.trim().startsWith('{'));
        return firstLine?.trim() ?? 'Market Vision simulation completed.';
    }
}
