import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import pluginDefault, {
    register,
    type AgentToolResult,
    type PluginApi,
    type PluginTool,
} from '../src/plugin/index.js';

function fail(msg: string): never {
    console.error(`FAIL: ${msg}`);
    process.exit(1);
}

function assert(cond: unknown, msg: string): asserts cond {
    if (!cond) fail(msg);
}

function textPayload(result: AgentToolResult): string {
    const first = result.content[0];
    assert(first?.type === 'text', 'tool result must contain text');
    return first.text;
}

async function main(): Promise<void> {
    const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'jepa-sandbox-smoke-'));
    const registered: Array<{ tool: PluginTool; opts: { optional?: boolean } | undefined }> = [];

    const api: PluginApi = {
        pluginConfig: {
            scratchDir: path.join(tmpRoot, 'scratch'),
            outputDir: path.join(tmpRoot, 'output'),
            agentName: 'Smoke Silicon Sandbox',
            defaultDelayMs: 1,
        },
        logger: {
            info: () => {},
            warn: () => {},
            error: () => {},
        },
        registerTool: (tool, opts) => {
            registered.push({ tool, opts });
        },
    };

    assert(typeof register === 'function', 'named register export is missing');
    assert(pluginDefault.id === 'jepa-inspired-silicon-sandbox', 'default export id mismatch');

    const teardown = register(api);
    const expectedTools = [
        'marketsim_start_session',
        'marketsim_run_market_simulation',
        'marketsim_get_session_status',
        'marketsim_stop_run',
        'marketsim_reset_all',
        'marketsim_end_session',
    ];
    assert(
        registered.map((r) => r.tool.name).join(',') === expectedTools.join(','),
        `registered tools mismatch: ${registered.map((r) => r.tool.name).join(',')}`
    );

    const tool = (name: string): PluginTool => {
        const found = registered.find((r) => r.tool.name === name)?.tool;
        assert(found, `${name} tool not registered`);
        return found;
    };

    const start = await tool('marketsim_start_session').execute('call-1', {});
    const startJson = JSON.parse(textPayload(start));
    assert(typeof startJson.session_id === 'string', 'marketsim_start_session missing session_id');

    const run = await tool('marketsim_run_market_simulation').execute('call-2', {
        session_id: startJson.session_id,
        current_market: 'AI coding assistants are growing and competitive',
        strategic_action: 'launch a free coding agent',
        company_type: 'startup',
        objective: 'developer_adoption',
        industry: 'AI',
        rounds: 2,
        level: 'hard',
    });
    const runJson = JSON.parse(textPayload(run));
    assert(runJson.status === 'started', 'marketsim_run_market_simulation did not start');

    const runToolParams = tool('marketsim_run_market_simulation').parameters;
    assert(
        Object.keys(runToolParams.properties).sort().join(',') ===
            ['company_type', 'current_market', 'industry', 'level', 'objective', 'rounds', 'session_id', 'strategic_action'].join(','),
        'marketsim_run_market_simulation exposed unexpected parameters'
    );
    assert(
        runToolParams.required?.join(',') === 'session_id,current_market,strategic_action,company_type',
        'marketsim_run_market_simulation required fields mismatch'
    );

    let terminalStatus = '';
    let terminalPayload: any = null;
    for (let i = 0; i < 80; i++) {
        await new Promise((resolve) => setTimeout(resolve, 100));
        const status = await tool('marketsim_get_session_status').execute('call-3', {
            session_id: startJson.session_id,
        });
        const statusJson = JSON.parse(textPayload(status));
        if (['completed', 'failed', 'stopped'].includes(statusJson.run_status)) {
            terminalStatus = statusJson.run_status;
            terminalPayload = statusJson;
            break;
        }
    }

    assert(terminalStatus === 'completed', `expected completed, got ${terminalStatus || 'none'}`);
    assert(
        typeof terminalPayload.result?.artifactPath === 'string' &&
            fs.existsSync(terminalPayload.result.artifactPath),
        'completed run did not write an artifact'
    );
    assert(
        String(terminalPayload.result.artifactPath).endsWith('.md'),
        'completed run did not write a markdown report'
    );

    const end = await tool('marketsim_end_session').execute('call-4', {
        session_id: startJson.session_id,
    });
    assert(textPayload(end) === 'Session ended.', 'marketsim_end_session response mismatch');

    teardown();
    fs.rmSync(tmpRoot, { recursive: true, force: true });
    console.log('plugin smoke test passed');
}

main().catch((err) => {
    fail(err instanceof Error ? err.message : String(err));
});
