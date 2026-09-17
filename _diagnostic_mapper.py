from exchange_adapter_mapping import map_bitpin_account, map_bitpin_balance, map_toobit_account

class R:
    pass

r = R()

print("=== BITPIN ACCOUNT ===")
r.status = "NOT_IMPLEMENTED"
r.allowed = False
r.operation = "get_account"
r.reason = "test"
r.data = None
print(map_bitpin_account(r))

print()
print("=== BITPIN BALANCE ===")
r.operation = "get_balances"
print(map_bitpin_balance(r))

print()
print("=== TOOBIT ACCOUNT ===")
r.status = "PASS"
r.allowed = True
r.operation = "get_account"
r.reason = "test"
r.data = {
    "account_response": {
        "accountType": "master",
        "canTrade": None,
    },
    "balance_rows": 0,
}
print(map_toobit_account(r))
