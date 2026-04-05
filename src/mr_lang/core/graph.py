"""Central graph builder — the runtime engine of mr_lang."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import ToolNode, tools_condition

from mr_lang.core.state import AgentState
from mr_lang.middleware.base import BaseMiddleware


def build_agent_graph(
    model: BaseChatModel,
    tools: list[BaseTool],
    system_prompt: str,
    checkpointer: BaseCheckpointSaver | None = None,
    middleware: list[BaseMiddleware] | None = None,
) -> CompiledGraph:
    """Build a ReAct agent graph from model, tools, and system prompt.

    The graph follows the standard ReAct pattern:
    1. Agent node: model decides to call tools or respond
    2. Tool node: executes tool calls
    3. Loop until model responds without tool calls

    Middleware hooks run around each model invocation:
    - before_model hooks execute first → last before the model call
    - after_model hooks execute first → last after the model responds
    """
    model_with_tools = model.bind_tools(tools) if tools else model
    mw_chain = middleware or []

    async def agent_node(state: AgentState) -> dict:
        # Run before_model hooks in order
        current_state = state
        for mw in mw_chain:
            current_state = await mw.before_model(current_state)

        messages = current_state["messages"]
        sys_msg = SystemMessage(content=system_prompt)
        response = await model_with_tools.ainvoke([sys_msg, *messages])

        # Run after_model hooks in order
        current_response = response
        for mw in mw_chain:
            current_response = await mw.after_model(current_state, current_response)

        return {"messages": [current_response]}

    builder = StateGraph(AgentState)
    builder.add_node("agent", agent_node)

    if tools:
        builder.add_node("tools", ToolNode(tools))
        builder.set_entry_point("agent")
        builder.add_conditional_edges("agent", tools_condition)
        builder.add_edge("tools", "agent")
    else:
        builder.set_entry_point("agent")
        builder.set_finish_point("agent")

    return builder.compile(checkpointer=checkpointer)
