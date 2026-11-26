"""
Copyright 2026, Zep Software, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import graphiti_mcp_server as server


@pytest.mark.asyncio
async def test_every_tool_has_packaging_metadata():
    tools = await server.mcp.list_tools()

    assert tools
    for tool in tools:
        assert tool.title
        assert tool.title != tool.name
        assert tool.description
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is not None
        assert tool.annotations.destructive_hint is not None
        assert tool.annotations.idempotent_hint is not None
        assert tool.annotations.open_world_hint is not None
        assert not (tool.annotations.read_only_hint and tool.annotations.destructive_hint)
        for parameter in tool.input_schema.get('properties', {}).values():
            assert parameter.get('description')


@pytest.mark.asyncio
async def test_read_only_mode_registers_only_read_tools():
    script = """
import asyncio
import graphiti_mcp_server as server

async def main():
    tools = await server.mcp.list_tools()
    print(','.join(sorted(tool.name for tool in tools)))

asyncio.run(main())
"""
    env = os.environ | {'MCP_SERVER_GRAPHITI_READ_ONLY': 'true'}
    result = subprocess.run(
        [sys.executable, '-c', script],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert set(result.stdout.strip().split(',')) == {
        'get_entity_edge',
        'get_episode_entities',
        'get_episodes',
        'get_status',
        'search_memory_facts',
        'search_nodes',
    }


@pytest.mark.asyncio
async def test_stdio_discovery_does_not_require_database_or_api_keys():
    env = {
        key: value
        for key, value in os.environ.items()
        if key
        not in {
            'OPENAI_API_KEY',
            'NEO4J_PASSWORD',
            'FALKORDB_PASSWORD',
        }
    }
    env['GRAPHITI_TELEMETRY_ENABLED'] = 'false'
    params = StdioServerParameters(
        command=sys.executable,
        args=['-m', 'mcp_server_graphiti', '--transport', 'stdio'],
        env=env,
    )

    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()

    assert {tool.name for tool in tools.tools} >= {
        'get_status',
        'search_nodes',
        'search_memory_facts',
    }


def test_destroy_graph_is_rejected_in_read_only_mode():
    env = os.environ | {'MCP_SERVER_GRAPHITI_READ_ONLY': 'true'}
    project = Path(__file__).parents[1]
    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'mcp_server_graphiti',
            '--destroy-graph',
            '--transport',
            'stdio',
        ],
        cwd=project,
        env=env,
        text=True,
        capture_output=True,
        timeout=15,
    )

    assert result.returncode != 0
    assert '--destroy-graph cannot be used in read-only mode' in result.stderr


@pytest.mark.asyncio
async def test_manifest_matches_tools_and_documents_environment_variables():
    project = Path(__file__).parents[2]
    manifest = json.loads((project / 'server.json').read_text())
    extension = manifest['_meta']['io.modelcontextprotocol.registry/publisher-provided'][
        'cz.vitexsoftware.mcp'
    ]
    registered = {tool.name for tool in await server.mcp.list_tools()}
    manifested = {tool['name'] for tool in extension['tools']}
    readme = (project / 'mcp_server' / 'README.md').read_text()

    assert manifested == registered
    assert extension['uuid'] == '7b85f0ea-47dc-41ad-a112-588915b75fab'
    for variable in manifest['packages'][0]['environmentVariables']:
        assert variable['name'] in readme
