/**
 * JEPA Silicon Sandbox OpenClaw plugin.
 *
 * This file is the boundary between OpenClaw and your agent implementation.
 * Most plugin projects should only need to edit:
 *
 * - Plugin identity in package.json / openclaw.plugin.json / default export
 * - Tool parameters for marketsim_run_market_simulation
 * - The runner called from marketsim_run_market_simulation
 */

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { createAgentSession } from '../core/AgentSession.js';
import {
    JepaSiliconSandboxRunner,
    type MarketSimulationInput,
} from '../main/JepaSiliconSandboxRunner.js';
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

function asRequiredString(params: Record<string, unknown>, key: string): string {
    const value = params[key];
    if (typeof value !== 'string' || !value.trim()) {
        throw new Error(`marketsim_run_market_simulation: ${key} is required.`);
    }
    return value.trim();
}

function asOptionalString(params: Record<string, unknown>, key: string): string | undefined {
    const value = params[key];
    if (typeof value !== 'string') return undefined;
    const trimmed = value.trim();
    return trimmed || undefined;
}

function asRequiredEnum<T extends string>(
    params: Record<string, unknown>,
    key: string,
    allowed: readonly T[]
): T {
    const value = asRequiredString(params, key);
    if (!allowed.includes(value as T)) {
        throw new Error(`marketsim_run_market_simulation: ${key} must be one of: ${allowed.join(', ')}.`);
    }
    return value as T;
}

function asOptionalEnum<T extends string>(
    params: Record<string, unknown>,
    key: string,
    allowed: readonly T[],
    fallback: T
): T {
    const value = asOptionalString(params, key);
    if (!value) return fallback;
    if (!allowed.includes(value as T)) {
        throw new Error(`marketsim_run_market_simulation: ${key} must be one of: ${allowed.join(', ')}.`);
    }
    return value as T;
}

const COMPANY_TYPES = ['startup', 'incumbent', 'platform', 'niche vendor'] as const;
const LEVEL_TO_STYLE = {
    light: 'conservative',
    medium: 'base_case',
    hard: 'aggressive',
} as const;

function parseRunInput(params: Record<string, unknown>): MarketSimulationInput {
    const level = asOptionalEnum(params, 'level', ['light', 'medium', 'hard'] as const, 'medium');
    return {
        currentMarket: asRequiredString(params, 'current_market'),
        companyType: asRequiredEnum(params, 'company_type', COMPANY_TYPES),
        strategicAction: asRequiredString(params, 'strategic_action'),
        simulationStyle: LEVEL_TO_STYLE[level],
        objective: asOptionalString(params, 'objective') ?? 'market_share',
        industry: asOptionalString(params, 'industry') ?? 'AI',
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

    const runMarketSimulation: PluginTool = {
        name: 'marketsim_run_market_simulation',
        description:
            'Create a session and start a fixed 4-round local JEPA-inspired market simulation in the background. Poll marketsim_get_session_status with the returned session_id for progress and the final Market Vision report.',
        parameters: {
            type: 'object',
            properties: {
                current_market: {
                    type: 'string',
                    description: 'Current market description to encode into the numeric market state.',
                },
                company_type: {
                    type: 'string',
                    enum: COMPANY_TYPES,
                    description: 'Company type: startup, incumbent, platform, or niche vendor.',
                },
                strategic_action: {
                    type: 'string',
                    description: 'Strategic action to simulate.',
                },
                objective: {
                    type: 'string',
                    description: 'Company objective for the scenario. Defaults to market_share.',
                },
                industry: {
                    type: 'string',
                    description: 'Industry context for the scenario. Defaults to AI.',
                },
                level: {
                    type: 'string',
                    enum: ['light', 'medium', 'hard'],
                    description: 'Simulation intensity: light, medium, or hard. Defaults to medium.',
                },
            },
            required: ['current_market', 'strategic_action', 'company_type'],
            additionalProperties: false,
        },
        execute: async (_callId, params) => {
            let input: MarketSimulationInput;
            try {
                input = parseRunInput(params);
            } catch (err) {
                return textResult(err instanceof Error ? err.message : String(err), true);
            }

            const { session, controller } = createAgentSession({
                scratchDir,
                outputDir,
                runConfig: {
                    agentName: config.agentName ?? 'JEPA Silicon Sandbox',
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
            const sessionId = entry.sessionId;

            const runController = new AbortController();
            const startedAt = Date.now();
            entry.activeRun = {
                startedAt,
                status: 'running',
                controller: runController,
            };

            const runner = new JepaSiliconSandboxRunner(entry.session);
            void runner.run(input, runController.signal)
                .then((result) => {
                    if (!entry.activeRun) return;
                    entry.activeRun.status = 'completed';
                    entry.activeRun.result = result;
                    log.info('marketsim_run_market_simulation completed', { sessionId, artifactPath: result.artifactPath });
                })
                .catch((err) => {
                    if (!entry.activeRun) return;
                    const aborted = runController.signal.aborted || entry.controller.signal.aborted;
                    entry.activeRun.status = aborted ? 'stopped' : 'failed';
                    entry.activeRun.errorMessage = err instanceof Error ? err.message : String(err);
                    log.warn('marketsim_run_market_simulation ended', {
                        sessionId,
                        status: entry.activeRun.status,
                        error: entry.activeRun.errorMessage,
                    });
                });

            return jsonTextResult({
                status: 'started',
                session_id: sessionId,
                started_at: new Date(startedAt).toISOString(),
                message: 'Market simulation started in the background. Poll marketsim_get_session_status for progress.',
            });
        },
    };

    const getSessionStatus: PluginTool = {
        name: 'marketsim_get_session_status',
        description:
            'Return session lifecycle information, recent events, and the active run result when available.',
        parameters: {
            type: 'object',
            properties: {
                session_id: {
                    type: 'string',
                    description: 'The id returned by marketsim_run_market_simulation.',
                },
            },
            required: ['session_id'],
            additionalProperties: false,
        },
        execute: async (_callId, params) => {
            const sessionId = params.session_id;
            if (typeof sessionId !== 'string' || !sessionId) {
                return textResult('marketsim_get_session_status: session_id is required.', true);
            }
            const entry = sessions.get(sessionId);
            if (!entry) {
                return textResult(`marketsim_get_session_status: session_id ${sessionId} not found.`, true);
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
        name: 'marketsim_stop_run',
        description:
            'Request cancellation of an in-flight marketsim_run_market_simulation call. The runner receives an AbortSignal and should stop cooperatively.',
        parameters: {
            type: 'object',
            properties: {
                session_id: {
                    type: 'string',
                    description: 'The id returned by marketsim_run_market_simulation.',
                },
            },
            required: ['session_id'],
            additionalProperties: false,
        },
        execute: async (_callId, params) => {
            const sessionId = params.session_id;
            if (typeof sessionId !== 'string' || !sessionId) {
                return textResult('marketsim_stop_run: session_id is required.', true);
            }
            const entry = sessions.get(sessionId);
            if (!entry) {
                return textResult(`marketsim_stop_run: session_id ${sessionId} not found.`, true);
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
                message: 'Stop requested. Poll marketsim_get_session_status for the final stopped state.',
            });
        },
    };

    const resetAll: PluginTool = {
        name: 'marketsim_reset_all',
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
                    'marketsim_reset_all dry-run. Call again with { "confirm": true } to delete:\n\n' +
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

            return textResult('marketsim_reset_all complete. Scratch and output directories are empty.');
        },
    };

    const endSession: PluginTool = {
        name: 'marketsim_end_session',
        description:
            'Abort any in-flight run and forget the session_id. Call when the user is done.',
        parameters: {
            type: 'object',
            properties: {
                session_id: {
                    type: 'string',
                    description: 'The id returned by marketsim_run_market_simulation.',
                },
            },
            required: ['session_id'],
            additionalProperties: false,
        },
        execute: async (_callId, params) => {
            const sessionId = params.session_id;
            if (typeof sessionId !== 'string' || !sessionId) {
                return textResult('marketsim_end_session: session_id is required.', true);
            }
            const entry = sessions.get(sessionId);
            if (!entry) {
                return textResult(`marketsim_end_session: session_id ${sessionId} not found.`, true);
            }

            await closeEntry(entry);
            sessions.delete(sessionId);
            return textResult('Session ended.');
        },
    };

    api.registerTool(runMarketSimulation);
    api.registerTool(getSessionStatus);
    api.registerTool(stopRun);
    api.registerTool(resetAll);
    api.registerTool(endSession);

    log.info('JEPA Silicon Sandbox plugin registered', {
        scratchDir,
        outputDir,
        tools: 5,
    });

    return () => {
        for (const entry of sessions.values()) {
            void closeEntry(entry);
        }
        sessions.clear();
    };
}

export default {
    id: 'jepa-silicon-sandbox',
    name: 'JEPA Silicon Sandbox',
    description: 'Host-only local market-vision simulations powered by a JEPA-inspired Python engine with a fixed 4-round horizon.',
    kind: 'capability' as const,
    register,
};
