# Prompts for Claude or ChatGPT with the Stacksync MCP server

Connect first (`https://mcp.stacksync.com/mcp`, OAuth, no key in the chat). For planning, sign in with "Make changes" cleared. Use **sandboxes**.

## 1. Look before you build

```text
List my Stacksync workspaces and tell me which one you will use. Then list my connections and any existing syncs involving NetSuite or Salesforce. Do not create or change anything.
```

## 2. Plan the pairs

```text
Plan a sync between my Salesforce and NetSuite connections. Read the real tables and fields with connections_tables. Show me a table with: the Salesforce table, the NetSuite table, the direction for each pair, the match key and the load order. Start with items, customers and orders. Ask me, before proposing directions, where people edit each table. Do not create anything until I confirm.
```

## 3. Look at order lines

```text
Read the NetSuite sales order table and show me how its lines are stored. Tell me the name of the field that holds the lines and its format. Then explain how my Salesforce order lines would have to be turned into that field, and what I must do when a line changes. Do not change anything.
```

## 4. Find the first-run risk

```text
Before we create anything, explain what the first run does with customers that already exist in both NetSuite and Salesforce, and what I should do first. Then list the questions I must answer.
```

## 5. Create it safely

```text
Create the sync we agreed on, saved paused, one table pair at a time starting with items. Show me the mapping before you switch each pair on. Set Delete Protection as we decided: <your decision>. Wait for my confirmation before switching anything on, and read the first run's results.
```

## 6. Read the issues

```text
Read the current issues on my NetSuite and Salesforce sync and group them by cause. For each group tell me whether it looks like a NetSuite concurrency limit, a bad reference (an item or customer id), a required field, a closed posting period, permissions, a Salesforce API limit, record locking, a validation rule, or a problem with the order lines. Show the affected mappings and record ids. Do not retry, revert or ignore anything.
```

## 7. Tune the pace

```text
My sync is showing concurrency or rate limit errors. Read its settings: the Data Sync Frequency, the rate limit for each app and pending changes. Tell me the one setting you would change first and why. Do not change anything until I approve.
```

## 8. Duplicates appeared

```text
Customers are duplicating between NetSuite and Salesforce. Do not delete or recreate the sync. Look at the table pairs, directions and recent issues. Tell me the most likely causes and what to check in each, including customers that existed in both systems before the first run.
```
