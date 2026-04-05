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


def build_agent_graph(
    model: BaseChatModel,
    tools: list[BaseTool],
    system_prompt: str,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledGraph:
    """Build a ReAct agent graph from model, tools, and system prompt.

    The graph follows the standard ReAct pattern:
    1. Agent node: model decides to call tools or respond
    2. Tool node: executes tool calls
    3. Loop until model responds without tool calls
    """
    model_with_tools = model.bind_tools(tools) if tools else model

    def agent_node(state: AgentState) -> dict:
        messages = state["messages"]
        sys_msg = SystemMessage(content=system_prompt)
        response = model_with_tools.invoke([sys_msg, *messages])
        return {"messages": [response]}

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
