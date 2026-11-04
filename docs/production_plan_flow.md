# Production Plan: branch warehouse flow

How the Production Plan customization picks, limits and checks warehouses per branch,
and how those warehouses reach the Work Orders.

## 1. What happens, step by step

```mermaid
flowchart TD
  subgraph Setup["One-time setup (per company + branch)"]
    A["Create Production Branch Warehouse<br/>company, branch, parent group warehouse,<br/>source / WIP / FG / wastage defaults"] --> A1{"Parent is a group warehouse<br/>of the same company, and every<br/>default sits under it?"}
    A1 -- No --> A2["Save blocked: Invalid Warehouse"]
    A1 -- Yes --> A3["Saved as '{branch} - {company}'"]
  end

  subgraph Form["Production Plan form (browser)"]
    B["Pick Company"] --> C["Pick Branch<br/>(only branches of that company)"]
    C --> D["Header warehouses filled from the branch:<br/>Source, WIP, Finished Goods, Wastage<br/>(blank where the branch has no default)"]
    D --> E["Every warehouse picker, header and rows,<br/>lists only non-group warehouses<br/>under the branch's group warehouse"]
    E --> F["Header Finished Goods / Source / WIP<br/>copied to every item row"]
    T["Or pick a Production Plan Template"] --> T1{"Template company<br/>= plan company?"}
    T1 -- No --> T2["Message, nothing loaded"]
    T1 -- Yes --> T3{"Template has a branch?"}
    T3 -- Yes --> C
    T3 -- No --> T4["Branch cleared, template's own<br/>warehouses used"] --> F
    B -. "company changed" .-> B1["Branch cleared"]
  end

  subgraph Save["Save (validate, server)"]
    G{"Any group warehouse<br/>on header or rows?"}
    G -- Yes --> G1["Blocked: Invalid Warehouse"]
    G -- No --> H{"Branch set?"}
    H -- No --> OK["Saved"]
    H -- Yes --> H1{"Branch belongs to<br/>the plan's company?"}
    H1 -- No --> H2["Blocked: Invalid Branch"]
    H1 -- Yes --> H3{"Every warehouse inside<br/>the branch's group warehouse?"}
    H3 -- No --> H4["Blocked: Invalid Warehouse<br/>(names the offending fields)"]
    H3 -- Yes --> OK
  end

  subgraph Submit["Submit (on_submit, server)"]
    S["Group-warehouse check again"] --> S1["make_work_order()"]
    S1 --> S2["Each draft Work Order gets:<br/>FG, Source, WIP warehouses,<br/>scrap warehouse = Wastage (if set),<br/>skip transfer flag,<br/>required items' source warehouse"]
  end

  A3 --> C
  F --> G
  OK --> S
```

## 2. Which file does what

```mermaid
graph LR
  PBW["Production Branch Warehouse doctype<br/>production_branch_warehouse.py"] -->|"validate: branch_profile_candidates"| WR[warehouse_rules.py]
  PBW -->|get_branch_warehouses| HPP[hook_functions/production_plan.py]
  DE[hooks.py doc_events] -->|validate| VAL[validate]
  DE -->|on_submit| SUB[on_submit]
  VAL --> GW["validate_warehouses<br/>block group warehouses"]
  VAL -->|only if custom_branch set| BW["validate_branch_warehouses<br/>same company + inside branch"]
  SUB --> GW
  SUB -->|"make_work_order, set warehouses"| WO[Work Order]
  GW --> WR
  BW --> WR
  VAL -.- HPP
  SUB -.- HPP
  HOOKS[hooks.py doctype_js] --> BWJS[public/js/branch_warehouse.js]
  HOOKS --> PPJS[public/js/production_plan.js]
  HOOKS --> PPTJS[public/js/production_plan_template.js]
  PPJS --> BWJS
  PPTJS --> BWJS
  BWJS -->|frappe.db.get_value| PBW
  PPJS -->|loads template| PPT[Production Plan Template]
  CF["custom/production_plan*.json"] -->|custom_branch Link| PBW
```

## 3. Field mapping

| Production Plan header field | Comes from Production Branch Warehouse | Ends up on |
|---|---|---|
| `custom_source_warehouse` | `source_warehouse` | item rows, Work Order `source_warehouse`, required items |
| `custom_wip_warehouse` | `wip_warehouse` | item rows, Work Order `wip_warehouse` |
| `custom_finished_goods_warehouse` | `fg_warehouse` | item rows (`warehouse`), Work Order `fg_warehouse` |
| `custom_wastage_warehouse` | `wastage_warehouse` | Work Order `scrap_warehouse` |
| `custom_branch_warehouse` (read-only) | `parent_warehouse` | limits every warehouse picker |

The browser-side filters only make picking easier. The checks that actually stop a wrong
warehouse are the server-side ones in `hook_functions/production_plan.py` and
`warehouse_rules.py`.
