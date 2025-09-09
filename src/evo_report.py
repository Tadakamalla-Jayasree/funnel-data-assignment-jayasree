import argparse
import pandas as pd
import json
import matplotlib.pyplot as plt
import os
import sys


def main(events_file, messages_file, orders_file, out_dir):
    # Ensure output directory exists
    os.makedirs(out_dir, exist_ok=True)

    # ---------------- Load Data ----------------
    try:
        events = pd.read_csv(events_file)
        messages = pd.read_csv(messages_file)
        orders = pd.read_csv(orders_file)
    except Exception as e:
        print(f"Error loading input files: {e}")
        sys.exit(1)

    # ---------------- Funnel ----------------
    funnel_order = ["Loaded", "Interact", "Clicks", "Purchase"]

    if not {"device", "event_name", "user_id"}.issubset(events.columns):
        print("Missing required columns in events.csv")
        funnel_results, funnel_df = [], pd.DataFrame()
    else:
        funnel = (
            events.groupby(["device", "event_name"])["user_id"]
            .nunique()
            .reset_index()
        )

        funnel["step_order"] = funnel["event_name"].apply(
            lambda x: funnel_order.index(x) if x in funnel_order else -1
        )
        funnel = funnel[funnel["step_order"] >= 0].sort_values(
            ["device", "step_order"]
        )

        results = []
        for device, grp in funnel.groupby("device"):
            start_users = grp.iloc[0]["user_id"]
            prev_users = start_users
            for _, row in grp.iterrows():
                conv_prev = (
                    round(100 * row["user_id"] / prev_users, 2)
                    if prev_users > 0
                    else 0
                )
                conv_start = (
                    round(100 * row["user_id"] / start_users, 2)
                    if start_users > 0
                    else 0
                )
                results.append(
                    {
                        "step": row["event_name"],
                        "users": int(row["user_id"]),
                        "conv_from_prev_pct": conv_prev,
                        "conv_from_start_pct": conv_start,
                        "device": device,
                    }
                )
                prev_users = row["user_id"]

        funnel_results = results
        funnel_df = pd.DataFrame(results)

        # Funnel chart
        if not funnel_df.empty:
            funnel_df.pivot(index="step", columns="device", values="users").plot(
                kind="bar", figsize=(8, 5)
            )
            plt.title("Funnel conversion by step and device")
            plt.ylabel("Users")
            plt.xticks(rotation=0)
            plt.tight_layout()
            plt.savefig(os.path.join(out_dir, "funnel.png"))
            plt.close()

    # ---------------- Intents ----------------
    if "detected_intent" not in messages.columns:
        print("Missing 'detected_intent' column in messages.csv")
        intents = []
    else:
        messages["detected_intent"] = messages["detected_intent"].fillna("unknown")
        intent_counts = messages["detected_intent"].value_counts().reset_index()
        intent_counts.columns = ["intent", "count"]
        intent_counts["pct_of_total"] = round(
            100 * intent_counts["count"] / intent_counts["count"].sum(), 2
        )

        intents = intent_counts.to_dict(orient="records")

        # Intent chart
        intent_counts.head(10).set_index("intent")["count"].plot(
            kind="bar", figsize=(8, 5)
        )
        plt.title("Top 10 Intents")
        plt.ylabel("Count")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "intents.png"))
        plt.close()

    # ---------------- Cancellation SLA ----------------
    if not {"created_at", "canceled_at"}.issubset(orders.columns):
        print("Missing 'created_at' or 'canceled_at' columns in orders.csv")
        cancellation_sla = {}
    else:
        orders["created_at"] = pd.to_datetime(orders["created_at"], errors="coerce")
        orders["canceled_at"] = pd.to_datetime(orders["canceled_at"], errors="coerce")

        total_orders = len(orders)
        canceled = orders["canceled_at"].notnull().sum()
        violations = (
            (orders["canceled_at"] - orders["created_at"]).dt.total_seconds() > 3600
        ).sum()
        violation_rate = (
            round(100 * violations / total_orders, 2) if total_orders > 0 else 0
        )

        cancellation_sla = {
            "total_orders": int(total_orders),
            "canceled": int(canceled),
            "violations": int(violations),
            "violation_rate_pct": violation_rate,
        }

    # ---------------- Save JSON ----------------
    report = {
        "funnel": funnel_results,
        "intents": intents,
        "cancellation_sla": cancellation_sla,
    }

    with open(os.path.join(out_dir, "report.json"), "w") as f:
        json.dump(report, f, indent=2)

    # ---------------- Console Summary ----------------
    print("Report generated")
    print(f"- Funnel steps: {len(funnel_results)}")
    print(f"- Intents found: {len(intents)}")
    if cancellation_sla:
        print(
            f"- Cancellation SLA violation rate: {cancellation_sla['violation_rate_pct']}%"
        )
    print(f"Output saved in: {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Funnel Data Report")
    parser.add_argument("--events", required=True, help="Path to events.csv")
    parser.add_argument("--messages", required=True, help="Path to messages.csv")
    parser.add_argument("--orders", required=True, help="Path to orders.csv")
    parser.add_argument("--out", required=True, help="Output directory")
    args = parser.parse_args()

    main(args.events, args.messages, args.orders, args.out)
