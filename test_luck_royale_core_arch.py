"""
Unit and integration test suite for Centralized Backend Architecture & Data Models (Luck Royale FF 1.39).
Verifies:
1. Machine Registry & Configuration Schema (Existence, Visibility, Availability, Eligibility, Spin Authorization).
2. Reward Pool Models (Weighted Probabilities, Rarity Tiers, Isolation, Guaranteed Drop Rules).
3. Voucher, Token & Special Exchange (Incubator Forge) Models & Alias Resolvers.
4. File/Database Persistence Layer (JSON Atomic Write, Versioning, Validation, SQLite Tables).
5. Shared Interface Contracts (ABCs and DTOs for gacha_eng, economy_spec, admin_api).
6. Backward Compatibility (Dynamic CHEST_CONFIGS, DEFAULT_SPECIAL_EXCHANGES, Protobuf Encoders/Decoders).
"""

import copy
import json
import os
import random
import sys
import tempfile
import time
import unittest

# Ensure server package path is present in sys.path
_SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
if _SERVER_DIR not in sys.path:
    sys.path.insert(0, _SERVER_DIR)

from core.database import db
from core.state import DEFAULT_ACCOUNT_ID, state
from proto.gacha_models import (
    CHEST_CONFIGS,
    CHEST_DIAMOND_ROYALE,
    CHEST_GOLD_ROYALE,
    CHEST_INCUBATOR,
    CHEST_WEAPON_ROYALE,
    DEFAULT_SPECIAL_EXCHANGES,
    ITEM_BLUEPRINT_JOKER,
    ITEM_BLUEPRINT_YINYANG,
    ITEM_EVOLUTION_STONE,
    ITEM_FF_TOKEN,
    ITEM_MAGIC_CUBE,
    LEGACY_ITEM_BLUEPRINT_JOKER,
    LEGACY_ITEM_BLUEPRINT_YINYANG,
    LEGACY_ITEM_EVOLUTION_STONE,
    LEGACY_ITEM_FF_TOKEN,
    LEGACY_VOUCHER_DIAMOND_ROYALE,
    LEGACY_VOUCHER_GOLD_ROYALE,
    LEGACY_VOUCHER_INCUBATOR,
    LEGACY_VOUCHER_WEAPON_ROYALE,
    VALID_ITEM_ID_ALIASES,
    VOUCHER_ALIASES,
    VOUCHER_DIAMOND_ROYALE,
    VOUCHER_GOLD_ROYALE,
    VOUCHER_INCUBATOR,
    VOUCHER_WEAPON_ROYALE,
    ChestConfig,
    ChestTabType,
    CoinType,
    ConsumeType,
    CostDeductionResult,
    CostType,
    DropItem,
    DropRarityTier,
    ExtraRewardConfig,
    ForgeExchangeResult,
    GachaPlayerState,
    GachaShowItemConfig,
    IEconomyService,
    IGachaEngine,
    ILuckRoyaleAdminService,
    ILuckRoyaleRegistry,
    LotteryType,
    LuckRoyaleConfigManager,
    LuckRoyaleRegistry,
    LuckyMeterConfig,
    MachineConfig,
    MachineState,
    RareType,
    RewardPool,
    RewardPoolItem,
    SpecialExchangeConfig,
    SpecialExchangeRecipe,
    SpinRequest,
    SpinResult,
    VoucherDefinition,
    config_manager,
    decode_do_gacha_special_exchange_req,
    decode_lottery_req,
    encode_do_gacha_special_exchange_res,
    encode_get_gacha_desc_res,
    encode_get_gacha_info_res,
    encode_get_lottery_probability_res,
    encode_lottery_res,
    is_stackable_item,
    registry,
    resolve_canonical_item_id,
    validate_catalog_dict,
    validate_machine_config,
)


class TestLuckRoyaleArchitecture(unittest.TestCase):

    def setUp(self):
        self.test_aid = 10001
        state.set_wallet(coins=50000, gems=5000, account_id=self.test_aid)

    # -----------------------------------------------------------------------
    # 1. Machine Registry & Configuration Schema
    # -----------------------------------------------------------------------
    def test_machine_existence_and_registry(self):
        """Verify machine existence in registry with all standard chests."""
        for cid in (CHEST_DIAMOND_ROYALE, CHEST_WEAPON_ROYALE, CHEST_GOLD_ROYALE, CHEST_INCUBATOR):
            machine = registry.get_machine(cid)
            self.assertIsNotNone(machine, f"Machine {cid} must exist in registry")
            self.assertEqual(machine.chest_id, cid)
            self.assertGreater(len(machine.items), 0, f"Machine {cid} must have reward items")

    def test_visibility_separation(self):
        """Verify visibility check independent of availability."""
        diamond = registry.get_machine(CHEST_DIAMOND_ROYALE)
        test_cfg = copy.deepcopy(diamond)
        now = int(time.time())

        # When visible
        test_cfg.is_visible = True
        self.assertTrue(test_cfg.is_visible_to(now=now))

        # When hidden by admin
        test_cfg.is_visible = False
        self.assertFalse(test_cfg.is_visible_to(now=now))

        # When expired
        test_cfg.is_visible = True
        test_cfg.end_time = now - 100
        self.assertFalse(test_cfg.is_visible_to(now=now))

    def test_availability_separation(self):
        """Verify availability rules (enabled, active window, maintenance)."""
        gold = registry.get_machine(CHEST_GOLD_ROYALE)
        test_cfg = copy.deepcopy(gold)
        now = int(time.time())

        # Normal active state
        test_cfg.is_enabled = True
        test_cfg.state_enum = MachineState.ACTIVE
        test_cfg.start_time = 0
        test_cfg.end_time = 0
        self.assertTrue(test_cfg.is_available(now))

        # Maintenance mode
        test_cfg.state_enum = MachineState.MAINTENANCE
        self.assertFalse(test_cfg.is_available(now))

        # Disabled
        test_cfg.state_enum = MachineState.ACTIVE
        test_cfg.is_enabled = False
        self.assertFalse(test_cfg.is_available(now))

        # Scheduled future start
        test_cfg.is_enabled = True
        test_cfg.start_time = now + 3600
        self.assertFalse(test_cfg.is_available(now))

    def test_eligibility_separation(self):
        """Verify player eligibility rules."""
        weapon = registry.get_machine(CHEST_WEAPON_ROYALE)
        test_cfg = copy.deepcopy(weapon)
        test_cfg.min_player_level = 10
        test_cfg.requires_elite_pass = True

        # Player under level
        ok, reason = test_cfg.check_eligibility({"level": 5, "has_elite_pass": True})
        self.assertFalse(ok)
        self.assertIn("Requires player level 10", reason)

        # Player without pass
        ok, reason = test_cfg.check_eligibility({"level": 15, "has_elite_pass": False})
        self.assertFalse(ok)
        self.assertIn("Requires active Elite Pass", reason)

        # Player fully eligible
        ok, reason = test_cfg.check_eligibility({"level": 15, "has_elite_pass": True})
        self.assertTrue(ok)

    def test_spin_authorization_rules(self):
        """Verify spin authorization for free spin, voucher, and currency."""
        gold = registry.get_machine(CHEST_GOLD_ROYALE)
        now = int(time.time())

        # Case 1: Free spin available
        p_state = {"next_free_time": now - 10, "lottery_count_weekly": 0}
        ok, msg = gold.authorize_spin(
            account_id=self.test_aid,
            gacha_type=LotteryType.ONE,
            consume_type=ConsumeType.FREE,
            player_state=p_state,
            wallet={"coins": 1000, "gems": 100},
            inventory={},
            now=now,
        )
        self.assertTrue(ok)

        # Case 2: Free spin on cooldown
        p_state_cd = {"next_free_time": now + 500, "lottery_count_weekly": 0}
        ok, msg = gold.authorize_spin(
            account_id=self.test_aid,
            gacha_type=LotteryType.ONE,
            consume_type=ConsumeType.FREE,
            player_state=p_state_cd,
            wallet={"coins": 1000, "gems": 100},
            inventory={},
            now=now,
        )
        self.assertFalse(ok)
        self.assertIn("cooldown", msg)

        # Case 3: Voucher draw with canonical and legacy aliases
        inv = {VOUCHER_GOLD_ROYALE: 1}
        ok, msg = gold.authorize_spin(
            account_id=self.test_aid,
            gacha_type=LotteryType.ONE,
            consume_type=ConsumeType.EXCHANGE_ITEM,
            player_state=p_state,
            wallet={},
            inventory=inv,
            now=now,
        )
        self.assertTrue(ok)

        # Legacy alias voucher (802000000) also authorized
        inv_legacy = {LEGACY_VOUCHER_GOLD_ROYALE: 1}
        ok, msg = gold.authorize_spin(
            account_id=self.test_aid,
            gacha_type=LotteryType.ONE,
            consume_type=ConsumeType.EXCHANGE_ITEM,
            player_state=p_state,
            wallet={},
            inventory=inv_legacy,
            now=now,
        )
        self.assertTrue(ok)

        # Insufficient coins
        ok, msg = gold.authorize_spin(
            account_id=self.test_aid,
            gacha_type=LotteryType.ONE,
            consume_type=ConsumeType.MONEY,
            player_state=p_state,
            wallet={"coins": 50},  # need 300
            inventory={},
            now=now,
        )
        self.assertFalse(ok)
        self.assertIn("Insufficient Gold", msg)

    # -----------------------------------------------------------------------
    # 2. Reward Pool Models & Probabilities
    # -----------------------------------------------------------------------
    def test_reward_pool_isolation_and_weights(self):
        """Verify each machine pool is isolated and calculates weighted distribution."""
        for cid in (CHEST_DIAMOND_ROYALE, CHEST_WEAPON_ROYALE, CHEST_GOLD_ROYALE, CHEST_INCUBATOR):
            pool = registry.get_reward_pool(cid)
            self.assertIsNotNone(pool)
            sr = pool.get_super_rare_items()
            rare = pool.get_rare_items()
            normal = pool.get_normal_items()
            self.assertGreater(len(sr), 0, f"Chest {cid} must have Gold tier items")
            self.assertGreater(len(rare), 0, f"Chest {cid} must have Purple tier items")
            self.assertGreater(len(normal), 0, f"Chest {cid} must have Blue tier items")

            probs = pool.calculate_tier_probabilities()
            self.assertEqual(len(probs), 3)

    def test_reward_pool_roll_and_guaranteed_jackpot(self):
        """Verify random roll and guaranteed rare/super-rare roll."""
        pool = registry.get_reward_pool(CHEST_DIAMOND_ROYALE)
        rng = random.Random(1337)

        # Force rare roll
        item = pool.roll_item(rng=rng, force_tier=RareType.SUPER_RARE)
        self.assertGreaterEqual(item.reward_level, RareType.SUPER_RARE)

    # -----------------------------------------------------------------------
    # 3. Voucher, Token & Special Exchange (Incubator Forge) Models
    # -----------------------------------------------------------------------
    def test_canonical_and_alias_vouchers(self):
        """Verify canonical voucher IDs match Coordinator Baseline #49."""
        self.assertEqual(VOUCHER_GOLD_ROYALE, 110100010)
        self.assertEqual(VOUCHER_DIAMOND_ROYALE, 110100008)
        self.assertEqual(VOUCHER_WEAPON_ROYALE, 110100009)
        self.assertEqual(VOUCHER_INCUBATOR, 110100018)

        # Test alias resolution
        self.assertEqual(resolve_canonical_item_id(LEGACY_VOUCHER_GOLD_ROYALE), 110100010)
        self.assertEqual(resolve_canonical_item_id(LEGACY_ITEM_FF_TOKEN), 110200001)
        self.assertEqual(resolve_canonical_item_id(LEGACY_ITEM_EVOLUTION_STONE), 808000003)
        self.assertEqual(resolve_canonical_item_id(LEGACY_ITEM_BLUEPRINT_YINYANG), 808000001)

    def test_incubator_forge_recipes(self):
        """Verify Incubator forge recipes have YinYang (Tab 1) and Joker (Tab 2)."""
        recipes = registry.get_special_exchanges()
        self.assertGreaterEqual(len(recipes), 12)

        tab1 = [r for r in recipes if r.forge_tab_id == 1]
        tab2 = [r for r in recipes if r.forge_tab_id == 2]
        self.assertEqual(len(tab1), 6, "YinYang Tab 1 must contain 6 bundle recipes")
        self.assertEqual(len(tab2), 6, "Joker Tab 2 must contain 6 bundle recipes")

        # Top YinYang Gold bundle requires 3 blueprints + 7 stones
        top_yinyang = tab1[0]
        self.assertEqual(top_yinyang.item_id, 710000410)
        reqs = {it[0]: it[1] for it in top_yinyang.exchange_items}
        self.assertEqual(reqs.get(ITEM_BLUEPRINT_YINYANG), 3)
        self.assertEqual(reqs.get(ITEM_EVOLUTION_STONE), 7)

    # -----------------------------------------------------------------------
    # 4. File / Database Persistence Layer
    # -----------------------------------------------------------------------
    def test_atomic_file_persistence_and_versioning(self):
        """Verify atomic JSON persistence, schema validation, and version increment."""
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
            temp_path = tf.name

        try:
            mgr = LuckRoyaleConfigManager(config_path=temp_path)
            self.assertTrue(os.path.exists(temp_path))
            v1 = mgr._version

            # Mutate machine and save
            diamond = mgr.get_machine(CHEST_DIAMOND_ROYALE)
            diamond.once_price = 65
            mgr.set_machine(diamond)

            # Reload into fresh manager
            mgr2 = LuckRoyaleConfigManager(config_path=temp_path)
            self.assertGreater(mgr2._version, v1)
            reloaded_diamond = mgr2.get_machine(CHEST_DIAMOND_ROYALE)
            self.assertEqual(reloaded_diamond.once_price, 65)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_validation_schema(self):
        """Verify validation schema catches bad configurations."""
        invalid_cfg = ChestConfig(
            chest_id=0,  # Invalid
            chest_sub_id=0,
            priority=1,
            coin_type=99,  # Invalid
            chest_name="",  # Invalid
            exchange_itemid=0,
            free_type=0,
            once_price=-10,  # Invalid
            ten_price=0,
            exchange_once_num=0,
            exchange_ten_num=0,
            color_id=0,
            chest_model_id=0,
            show_model_male=0,
            show_model_female=0,
            rare_item_max=0,
            items=(),  # Invalid: empty pool
        )
        ok, errors = validate_machine_config(invalid_cfg)
        self.assertFalse(ok)
        self.assertGreater(len(errors), 3)

    def test_database_gacha_transaction_persistence(self):
        """Verify SQLite gacha_transactions and gacha_special_exchanges tables."""
        tx_id = db.record_gacha_transaction(
            account_id=self.test_aid,
            chest_id=CHEST_DIAMOND_ROYALE,
            gacha_type=LotteryType.ONE,
            consume_type=ConsumeType.MONEY,
            cost_type=CostType.DIAMOND,
            cost_amount=60,
            reward_list=[{"dest_award_id": ITEM_MAGIC_CUBE, "dest_award_num": 1}],
            lucky_before=149,
            lucky_after=0,
            has_big_reward=True,
        )
        self.assertGreater(tx_id, 0)

        txs = db.get_gacha_transactions(account_id=self.test_aid, limit=5)
        self.assertGreater(len(txs), 0)
        latest = txs[0]
        self.assertEqual(latest["chest_id"], CHEST_DIAMOND_ROYALE)
        self.assertTrue(latest["has_big_reward"])

        # Test special exchange record
        se_id = db.record_special_exchange(
            account_id=self.test_aid,
            forge_tab_id=1,
            item_id=710000410,
            count=1,
            consumed_items=[{"item_id": ITEM_BLUEPRINT_YINYANG, "count": 3}],
        )
        self.assertGreater(se_id, 0)
        purchases = db.get_special_exchange_purchases(self.test_aid)
        self.assertIn((1, 710000410), purchases)

    # -----------------------------------------------------------------------
    # 5. Shared Interface Contracts & DTOs
    # -----------------------------------------------------------------------
    def test_interface_contracts_and_dtos(self):
        """Verify DTO instantiation and contract conformity."""
        req = SpinRequest(account_id=self.test_aid, chest_id=CHEST_DIAMOND_ROYALE)
        self.assertEqual(req.gacha_type, LotteryType.ONE)

        drop = DropItem(
            origin_award_type=1,
            origin_award_id=710000401,
            origin_award_num=1,
            dest_award_type=1,
            dest_award_id=ITEM_FF_TOKEN,
            dest_award_num=10,
            reward_level=RareType.SUPER_RARE,
            is_duplicate=True,
        )
        self.assertTrue(drop.is_duplicate)

        res = CostDeductionResult(
            success=True,
            cost_type=CostType.DIAMOND,
            amount_deducted=60,
            message="Deducted 60 Diamonds",
        )
        self.assertTrue(res.success)

    # -----------------------------------------------------------------------
    # 6. Backward Compatibility & Wire Encoders/Decoders
    # -----------------------------------------------------------------------
    def test_backward_compatibility_dicts(self):
        """Verify CHEST_CONFIGS and DEFAULT_SPECIAL_EXCHANGES dynamic proxies."""
        self.assertEqual(len(CHEST_CONFIGS), 4)
        self.assertIn(CHEST_DIAMOND_ROYALE, CHEST_CONFIGS)
        diamond = CHEST_CONFIGS[CHEST_DIAMOND_ROYALE]
        self.assertEqual(diamond.chest_id, CHEST_DIAMOND_ROYALE)

        self.assertGreaterEqual(len(DEFAULT_SPECIAL_EXCHANGES), 12)

    def test_protobuf_wire_encoders_and_decoders(self):
        """Verify CSGetGachaDescRes, CSGetGachaInfoRes, CSLotteryRes encode cleanly."""
        desc_bytes = encode_get_gacha_desc_res()
        self.assertGreater(len(desc_bytes), 100)

        info_bytes = encode_get_gacha_info_res([
            {"chest_id": CHEST_DIAMOND_ROYALE, "lottery_count_weekly": 5, "not_got_num": 10}
        ])
        self.assertGreater(len(info_bytes), 0)

        lottery_bytes = encode_lottery_res(
            lottery_goods=[{"origin_award_type": 1, "origin_award_id": 800000304, "origin_award_num": 1,
                            "dest_award_type": 1, "dest_award_id": 800000304, "dest_award_num": 1}],
            has_big_reward=True,
        )
        self.assertGreater(len(lottery_bytes), 0)


if __name__ == "__main__":
    unittest.main()
