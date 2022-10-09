import requests
from datetime import datetime
import csv
from pathlib import Path
from collections import defaultdict

csrf_token = "xxxx"  # Fetch manually
jwt = "xxxxxx"  # Fetch manually


def get_investments():
    orders_url = "https://api.smallcase.com/user/sc/investments"
    request_headers = {"x-csrf-token": csrf_token, "x-sc-jwt": jwt}
    response = requests.get(orders_url, headers=request_headers)
    if not response.status_code == 200:
        raise Exception("Get investments error from Smallcase")
    return response.json()["data"]["investedSmallcases"]


def get_orders(iscid):
    orders_url = "https://api.smallcase.com/user/sc/orders"
    request_params = {"iscid": iscid}
    request_headers = {"x-csrf-token": csrf_token, "x-sc-jwt": jwt}
    response = requests.get(orders_url, params=request_params, headers=request_headers)
    if not response.status_code == 200:
        raise Exception("Get orders error from Smallcase")
    return response.json()["data"]


def get_subscriptions():
    subscriptions_url = "https://api.smallcase.com/user/sc/subscriptions"
    request_headers = {"x-csrf-token": csrf_token, "x-sc-jwt": jwt}
    response = requests.get(subscriptions_url, headers=request_headers)
    if not response.status_code == 200:
        raise Exception("Get subscriptions error from Smallcase")
    return response.json()["data"]


def get_subscription_history(plan_id):
    subscription_history_url = "https://api.smallcase.com/user/sc/subscription/history"
    request_params = {"planId": plan_id}
    request_headers = {"x-csrf-token": csrf_token, "x-sc-jwt": jwt}
    response = requests.get(subscription_history_url, params=request_params, headers=request_headers)
    if not response.status_code == 200:
        raise Exception("Get subscription history error from Smallcase" + str(response.text))
    return response.json()["data"]


def get_subscription_details():
    subscriptions = get_subscriptions()

    # [{"fee": 6749.1, "date": "2022-09-01"}, {"fee": 6749.1, "date": "2022-09-01"}]
    subscription_details = defaultdict(list)
    for subscription in subscriptions:
        if subscription["status"] != "SUBSCRIBED":
            continue
        scid = subscription["scids"][0]["scid"]
        subscription_details[scid].append(
            {"fee": subscription["amount"], "date": date_helper(subscription["date"]), "scid": scid})
        subscription_history = get_subscription_history(subscription["id"])
        for history in subscription_history:
            if subscription_details[scid][0]["date"] == date_helper(history["date"]):
                continue
            subscription_details[scid].append(
                {"fee": history["amount"], "date": date_helper(history["date"]), "scid": scid})

    return subscription_details


def date_helper(date_time):
    return datetime.fromisoformat(date_time[:-1]).strftime("%Y-%m-%d")


# [{"date", "label", "buy_amount", "sell_amount", "buy_quantity", "sell_quantity", "dp_charges"}]
def write_to_csv(smallcase_name, sorted_rows, summary_row):
    header = ["date", "label", "buy_amount", "sell_amount", "buy_quantity", "sell_quantity", "dp_charges"]
    file_name = Path(__file__).with_name(smallcase_name + '.csv')
    with open(file_name, 'w', encoding='UTF8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(sorted_rows)
        writer.writerows([[] * 5])
        writer.writerow(["total_invested", "current_value", "current_returns", "time_in_days", "time_in_years"])
        writer.writerow(summary_row)


def main():
    subscription_details = get_subscription_details()
    invested_smallcases = get_investments()
    dp_charge = 15
    for invested_smallcase in invested_smallcases:
        rows = []
        iscid = invested_smallcase["_id"]
        subscription_detail = subscription_details[invested_smallcase["scid"]]
        orders = get_orders(iscid)
        for subscription in subscription_detail:
            rows.append([subscription["date"], 'SUBSCRIPTION', subscription["fee"], 0, 0, 0, 0])
        for batch in orders[0]["batches"]:
            buy_quantity, sell_quantity = 0, 0
            for stock_order in batch["orders"]:
                if stock_order["status"] != "COMPLETE":
                    continue
                if stock_order["transactionType"] == "BUY":
                    buy_quantity += 1
                elif stock_order["transactionType"] == "SELL":
                    sell_quantity += 1

            rows.append([date_helper(batch["date"]), batch["label"], round(batch["buyAmount"], 2),
                         round(batch["sellAmount"], 2), buy_quantity, sell_quantity, sell_quantity * dp_charge])

        sorted_rows = sorted(rows, key=lambda x: (x[0]))
        total_invested = 0
        current_value = round(invested_smallcase["returns"]["networth"], 2)
        for row in sorted_rows:
            total_invested += row[2] - row[3] + row[6]
        start_day = datetime.strptime(sorted_rows[0][0], "%Y-%m-%d")
        current_day = datetime.now()
        days = (current_day - start_day).days
        years = days // 365
        months = (days - years * 365) // 30
        summary_row = [round(total_invested, 2), round(current_value, 2), round(current_value - total_invested, 2),
                       days, round(years + (0.1 * months), 2)]
        write_to_csv(invested_smallcase["name"], sorted_rows, summary_row)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()
    # write_to_csv("NNF10")
