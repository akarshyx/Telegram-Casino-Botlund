import asyncio
import math
import threading
import unittest
from unittest.mock import patch

import main


class _FakeUser:
    def __init__(self, user_id):
        self.id = user_id


class _FakeQuery:
    def __init__(self, user_id):
        self.from_user = _FakeUser(user_id)
        self.answers = []
        self.edits = []

    async def answer(self, text="", **kwargs):
        self.answers.append((text, kwargs))

    async def edit_message_text(self, text, **kwargs):
        self.edits.append((text, kwargs))


class BalanceSafetyTests(unittest.TestCase):
    def setUp(self):
        self.originals = {
            "user_balances": main.user_balances,
            "crypto_house_balances": main.crypto_house_balances,
            "house_balance": main.house_balance,
            "casino_balance_usd": main.casino_balance_usd,
            "pending_referral_commissions": main.pending_referral_commissions,
            "referral_earnings": main.referral_earnings,
        }
        main.user_balances = {"u1": 10.0}
        main.crypto_house_balances = {"USDT": 100.0, "GRAM": 1.0}
        main.house_balance = 100.0
        main.casino_balance_usd = 100.0
        main.pending_referral_commissions = {"u1": 5.0}
        main.referral_earnings = {}
        main._processing_referral_claims.clear()

        self.patches = [
            patch.object(main, "_refresh_balances_from_disk_if_changed"),
            patch.object(main, "_flush_balances_backup"),
            patch.object(main, "save_data_critical"),
            patch.object(main, "save_data"),
            patch.object(main, "log_transaction"),
        ]
        for active_patch in self.patches:
            active_patch.start()

    def tearDown(self):
        main._processing_referral_claims.clear()
        for active_patch in reversed(self.patches):
            active_patch.stop()
        main.user_balances = self.originals["user_balances"]
        main.crypto_house_balances = self.originals["crypto_house_balances"]
        main.house_balance = self.originals["house_balance"]
        main.casino_balance_usd = self.originals["casino_balance_usd"]
        main.pending_referral_commissions = self.originals["pending_referral_commissions"]
        main.referral_earnings = self.originals["referral_earnings"]

    def test_core_user_primitives_reject_non_finite_amounts(self):
        for bad_amount in (float("nan"), float("inf"), float("-inf")):
            before = main.get_real_user_balance("u1")
            self.assertEqual(main.ultra_secure_add_user_balance("u1", bad_amount), before)
            self.assertFalse(main.ultra_secure_deduct_user_balance("u1", bad_amount))
            self.assertEqual(main.get_real_user_balance("u1"), before)

    def test_user_debit_is_atomic_and_never_overdraws(self):
        results = []

        def debit_once():
            results.append(main.ultra_secure_deduct_user_balance("u1", 1.0, "test_bet"))

        threads = [threading.Thread(target=debit_once) for _ in range(20)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(sum(results), 10)
        self.assertEqual(main.get_real_user_balance("u1"), 0.0)

    def test_house_mutations_validate_and_reject_overdrafts(self):
        self.assertFalse(main.add_house_balance(float("nan")))
        self.assertFalse(main.deduct_house_balance(float("inf")))
        self.assertFalse(main.deduct_house_balance(101.0))
        self.assertEqual(main.get_house_balance(), 100.0)
        self.assertTrue(main.deduct_house_balance(40.0))
        self.assertEqual(main.get_house_balance(), 60.0)
        self.assertTrue(main.add_house_balance(2.5))
        self.assertEqual(main.get_house_balance(), 62.5)

    def test_referral_claim_can_only_credit_once_when_callbacks_race(self):
        queries = [_FakeQuery("u1"), _FakeQuery("u1")]
        original_currency = main.get_user_currency
        original_add = main.ultra_secure_add_user_balance
        original_save = main.save_data_critical
        try:
            main.get_user_currency = lambda _uid: "USDT"
            main.ultra_secure_add_user_balance = lambda uid, amount, tx: (
                main.user_balances.__setitem__(uid, main.get_real_user_balance(uid) + amount)
                or main.get_real_user_balance(uid)
            )
            main.save_data_critical = lambda: None
            with patch.object(main, "deduct_house_balance", return_value=True) as house_debit:
                async def run_claims():
                    await asyncio.gather(
                        main.handle_claim_referral_commission(queries[0], None),
                        main.handle_claim_referral_commission(queries[1], None),
                    )

                asyncio.run(run_claims())
                self.assertEqual(house_debit.call_count, 1)
            self.assertEqual(main.user_balances["u1"], 15.0)
            self.assertEqual(main.pending_referral_commissions["u1"], 0.0)
        finally:
            main.get_user_currency = original_currency
            main.ultra_secure_add_user_balance = original_add
            main.save_data_critical = original_save

    def test_set_user_balance_rejects_negative_and_non_finite_values(self):
        for bad_amount in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                main.set_user_balance("u1", bad_amount)
        self.assertEqual(main.get_real_user_balance("u1"), 10.0)


if __name__ == "__main__":
    unittest.main()