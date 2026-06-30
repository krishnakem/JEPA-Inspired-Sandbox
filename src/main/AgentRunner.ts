export interface AgentRunResult {
    title: string;
    summary: string;
    artifactPath: string;
    data?: Record<string, unknown>;
}

export interface AgentRunner<TInput = unknown> {
    run(input: TInput, signal: AbortSignal): Promise<AgentRunResult>;
}

export function throwIfAborted(signal: AbortSignal): void {
    if (signal.aborted) {
        throw new Error('RUN_ABORTED');
    }
}

export function sleep(ms: number, signal: AbortSignal): Promise<void> {
    return new Promise((resolve, reject) => {
        if (signal.aborted) {
            reject(new Error('RUN_ABORTED'));
            return;
        }

        const timer = setTimeout(resolve, ms);
        const onAbort = () => {
            clearTimeout(timer);
            reject(new Error('RUN_ABORTED'));
        };
        signal.addEventListener('abort', onAbort, { once: true });
    });
}
