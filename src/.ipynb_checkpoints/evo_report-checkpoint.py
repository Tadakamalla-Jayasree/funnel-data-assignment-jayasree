import argparse
import pandas as pd
import json
import matplotlib.pyplot as plt
import os

def main(events_file, messages_file, orders_file, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    # Load CSVs
    events = pd.read_csv(events_file)
    messages = pd.read_csv(messages_file)
    orders = pd.read_csv(orders_file)

    # ---------------- Funnel ----------------
    funnel_order = ["Loaded", "Interact", "Clicks", "Purchase"]
    funnel = (
        events.groupby(["device", "event_name"])["user_id"].nunique().reset_index()
    )

    funnel["step_order"] = funnel["event_name"].apply(lambda x: funnel_order.index(x) if x in funnel_order else -1)
    funnel = funnel[funnel["step_order"] >= 0].sort_values(["device", "step_order"])

    results = []
    for device, grp in funnel.groupby("device"):
        start_users = grp.iloc[0]["user_id"]
        prev_users = start_users
        for _, row in grp.iterrows():
            conv_prev = round(100 * row["user_id"] / prev_users, 2) if prev_users > 0 else 0
            conv_start = round(100 * row["user_id"] / start_users, 2) if start_users > 0 else 0
            results.append({
                "step": row["event_name"],
                "users": int(row["user_id"]),
                "conv_from_prev_pct": conv_prev,
                "conv_from_start_pct": conv_start,
                "device": device
            })
            prev_users = row["user_id"]

    # Funnel chart
    funnel_df = pd.DataFrame(results)
    funnel_df.pivot(index="step", columns="device", values="users").plot(kind="bar")
    plt.title("Funnel conversion by step and device")
    plt.ylabel("Users")
    plt.savefig(os.path.join(out_dir, "funnel.png"))
    plt.close()

    # ---------------- Intents ----------------
    messages["detected_intent"] = messages["detected_intent"].fillna("unknown")
    intent_counts = messages["detected_intent"].value_counts().reset_index()
    intent_counts.columns = ["intent", "count"]
    intent_counts["pct_of_total"] = round(100 * intent_counts["count"] / intent_counts["count"].sum(), 2)

    intents = intent_counts.to_dict(orient="records")

    # Intent chart
    intent_counts.head(10).set_index("intent")["count"].plot(kind="bar")
    plt.title("Top 10 Intents")
    plt.ylabel("Count")
    plt.savefig(os.path.join(out_dir, "intents.png"))
    plt.close()

    # ---------------- Cancellation SLA ----------------
    orders["created_at"] = pd.to_datetime(orders["created_at"])
    orders["canceled_at"] = pd.to_datetime(orders["canceled_at"], errors="coerce")

    total_orders = len(orders)
    canceled = orders["canceled_at"].notnull().sum()
    violations = ((orders["canceled_at"] - orders["created_at"]).dt.total_seconds() > 3600).sum()
    violation_rate = round(100 * violations / total_orders, 2) if total_orders > 0 else 0

    cancellation_sla = {
        "total_orders": int(total_orders),
        "canceled": int(canceled),
        "violations": int(violations),
        "violation_rate_pct": violation_rate
    }

    # ---------------- Save JSON ----------------
    report = {
        "funnel": results,
        "intents": intents,
        "cancellation_sla": cancellation_sla
    }

    with open(os.path.join(out_dir, "report.json"), "w") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", required=True)
    parser.add_argument("--messages", required=True)
    parser.add_argument("--orders", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    main(args.events, args.messages, args.orders, args.out)
