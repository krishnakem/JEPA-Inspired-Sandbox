import { EventEmitter } from 'node:events';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { randomUUID } from 'node:crypto';

export interface AgentSession {
    id: string;
    scratchDir: string;
    outputDir: string;
    runConfig: {
        agentName: string;
        defaultDelayMs: number;
    };
    events: EventEmitter;
    abortSignal: AbortSignal;
}

export interface CreateAgentSessionOptions {
    scratchDir?: string;
    outputDir?: string;
    runConfig?: Partial<AgentSession['runConfig']>;
}

export interface CreateAgentSessionResult {
    session: AgentSession;
    controller: AbortController;
}

export function createAgentSession(opts: CreateAgentSessionOptions = {}): CreateAgentSessionResult {
    const id = randomUUID();
    const base = path.join(os.tmpdir(), `agent-template-${id}`);
    const scratchDir = opts.scratchDir ?? path.join(base, 'scratch');
    const outputDir = opts.outputDir ?? path.join(base, 'output');

    fs.mkdirSync(scratchDir, { recursive: true });
    fs.mkdirSync(outputDir, { recursive: true });

    const controller = new AbortController();
    const session: AgentSession = {
        id,
        scratchDir,
        outputDir,
        runConfig: {
            agentName: opts.runConfig?.agentName ?? 'Template Agent',
            defaultDelayMs: opts.runConfig?.defaultDelayMs ?? 750,
        },
        events: new EventEmitter(),
        abortSignal: controller.signal,
    };

    return { session, controller };
}
