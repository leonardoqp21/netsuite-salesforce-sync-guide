# Prerequisites: connecting NetSuite and Salesforce

From the Stacksync connector documentation. Check the current pages, and use sandboxes.

## NetSuite

- An **admin role** is needed to set it up.
- In **Setup > Company > Enable Features**, enable **REST web services** and **token-based authentication**.
- Create an **integration record** with token-based authentication.
- You connect through a **secure sign-in link**. The account ID and tokens go into that form, **never into a chat**.
- Give the integration role what the sync needs and no more: the record types and sublists it reads and writes. **Not an administrator role.**
- In **Setup > Integration > Manage Integrations**, set the Stacksync integration's **Concurrency Limit to 3**, and size other integrations the same way.
- Saved searches are **read only**. A saved search that returns no records may not show its columns, which can keep a sync from mapping them.
- Writes to term, subsidiary, department and classification **records** are listed as coming soon. **Setting those values on a customer works.**
- Custom objects read. Writing them is on request.

## Salesforce

- The org's **edition must include the API**. Enterprise, Unlimited, Developer and Performance do. Professional needs the API add-on. Group and Essentials cannot connect.
- Connect a **dedicated user** made for Stacksync, with only the permissions it needs. It needs **API Enabled**.
- The Stacksync app must be **installed in the org once**, by a user who can approve uninstalled connected apps.
- **Custom fields** (the NetSuite internal id, payment terms, credit limit) must be visible to the connected user through **field-level security**.
- **Formula fields** are read only and computed.
- Change capture uses regular polling by default, or Apex triggers when set up with the extra permissions.

## Both

- Both connections must be in the **same Stacksync region**.
- **Sandboxes first** for both systems.
- Write the **field ownership matrix** ([ownership and conflicts](ownership-and-conflicts.md)).
- Decide **Delete Protection** for each app before switching on.
- Create the **mapping tables**: product code to item id, owner ids, picklist values.
- Agree what "fresh" means and **measure the delay** in a pilot.

## Never paste credentials in a chat

Apps connect through secure sign-in links. The same goes for building the sync from an assistant: see [build with MCP](build-with-mcp.md).

Official pages: [NetSuite connector](https://docs.stacksync.com/two-way-sync/connectors/netsuite) and [Salesforce connector](https://docs.stacksync.com/two-way-sync/connectors/salesforce).
