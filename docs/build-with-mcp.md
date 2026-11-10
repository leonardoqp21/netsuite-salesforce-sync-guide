# Plan and build the sync from Claude or ChatGPT (Stacksync MCP)

The [Stacksync MCP server](https://www.stacksync.com/mcp) (`https://mcp.stacksync.com/mcp`) lets an assistant plan and create a sync with exactly your permissions. You sign in with OAuth. **No key, token or NetSuite credential goes into the chat.** Setup: [docs.stacksync.com/mcp](https://docs.stacksync.com/mcp).

## Safe order of work

1. **Read-only first.** Sign in with "Make changes" cleared.
2. **Look at what exists.** `syncs_list`, `connections_list`. Extend an existing sync between the same two apps. Never create a second.
3. **Read the real tables and fields** with `connections_tables`. Never guess a name. Pay attention to the NetSuite `itemList` field on sales orders.
4. **Plan as a table**: table in Salesforce, table in NetSuite, direction per pair, fields, match key, load order.
5. **You approve the plan.** Nothing is created yet.
6. **Create it saved paused**, check the mapping, then switch it on, one pair at a time.

## What the assistant should ask you

- Where do people edit each table: Salesforce, NetSuite or both?
- Do both systems already hold these customers?
- Should deletes reach the other side?
- Who calculates price and tax on an order?
- How should order lines be built (workflow or database view)?
- How fresh must the data be?

## What it cannot do

- Merge your existing duplicates.
- Build the product-to-item mapping for you. That is your data.
- Decide for you which resolution (retry, revert, ignore) to use for a group of issues.
- Configure some settings that live only in the web app, such as per-field direction and associations.

If a tool says you have no access, a workspace owner changes your role.

## Prompts

See [`prompts/prompts.md`](../prompts/prompts.md).

## Product page

[NetSuite and Salesforce integration](https://www.stacksync.com/integrations/netsuite-and-salesforce) on stacksync.com. More on [two-way sync](https://www.stacksync.com/two-way-sync).
