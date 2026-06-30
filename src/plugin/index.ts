/**
 * JEPA-Inspired Silicon Sandbox OpenClaw plugin.
 *
 * This file is the boundary between OpenClaw and your agent implementation.
 * Most plugin projects should only need to edit:
 *
 * - Plugin identity in package.json / openclaw.plugin.json / default export
 * - Tool parameters for run_market_simulation
 * - The runner called from run_market_simulation
 */

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { createAgentSession } from '../core/AgentSession.js';
import {
    JepaInspiredSiliconSandboxRunner,
    type MarketSimulationInput,
} from '../main/JepaInspiredSiliconSandboxRunner.js';
import { attachEventBuffer, createRegistry, type SessionEntry } from './session-registry.js';

export interface AgentToolResult {
    content: Array<{ type: 'text'; text: string }>;
    isError?: boolean;
}

export interface PluginTool {
    name: string;
    description: string;
    parameters: {
        type: 'object';
        properties: Record<string, unknown>;
        required?: string[];
        additionalProperties?: boolean;
    };
    execute: (callId: string, params: Record<string, unknown>) => Promise<AgentToolResult>;
}

export interface PluginApi {
    pluginConfig: PluginConfig;
    logger?: {
        info: (msg: string, ...args: unknown[]) => void;
        warn: (msg: string, ...args: unknown[]) => void;
        error: (msg: string, ...args: unknown[]) => void;
    };
    registerTool: (tool: PluginTool, opts?: { optional?: boolean }) => void;
}

export interface PluginConfig {
    scratchDir?: string;
    outputDir?: string;
    agentName?: string;
    defaultDelayMs?: number;
}

function expandTilde(p: string): string {
    if (p === '~') return os.homedir();
    if (p.startsWith('~/')) return path.join(os.homedir(), p.slice(2));
    return p;
}

function textResult(text: string, isError = false): AgentToolResult {
    const result: AgentToolResult = { content: [{ type: 'text', text }] };
    if (isError) result.isError = true;
    return result;
}

function jsonTextResult(payload: unknown, isError = false): AgentToolResult {
    return textResult(JSON.stringify(payload, null, 2), isError);
}

function resolvePaths(config: PluginConfig): { scratchDir: string; outputDir: string } {
    const scratchDir = expandTilde(
        config.scratchDir ?? path.join(os.homedir(), '.jepa-silicon-sandbox', 'scratch')
    );
    const outputDir = expandTilde(
        config.outputDir ?? path.join(os.homedir(), '.jepa-silicon-sandbox', 'output')
    );
    return { scratchDir, outputDir };
}

function asPositiveInteger(value: unknown, fallback: number, max: number): number {
    if (typeof value !== 'number' || !Number.isFinite(value)) return fallback;
    return Math.max(1, Math.min(Math.floor(value), max));
}

function asRequiredString(params: Record<string, unknown>, key: string): string {
    const value = params[key];
    if (typeof value !== 'string' || !value.trim()) {
        throw new Error(`run_market_simulation: ${key} is required.`);
    }
    return value.trim();
}

function asOptionalString(params: Record<string, unknown>, key: string): string | undefined {
    const value = params[key];
    if (typeof value !== 'string') return undefined;
    const trimmed = value.trim();
    return trimmed || undefined;
}

function asStringList(params: Record<string, unknown>, key: string): string[] | undefined {
    const value = params[key];
    if (typeof value === 'string') {
        const items = value.split(',').map((item) => item.trim()).filter(Boolean);
        return items.length ? items : undefined;
    }
    if (Array.isArray(value)) {
        const items = value
            .filter((item): item is string => typeof item === 'string')
            .map((item) => item.trim())
            .filter(Boolean);
        return items.length ? items : undefined;
    }
    return undefined;
}

function parseRunInput(params: Record<string, unknown>): MarketSimulationInput {
    const companyType = asOptionalString(params, 'company_type');
    const companyProfile = asOptionalString(params, 'company_profile');
    return {
        currentMarket: asRequiredString(params, 'current_market'),
        companyType,
        companyProfile,
        strategicAction: asRequiredString(params, 'strategic_action'),
        simulationRounds: asPositiveInteger(params.rounds ?? params.simulation_rounds, 4, 12),
        preset: asOptionalString(params, 'preset'),
        simulationStyle: asOptionalString(params, 'simulation_style'),
        actors: asStringList(params, 'actors'),
        marketDimensions: asStringList(params, 'market_dimensions'),
        actionDimensions: asStringList(params, 'action_dimensions'),
        shockEvents: asStringList(params, 'shock_events'),
        objective: asOptionalString(params, 'objective'),
        reportFormat: asOptionalString(params, 'report_format'),
    };
}

async function closeEntry(entry: SessionEntry): Promise<void> {
    try {
        entry.controller.abort();
    } catch {
        /* already aborted */
    }
    try {
        entry.activeRun?.controller.abort();
    } catch {
        /* already aborted */
    }
}

export function register(api: PluginApi): () => void {
    const config = api.pluginConfig ?? {};
    const { scratchDir, outputDir } = resolvePaths(config);
    fs.mkdirSync(scratchDir, { recursive: true });
    fs.mkdirSync(outputDir, { recursive: true });

    const sessions = createRegistry();
    const log = api.logger ?? {
        info: (...a: unknown[]) => console.log('[jepa-silicon-sandbox]', ...a),
        warn: (...a: unknown[]) => console.warn('[jepa-silicon-sandbox]', ...a),
        error: (...a: unknown[]) => console.error('[jepa-silicon-sandbox]', ...a),
    };

    const startSession: PluginTool = {
        name: 'start_session',
        description:
            'Create a new market simulation session. Always call this before run_market_simulation. Returns a session_id used by every other tool.',
        parameters: {
            type: 'object',
            properties: {},
            additionalProperties: false,
        },
        execute: async () => {
            const { session, controller } = createAgentSession({
                scratchDir,
                outputDir,
                runConfig: {
                    agentName: config.agentName ?? 'JEPA-Inspired Silicon Sandbox',
                    defaultDelayMs: config.defaultDelayMs ?? 750,
                },
            });

            const entry: SessionEntry = {
                sessionId: session.id,
                session,
                controller,
                events: [],
                lastPhase: null,
                createdAt: Date.now(),
            };
            attachEventBuffer(entry);
            sessions.set(entry.sessionId, entry);

            log.info('start_session', { sessionId: entry.sessionId });
            return jsonTextResult({
                session_id: entry.sessionId,
                message: 'Session started. Call run_market_simulation with this session_id.',
            });
        },
    };

    const runMarketSimulation: PluginTool = {
        name: 'run_market_simulation',
        description:
            'Start a local JEPA-inspired market simulation in the background. Poll get_session_status for progress and the final Market Vision report.',
        parameters: {
            type: 'object',
            properties: {
                session_id: {
                    type: 'string',
                    description: 'The id returned by start_session.',
                },
                current_market: {
                    type: 'string',
                    description: 'Current market description to encode into the numeric market state.',
                },
                company_type: {
                    type: 'string',
                    description: 'Company type or profile, such as startup, incumbent, platform, or niche vendor.',
                },
                company_profile: {
                    type: 'string',
                    description: 'Alias for company_type, useful for richer company profile text.',
                },
                strategic_action: {
                    type: 'string',
                    description: 'Strategic action to simulate.',
                },
                simulation_rounds: {
                    type: 'number',
                    description: 'Number of simulation rounds. Defaults to 4, max 12.',
                },
                rounds: {
                    type: 'number',
                    description: 'Alias for simulation_rounds.',
                },
                preset: {
                    type: 'string',
                    description: 'Built-in preset, such as ai_startup, saas_enterprise, consumer_tech, retail, manufacturing, or fintech.',
                },
                simulation_style: {
                    type: 'string',
                    description: 'Simulation style: conservative, base_case, aggressive, chaotic, winner_take_all, regulated, or capital_constrained.',
                },
                actors: {
                    oneOf: [
                        { type: 'string' },
                        { type: 'array', items: { type: 'string' } },
                    ],
                    description: 'Comma-separated string or array of actor roles.',
                },
                market_dimensions: {
                    oneOf: [
                        { type: 'string' },
                        { type: 'array', items: { type: 'string' } },
                    ],
                    description: 'Comma-separated string or array of market dimension names.',
                },
                action_dimensions: {
                    oneOf: [
                        { type: 'string' },
                        { type: 'array', items: { type: 'string' } },
                    ],
                    description: 'Comma-separated string or array of action dimension names.',
                },
                shock_events: {
                    oneOf: [
                        { type: 'string' },
                        { type: 'array', items: { type: 'string' } },
                    ],
                    description: 'Comma-separated string or array of shock events. Use name@round for explicit timing.',
                },
                objective: {
                    type: 'string',
                    description: 'Company objective for the scenario, such as developer_adoption.',
                },
                report_format: {
                    type: 'string',
                    description: 'Narrative format: strategy_memo, founder_memo, investor_memo, board_update, risk_report, or product_brief.',
                },
            },
            required: ['session_id', 'current_market', 'strategic_action'],
            additionalProperties: false,
        },
        execute: async (_callId, params) => {
            const sessionId = params.session_id;
            if (typeof sessionId !== 'string' || !sessionId) {
                return textResult('run_market_simulation: session_id is required.', true);
            }
            const entry = sessions.get(sessionId);
            if (!entry) {
                return textResult(`run_market_simulation: session_id ${sessionId} not found.`, true);
            }
            if (entry.activeRun?.status === 'running') {
                return jsonTextResult({
                    status: 'already_running',
                    session_id: sessionId,
                    started_at: new Date(entry.activeRun.startedAt).toISOString(),
                });
            }

            let input: MarketSimulationInput;
            try {
                input = parseRunInput(params);
            } catch (err) {
                return textResult(err instanceof Error ? err.message : String(err), true);
            }
            const runController = new AbortController();
            const startedAt = Date.now();
            entry.activeRun = {
                startedAt,
                status: 'running',
                controller: runController,
            };

            const runner = new JepaInspiredSiliconSandboxRunner(entry.session);
            void runner.run(input, runController.signal)
                .then((result) => {
                    if (!entry.activeRun) return;
                    entry.activeRun.status = 'completed';
                    entry.activeRun.result = result;
                    log.info('run_market_simulation completed', { sessionId, artifactPath: result.artifactPath });
                })
                .catch((err) => {
                    if (!entry.activeRun) return;
                    const aborted = runController.signal.aborted || entry.controller.signal.aborted;
                    entry.activeRun.status = aborted ? 'stopped' : 'failed';
                    entry.activeRun.errorMessage = err instanceof Error ? err.message : String(err);
                    log.warn('run_market_simulation ended', {
                        sessionId,
                        status: entry.activeRun.status,
                        error: entry.activeRun.errorMessage,
                    });
                });

            return jsonTextResult({
                status: 'started',
                session_id: sessionId,
                started_at: new Date(startedAt).toISOString(),
                message: 'Market simulation started in the background. Poll get_session_status for progress.',
            });
        },
    };

    const getSessionStatus: PluginTool = {
        name: 'get_session_status',
        description:
            'Return session lifecycle information, recent events, and the active run result when available.',
        parameters: {
            type: 'object',
            properties: {
                session_id: {
                    type: 'string',
                    description: 'The id returned by start_session.',
                },
            },
            required: ['session_id'],
            additionalProperties: false,
        },
        execute: async (_callId, params) => {
            const sessionId = params.session_id;
            if (typeof sessionId !== 'string' || !sessionId) {
                return textResult('get_session_status: session_id is required.', true);
            }
            const entry = sessions.get(sessionId);
            if (!entry) {
                return textResult(`get_session_status: session_id ${sessionId} not found.`, true);
            }

            const activeRun = entry.activeRun;
            return jsonTextResult({
                session_id: entry.sessionId,
                created_at: new Date(entry.createdAt).toISOString(),
                last_phase: entry.lastPhase,
                run_status: activeRun?.status ?? 'idle',
                run_started_at: activeRun ? new Date(activeRun.startedAt).toISOString() : null,
                run_elapsed_ms: activeRun && activeRun.status === 'running'
                    ? Date.now() - activeRun.startedAt
                    : null,
                result: activeRun?.result ?? null,
                error: activeRun?.errorMessage ?? null,
                events: entry.events,
            });
        },
    };

    const stopRun: PluginTool = {
        name: 'stop_run',
        description:
            'Request cancellation of an in-flight run_market_simulation call. The runner receives an AbortSignal and should stop cooperatively.',
        parameters: {
            type: 'object',
            properties: {
                session_id: {
                    type: 'string',
                    description: 'The id returned by start_session.',
                },
            },
            required: ['session_id'],
            additionalProperties: false,
        },
        execute: async (_callId, params) => {
            const sessionId = params.session_id;
            if (typeof sessionId !== 'string' || !sessionId) {
                return textResult('stop_run: session_id is required.', true);
            }
            const entry = sessions.get(sessionId);
            if (!entry) {
                return textResult(`stop_run: session_id ${sessionId} not found.`, true);
            }
            if (!entry.activeRun || entry.activeRun.status !== 'running') {
                return jsonTextResult({
                    status: 'idle',
                    session_id: sessionId,
                    message: 'No active run to stop.',
                });
            }

            entry.activeRun.controller.abort();
            entry.session.events.emit('run-stopping', { reason: 'user-stop' });
            return jsonTextResult({
                status: 'stop_requested',
                session_id: sessionId,
                message: 'Stop requested. Poll get_session_status for the final stopped state.',
            });
        },
    };

    const resetAll: PluginTool = {
        name: 'reset_all',
        description:
            'Factory reset for this plugin. Aborts sessions and deletes scratch/output directories. Call without confirm first for a dry-run preview.',
        parameters: {
            type: 'object',
            properties: {
                confirm: {
                    type: 'boolean',
                    description: 'Must be true to actually delete data.',
                },
            },
            additionalProperties: false,
        },
        execute: async (_callId, params) => {
            const targets = [
                { label: 'scratch dir', path: scratchDir },
                { label: 'output dir', path: outputDir },
            ];

            if (params.confirm !== true) {
                return textResult(
                    'reset_all dry-run. Call again with { "confirm": true } to delete:\n\n' +
                    targets.map((t) => `- ${t.label}: ${t.path}`).join('\n') +
                    `\n\nActive sessions that will be aborted: ${sessions.size}`
                );
            }

            for (const entry of sessions.values()) {
                await closeEntry(entry);
            }
            sessions.clear();

            for (const target of targets) {
                fs.rmSync(target.path, { recursive: true, force: true });
                fs.mkdirSync(target.path, { recursive: true });
            }

            return textResult('reset_all complete. Scratch and output directories are empty.');
        },
    };

    const endSession: PluginTool = {
        name: 'end_session',
        description:
            'Abort any in-flight run and forget the session_id. Call when the user is done.',
        parameters: {
            type: 'object',
            properties: {
                session_id: {
                    type: 'string',
                    description: 'The id returned by start_session.',
                },
            },
            required: ['session_id'],
            additionalProperties: false,
        },
        execute: async (_callId, params) => {
            const sessionId = params.session_id;
            if (typeof sessionId !== 'string' || !sessionId) {
                return textResult('end_session: session_id is required.', true);
            }
            const entry = sessions.get(sessionId);
            if (!entry) {
                return textResult(`end_session: session_id ${sessionId} not found.`, true);
            }

            await closeEntry(entry);
            sessions.delete(sessionId);
            return textResult('Session ended.');
        },
    };

    api.registerTool(startSession);
    api.registerTool(runMarketSimulation);
    api.registerTool(getSessionStatus);
    api.registerTool(stopRun);
    api.registerTool(resetAll);
    api.registerTool(endSession);

    log.info('JEPA-Inspired Silicon Sandbox plugin registered', {
        scratchDir,
        outputDir,
        tools: 6,
    });

    return () => {
        for (const entry of sessions.values()) {
            void closeEntry(entry);
        }
        sessions.clear();
    };
}

export default {
    id: 'jepa-inspired-silicon-sandbox',
    name: 'JEPA-Inspired Silicon Sandbox',
    description: 'Local market-vision simulations powered by a JEPA-inspired Python engine.',
    kind: 'capability' as const,
    register,
};
