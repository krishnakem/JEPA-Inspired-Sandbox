/**
 * Session-side bookkeeping for the plugin layer.
 *
 * AgentSession intentionally stays small and host-neutral. The registry keeps
 * OpenClaw-facing concerns nearby: recent event buffering, active-run status,
 * and per-session abort handles.
 */

import type { AgentRunResult } from '../main/AgentRunner.js';
import type { AgentSession } from '../core/AgentSession.js';

export interface BufferedEvent {
    event: string;
    payload: unknown;
    ts: number;
}

export interface ActiveRun {
    startedAt: number;
    status: 'running' | 'completed' | 'failed' | 'stopped';
    controller: AbortController;
    result?: AgentRunResult;
    errorMessage?: string;
}

export interface SessionEntry {
    sessionId: string;
    session: AgentSession;
    controller: AbortController;
    events: BufferedEvent[];
    lastPhase: string | null;
    createdAt: number;
    activeRun?: ActiveRun;
}

const EVENT_BUFFER_SIZE = 50;

export function createRegistry(): Map<string, SessionEntry> {
    return new Map<string, SessionEntry>();
}

export function attachEventBuffer(entry: SessionEntry): void {
    const names = [
        'run-started',
        'run-phase',
        'run-progress',
        'run-stopping',
        'run-complete',
        'run-error',
    ] as const;

    for (const name of names) {
        entry.session.events.on(name, (payload?: unknown) => {
            entry.events.push({ event: name, payload: payload ?? null, ts: Date.now() });
            if (entry.events.length > EVENT_BUFFER_SIZE) {
                entry.events.shift();
            }

            if (name === 'run-phase' && typeof payload === 'object' && payload !== null) {
                const phase = (payload as { phase?: unknown }).phase;
                if (typeof phase === 'string') entry.lastPhase = phase;
            }
            if (name === 'run-started') entry.lastPhase = 'starting';
            if (name === 'run-complete') entry.lastPhase = 'complete';
            if (name === 'run-error') entry.lastPhase = 'error';
        });
    }
}
