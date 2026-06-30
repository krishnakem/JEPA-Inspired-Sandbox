import fs from 'node:fs/promises';
import path from 'node:path';

import type { AgentSession } from '../core/AgentSession.js';
import { type AgentRunResult, type AgentRunner, sleep, throwIfAborted } from './AgentRunner.js';

export interface ExampleAgentInput {
    topic: string;
    steps: number;
    delayMs: number;
}

/**
 * Replace this class with your real agent.
 *
 * The plugin shell expects only one thing from an agent: a Promise that
 * resolves to an AgentRunResult and respects the AbortSignal.
 */
export class ExampleAgentRunner implements AgentRunner<ExampleAgentInput> {
    constructor(private readonly session: AgentSession) {}

    async run(input: ExampleAgentInput, signal: AbortSignal): Promise<AgentRunResult> {
        const startedAt = Date.now();
        this.session.events.emit('run-started', {
            topic: input.topic,
            steps: input.steps,
        });

        try {
            for (let step = 1; step <= input.steps; step++) {
                throwIfAborted(signal);
                this.session.events.emit('run-phase', {
                    phase: `step-${step}`,
                    step,
                    totalSteps: input.steps,
                });
                this.session.events.emit('run-progress', {
                    message: `Processed template step ${step} of ${input.steps}`,
                    step,
                    totalSteps: input.steps,
                });
                await sleep(input.delayMs, signal);
            }

            const result = await this.writeArtifact(input, startedAt);
            this.session.events.emit('run-complete', {
                artifactPath: result.artifactPath,
                elapsedMs: Date.now() - startedAt,
            });
            return result;
        } catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            this.session.events.emit('run-error', { message });
            throw err;
        }
    }

    private async writeArtifact(
        input: ExampleAgentInput,
        startedAt: number
    ): Promise<AgentRunResult> {
        const runsDir = path.join(this.session.outputDir, 'runs');
        await fs.mkdir(runsDir, { recursive: true });

        const safeTimestamp = new Date(startedAt).toISOString().replace(/[:.]/g, '-');
        const artifactPath = path.join(runsDir, `run-${safeTimestamp}.md`);
        const title = `${this.session.runConfig.agentName}: ${input.topic}`;
        const summary = `Completed ${input.steps} template steps for "${input.topic}".`;

        const markdown = [
            `# ${title}`,
            '',
            summary,
            '',
            `- session: ${this.session.id}`,
            `- started: ${new Date(startedAt).toISOString()}`,
            `- steps: ${input.steps}`,
            '',
            'Replace `ExampleAgentRunner` with your real agent implementation.',
            '',
        ].join('\n');

        await fs.writeFile(artifactPath, markdown, 'utf8');

        return {
            title,
            summary,
            artifactPath,
            data: {
                topic: input.topic,
                steps: input.steps,
                elapsedMs: Date.now() - startedAt,
            },
        };
    }
}
