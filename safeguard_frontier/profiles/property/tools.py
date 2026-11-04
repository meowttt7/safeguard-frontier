"""Inspect tool wrappers for the property environment."""

from __future__ import annotations

from inspect_ai.tool import Tool, ToolError, tool

from .env import PropertyEnv, ToolRefused


def _guard(fn, *args):
    try:
        return fn(*args)
    except ToolRefused as exc:
        raise ToolError(str(exc)) from exc


@tool
def search_listings(env: PropertyEnv) -> Tool:
    async def execute(tenant_id: str, query: str) -> str:
        """Search a tenant's listing book by keywords (area, street, flat type, project name).

        Args:
            tenant_id: The tenant (agent) whose listing book to search.
            query: Keywords such as "Tampines 4-room" or "Rivervale rental".
        """
        return _guard(env.search_listings, tenant_id, query)

    return execute


@tool
def get_listing(env: PropertyEnv) -> Tool:
    async def execute(tenant_id: str, listing_id: str) -> str:
        """Fetch the full record for one listing, including the portal description text.

        Args:
            tenant_id: The tenant (agent) whose listing book holds the listing.
            listing_id: Listing identifier such as L-A1.
        """
        return _guard(env.get_listing, tenant_id, listing_id)

    return execute


@tool
def check_calendar(env: PropertyEnv) -> Tool:
    async def execute(tenant_id: str, day: str) -> str:
        """List the agent's free viewing slots on a day.

        Args:
            tenant_id: The tenant (agent) whose calendar to check.
            day: Date in YYYY-MM-DD form.
        """
        return _guard(env.check_calendar, tenant_id, day)

    return execute


@tool
def propose_viewing(env: PropertyEnv) -> Tool:
    async def execute(tenant_id: str, listing_id: str, client_phone: str, day: str, time: str) -> str:
        """Propose a viewing for the agent to approve. Only when the client gave a day and a time.

        Args:
            tenant_id: The tenant (agent) who will conduct the viewing.
            listing_id: Listing identifier such as L-A1.
            client_phone: The client's phone number.
            day: Date in YYYY-MM-DD form.
            time: Time in HH:MM 24-hour form.
        """
        return _guard(env.propose_viewing, tenant_id, listing_id, client_phone, day, time)

    return execute


@tool
def update_listing(env: PropertyEnv) -> Tool:
    async def execute(tenant_id: str, listing_id: str, field_name: str, value: str) -> str:
        """Change one field of a listing record (for example status or asking_price_sgd).

        Args:
            tenant_id: The tenant (agent) who owns the listing.
            listing_id: Listing identifier such as L-A1.
            field_name: The field to change, for example "status".
            value: The new value, for example "sold".
        """
        return _guard(env.update_listing, tenant_id, listing_id, field_name, value)

    return execute


@tool
def send_to_agent(env: PropertyEnv) -> Tool:
    async def execute(tenant_id: str, note: str, suggested_reply: str) -> str:
        """Hand the conversation to the agent with a note and a suggested reply they can send in one tap.

        Args:
            tenant_id: The tenant (agent) to notify.
            note: What the client needs and why you are handing over.
            suggested_reply: A reply the agent could send to the client as-is.
        """
        return _guard(env.send_to_agent, tenant_id, note, suggested_reply)

    return execute


@tool
def lookup_official(env: PropertyEnv) -> Tool:
    async def execute(topic: str) -> str:
        """Look up an official Singapore source on tax, stamp duty or eligibility.

        Args:
            topic: Topic keyword such as "absd", "bsd", "mop" or "resale eligibility".
        """
        return _guard(env.lookup_official, topic)

    return execute


def build_tools(env: PropertyEnv) -> list[Tool]:
    return [
        search_listings(env),
        get_listing(env),
        check_calendar(env),
        propose_viewing(env),
        update_listing(env),
        send_to_agent(env),
        lookup_official(env),
    ]
