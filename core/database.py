"""
India V1 — High-Performance SQLite Persistence Engine
Persists all player profiles, currencies, claimed rewards, inventory, equips,
characters, pets, mails, activity states, and full audit logs across server restarts.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "india_v1.db",
)


class Database:
    """Thread-safe SQLite storage engine for game state and claims."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._lock = threading.RLock()
        self._local = threading.local()
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                check_same_thread=False,
                isolation_level=None,  # Autocommit mode for granular transaction control
            )
            conn.row_factory = sqlite3.Row
            # Enable WAL mode for high concurrency
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute("PRAGMA foreign_keys = ON;")
            self._local.conn = conn
        return self._local.conn

    def _init_schema(self) -> None:
        with self._lock:
            conn = self._get_conn()
            conn.execute("BEGIN IMMEDIATE;")
            try:
                # 1. Accounts & Profile
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS accounts (
                        account_id INTEGER PRIMARY KEY,
                        nickname TEXT NOT NULL,
                        level INTEGER NOT NULL DEFAULT 60,
                        exp INTEGER NOT NULL DEFAULT 125000,
                        gold INTEGER NOT NULL DEFAULT 999999,
                        diamonds INTEGER NOT NULL DEFAULT 999999,
                        selected_avatar_id INTEGER NOT NULL DEFAULT 102000004,
                        selected_pet_id INTEGER NOT NULL DEFAULT 120000001,
                        equipped_clothes_json TEXT NOT NULL DEFAULT '[]',
                        profile_data_json TEXT NOT NULL DEFAULT '{}',
                        is_banned INTEGER NOT NULL DEFAULT 0,
                        updated_at INTEGER NOT NULL
                    );
                """)

                # Auto-migration: ensure is_banned column exists for legacy database schemas
                cur = conn.cursor()
                cur.execute("PRAGMA table_info(accounts);")
                account_cols = [r["name"] for r in cur.fetchall()]
                if "is_banned" not in account_cols:
                    conn.execute("ALTER TABLE accounts ADD COLUMN is_banned INTEGER NOT NULL DEFAULT 0;")

                # 2. Inventory Items
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS inventory (
                        account_id INTEGER NOT NULL,
                        item_id INTEGER NOT NULL,
                        count INTEGER NOT NULL DEFAULT 1,
                        unlocked_at INTEGER NOT NULL,
                        PRIMARY KEY(account_id, item_id)
                    );
                """)

                # 3. Characters
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS characters (
                        account_id INTEGER NOT NULL,
                        avatar_id INTEGER NOT NULL,
                        level INTEGER NOT NULL DEFAULT 1,
                        exp INTEGER NOT NULL DEFAULT 0,
                        clothes_json TEXT NOT NULL DEFAULT '[]',
                        skills_json TEXT NOT NULL DEFAULT '[]',
                        unlocked_at INTEGER NOT NULL,
                        PRIMARY KEY(account_id, avatar_id)
                    );
                """)

                # 4. Pets
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS pets (
                        account_id INTEGER NOT NULL,
                        pet_id INTEGER NOT NULL,
                        level INTEGER NOT NULL DEFAULT 1,
                        exp INTEGER NOT NULL DEFAULT 0,
                        selected_skin_id INTEGER NOT NULL DEFAULT 0,
                        selected_skill_id INTEGER NOT NULL DEFAULT 0,
                        unlocked_at INTEGER NOT NULL,
                        PRIMARY KEY(account_id, pet_id)
                    );
                """)

                # 5. Mails
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS mails (
                        mail_id INTEGER PRIMARY KEY,
                        account_id INTEGER NOT NULL,
                        sender_name TEXT NOT NULL,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        rewards_json TEXT NOT NULL DEFAULT '[]',
                        is_read INTEGER NOT NULL DEFAULT 0,
                        is_claimed INTEGER NOT NULL DEFAULT 0,
                        created_at INTEGER NOT NULL
                    );
                """)

                # 6. Friends
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS friends (
                        account_id INTEGER NOT NULL,
                        friend_id INTEGER NOT NULL,
                        status TEXT NOT NULL DEFAULT 'accepted',
                        created_at INTEGER NOT NULL,
                        PRIMARY KEY(account_id, friend_id)
                    );
                """)

                # 7. Claims Repository (Tracks every single claimed reward)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_claims (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        account_id INTEGER NOT NULL,
                        claim_type TEXT NOT NULL,
                        target_id INTEGER NOT NULL,
                        details_json TEXT NOT NULL DEFAULT '{}',
                        claimed_at INTEGER NOT NULL,
                        UNIQUE(account_id, claim_type, target_id)
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_claims_acct ON user_claims(account_id, claim_type);")

                # 8. Activity Runtime States (Full blob persistence for Attendance, 7-days, Bingo, Activeness)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS activity_states (
                        account_id INTEGER PRIMARY KEY,
                        state_json TEXT NOT NULL,
                        updated_at INTEGER NOT NULL
                    );
                """)

                # 9. Audit Log (History of all user actions: claims, purchases, equips, invites)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        account_id INTEGER NOT NULL,
                        action_type TEXT NOT NULL,
                        summary TEXT NOT NULL,
                        payload_json TEXT NOT NULL DEFAULT '{}',
                        timestamp INTEGER NOT NULL
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_acct ON audit_log(account_id, timestamp DESC);")

                # 10. Gacha / Luck Royale State (Luck counter, weekly count, claim milestones, free cooldown)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS gacha_states (
                        account_id INTEGER NOT NULL,
                        chest_id INTEGER NOT NULL,
                        state_json TEXT NOT NULL,
                        updated_at INTEGER NOT NULL,
                        PRIMARY KEY (account_id, chest_id)
                    );
                """)

                # 11. Gacha Transactions Log (Audit history of all spins)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS gacha_transactions (
                        trans_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        account_id INTEGER NOT NULL,
                        chest_id INTEGER NOT NULL,
                        gacha_type INTEGER NOT NULL,
                        consume_type INTEGER NOT NULL,
                        cost_type INTEGER NOT NULL,
                        cost_amount INTEGER NOT NULL,
                        reward_list_json TEXT NOT NULL DEFAULT '[]',
                        lucky_before INTEGER NOT NULL DEFAULT 0,
                        lucky_after INTEGER NOT NULL DEFAULT 0,
                        has_big_reward INTEGER NOT NULL DEFAULT 0,
                        timestamp INTEGER NOT NULL
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_gacha_tx_acct ON gacha_transactions(account_id, timestamp DESC);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_gacha_tx_chest ON gacha_transactions(chest_id, timestamp DESC);")

                # 12. Gacha Special Exchanges (Incubator Forge crafts)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS gacha_special_exchanges (
                        trans_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        account_id INTEGER NOT NULL,
                        forge_tab_id INTEGER NOT NULL,
                        item_id INTEGER NOT NULL,
                        count INTEGER NOT NULL DEFAULT 1,
                        consumed_json TEXT NOT NULL DEFAULT '[]',
                        timestamp INTEGER NOT NULL
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_gacha_se_acct ON gacha_special_exchanges(account_id, timestamp DESC);")

                conn.execute("COMMIT;")
            except Exception:
                conn.execute("ROLLBACK;")
                raise

    # -------------------------------------------------------------------------
    # Profile & Currencies
    # -------------------------------------------------------------------------

    def get_profile(self, account_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            cur = self._get_conn().cursor()
            cur.execute("SELECT * FROM accounts WHERE account_id = ?;", (int(account_id),))
            row = cur.fetchone()
            if not row:
                return None
            data = dict(row)
            try:
                data["clothes"] = json.loads(data.pop("equipped_clothes_json"))
            except Exception:
                data["clothes"] = []
            try:
                extra = json.loads(data.pop("profile_data_json"))
                data.update(extra)
            except Exception:
                pass
            data["is_banned"] = bool(data.get("is_banned", 0))
            return data

    def save_profile(self, account_id: int, profile_dict: Dict[str, Any]) -> None:
        with self._lock:
            conn = self._get_conn()
            now = int(time.time())
            nick = str(profile_dict.get("nickname", "Clack"))
            lvl = int(profile_dict.get("level", 60))
            exp = int(profile_dict.get("exp", 125000))
            gold = int(profile_dict.get("coins", profile_dict.get("gold", 999999)))
            gems = int(profile_dict.get("gems", profile_dict.get("diamonds", 999999)))
            avatar = int(profile_dict.get("avatar_id", profile_dict.get("selected_avatar_id", 102000004)))
            pet = int(profile_dict.get("selected_pet_id", 120000001))
            clothes = json.dumps(profile_dict.get("clothes", []))
            is_banned = 1 if profile_dict.get("is_banned") else 0

            # Store extra fields
            extra = {k: v for k, v in profile_dict.items() if k not in {
                "account_id", "nickname", "level", "exp", "gold", "diamonds", "gems", "coins",
                "selected_avatar_id", "avatar_id", "selected_pet_id", "clothes", "is_banned"
            }}

            conn.execute("""
                INSERT INTO accounts (
                    account_id, nickname, level, exp, gold, diamonds,
                    selected_avatar_id, selected_pet_id, equipped_clothes_json, profile_data_json, is_banned, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id) DO UPDATE SET
                    nickname=excluded.nickname,
                    level=excluded.level,
                    exp=excluded.exp,
                    gold=excluded.gold,
                    diamonds=excluded.diamonds,
                    selected_avatar_id=excluded.selected_avatar_id,
                    selected_pet_id=excluded.selected_pet_id,
                    equipped_clothes_json=excluded.equipped_clothes_json,
                    profile_data_json=excluded.profile_data_json,
                    is_banned=excluded.is_banned,
                    updated_at=excluded.updated_at;
            """, (
                int(account_id), nick, lvl, exp, gold, gems, avatar, pet,
                clothes, json.dumps(extra), is_banned, now
            ))

    def set_player_banned(self, account_id: int, banned: bool = True) -> bool:
        with self._lock:
            now = int(time.time())
            cur = self._get_conn().cursor()
            cur.execute("""
                UPDATE accounts
                SET is_banned = ?, updated_at = ?
                WHERE account_id = ?;
            """, (1 if banned else 0, now, int(account_id)))
            return cur.rowcount > 0

    def is_player_banned(self, account_id: int) -> bool:
        with self._lock:
            cur = self._get_conn().cursor()
            cur.execute("SELECT is_banned FROM accounts WHERE account_id = ?;", (int(account_id),))
            row = cur.fetchone()
            return bool(row["is_banned"]) if row else False

    def list_accounts_paged(
        self,
        search: str = "",
        sort_by: str = "account_id",
        sort_dir: str = "asc",
        page: int = 1,
        limit: int = 20,
        is_banned: Optional[bool] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        with self._lock:
            cur = self._get_conn().cursor()
            clauses: List[str] = []
            params: List[Any] = []

            clean_search = str(search or "").strip()
            if clean_search:
                s_pattern = f"%{clean_search}%"
                clauses.append("(LOWER(nickname) LIKE LOWER(?) OR CAST(account_id AS TEXT) LIKE ?)")
                params.extend([s_pattern, s_pattern])

            if is_banned is not None:
                clauses.append("is_banned = ?")
                params.append(1 if is_banned else 0)

            where_sql = (" WHERE " + " AND ".join(clauses)) if clauses else ""

            # Count total
            cur.execute(f"SELECT COUNT(*) AS total FROM accounts{where_sql};", tuple(params))
            total_row = cur.fetchone()
            total = int(total_row["total"]) if total_row else 0

            # Sort sanitation
            sort_map = {
                "id": "account_id",
                "account_id": "account_id",
                "nickname": "nickname",
                "level": "level",
                "exp": "exp",
                "gold": "gold",
                "coins": "gold",
                "diamonds": "diamonds",
                "gems": "diamonds",
                "is_banned": "is_banned",
                "updated_at": "updated_at",
                "created_at": "account_id",
            }
            safe_sort = sort_map.get(str(sort_by or "").lower().strip(), "account_id")
            safe_dir = "DESC" if str(sort_dir or "").upper().strip() == "DESC" else "ASC"

            safe_page = max(1, int(page))
            safe_limit = max(1, min(100, int(limit)))
            offset = (safe_page - 1) * safe_limit

            query_sql = f"SELECT * FROM accounts{where_sql} ORDER BY {safe_sort} {safe_dir} LIMIT ? OFFSET ?;"
            cur.execute(query_sql, tuple(params + [safe_limit, offset]))

            results: List[Dict[str, Any]] = []
            for r in cur.fetchall():
                d = dict(r)
                try:
                    d["clothes"] = json.loads(d.pop("equipped_clothes_json", "[]"))
                except Exception:
                    d["clothes"] = []
                try:
                    extra = json.loads(d.pop("profile_data_json", "{}"))
                    d.update(extra)
                except Exception:
                    pass
                d["is_banned"] = bool(d.get("is_banned", 0))
                d["coins"] = d.get("gold", 0)
                d["gems"] = d.get("diamonds", 0)
                results.append(d)

            return results, total

    def update_wallet(self, account_id: int, gold: int, diamonds: int) -> None:
        with self._lock:
            conn = self._get_conn()
            now = int(time.time())
            conn.execute("""
                UPDATE accounts
                SET gold = ?, diamonds = ?, updated_at = ?
                WHERE account_id = ?;
            """, (int(gold), int(diamonds), now, int(account_id)))

    # -------------------------------------------------------------------------
    # Inventory
    # -------------------------------------------------------------------------

    def get_inventory(self, account_id: int) -> Dict[int, int]:
        with self._lock:
            cur = self._get_conn().cursor()
            cur.execute("SELECT item_id, count FROM inventory WHERE account_id = ?;", (int(account_id),))
            return {int(r["item_id"]): int(r["count"]) for r in cur.fetchall()}

    def save_inventory_item(self, account_id: int, item_id: int, count: int = 1) -> None:
        with self._lock:
            now = int(time.time())
            self._get_conn().execute("""
                INSERT INTO inventory (account_id, item_id, count, unlocked_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(account_id, item_id) DO UPDATE SET
                    count = excluded.count;
            """, (int(account_id), int(item_id), int(count), now))

    def delete_inventory_item(self, account_id: int, item_id: int) -> None:
        with self._lock:
            self._get_conn().execute(
                "DELETE FROM inventory WHERE account_id = ? AND item_id = ?;",
                (int(account_id), int(item_id)),
            )

    def save_inventory_batch(self, account_id: int, items: Dict[int, int]) -> None:
        if not items:
            return
        with self._lock:
            conn = self._get_conn()
            now = int(time.time())
            conn.execute("BEGIN IMMEDIATE;")
            try:
                for it_id, count in items.items():
                    conn.execute("""
                        INSERT INTO inventory (account_id, item_id, count, unlocked_at)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(account_id, item_id) DO UPDATE SET
                            count = excluded.count;
                    """, (int(account_id), int(it_id), int(count), now))
                conn.execute("COMMIT;")
            except Exception:
                conn.execute("ROLLBACK;")
                raise

    # -------------------------------------------------------------------------
    # Characters & Pets
    # -------------------------------------------------------------------------

    def get_characters(self, account_id: int) -> List[Dict[str, Any]]:
        with self._lock:
            cur = self._get_conn().cursor()
            cur.execute("SELECT * FROM characters WHERE account_id = ?;", (int(account_id),))
            rows = []
            for r in cur.fetchall():
                d = dict(r)
                d["clothes"] = json.loads(d.pop("clothes_json", "[]"))
                d["skills"] = json.loads(d.pop("skills_json", "[]"))
                rows.append(d)
            return rows

    def save_character(self, account_id: int, char_dict: Dict[str, Any]) -> None:
        with self._lock:
            now = int(time.time())
            avatar_id = int(char_dict.get("avatar_id", 0))
            lvl = int(char_dict.get("level", char_dict.get("unlocked_level", 1)))
            exp = int(char_dict.get("exp", 0))
            clothes = json.dumps(char_dict.get("clothes", []))
            skills = json.dumps(char_dict.get("skills", char_dict.get("equiped_skills", [])))
            self._get_conn().execute("""
                INSERT INTO characters (account_id, avatar_id, level, exp, clothes_json, skills_json, unlocked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id, avatar_id) DO UPDATE SET
                    level = excluded.level,
                    exp = excluded.exp,
                    clothes_json = excluded.clothes_json,
                    skills_json = excluded.skills_json;
            """, (int(account_id), avatar_id, lvl, exp, clothes, skills, now))

    def get_pets(self, account_id: int) -> List[Dict[str, Any]]:
        with self._lock:
            cur = self._get_conn().cursor()
            cur.execute("SELECT * FROM pets WHERE account_id = ?;", (int(account_id),))
            return [dict(r) for r in cur.fetchall()]

    def save_pet(self, account_id: int, pet_dict: Dict[str, Any]) -> None:
        with self._lock:
            now = int(time.time())
            pet_id = int(pet_dict.get("pet_id", pet_dict.get("id", 0)))
            lvl = int(pet_dict.get("level", 1))
            exp = int(pet_dict.get("exp", 0))
            skin_id = int(pet_dict.get("selected_skin_id", pet_dict.get("skin_id", 0)))
            skill_id = int(pet_dict.get("selected_skill_id", 0))
            self._get_conn().execute("""
                INSERT INTO pets (account_id, pet_id, level, exp, selected_skin_id, selected_skill_id, unlocked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id, pet_id) DO UPDATE SET
                    level = excluded.level,
                    exp = excluded.exp,
                    selected_skin_id = excluded.selected_skin_id,
                    selected_skill_id = excluded.selected_skill_id;
            """, (int(account_id), pet_id, lvl, exp, skin_id, skill_id, now))

    # -------------------------------------------------------------------------
    # Friends
    # -------------------------------------------------------------------------

    def get_friends(self, account_id: int) -> List[int]:
        with self._lock:
            cur = self._get_conn().cursor()
            cur.execute("SELECT friend_id FROM friends WHERE account_id = ?;", (int(account_id),))
            return [int(r["friend_id"]) for r in cur.fetchall()]

    def save_friend(self, account_id: int, friend_id: int, status: str = "accepted") -> None:
        with self._lock:
            now = int(time.time())
            self._get_conn().execute("""
                INSERT INTO friends (account_id, friend_id, status, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(account_id, friend_id) DO UPDATE SET
                    status = excluded.status;
            """, (int(account_id), int(friend_id), str(status), now))

    def delete_friend(self, account_id: int, friend_id: int) -> None:
        with self._lock:
            self._get_conn().execute("DELETE FROM friends WHERE account_id = ? AND friend_id = ?;", (int(account_id), int(friend_id)))

    # -------------------------------------------------------------------------
    # Mails
    # -------------------------------------------------------------------------

    def get_mails(self, account_id: int) -> List[Dict[str, Any]]:
        with self._lock:
            cur = self._get_conn().cursor()
            cur.execute("SELECT * FROM mails WHERE account_id = ? ORDER BY mail_id DESC;", (int(account_id),))
            out = []
            for r in cur.fetchall():
                d = dict(r)
                raw_rew = json.loads(d.pop("rewards_json", "[]"))
                d["is_read"] = bool(d["is_read"])
                d["is_claimed"] = bool(d["is_claimed"])

                coins = 0
                gems = 0
                items: List[Dict[str, Any]] = []

                if isinstance(raw_rew, dict):
                    coins = int(raw_rew.get("coins", 0))
                    gems = int(raw_rew.get("gems", 0))
                    raw_items = raw_rew.get("attachments", raw_rew.get("rewards", []))
                    if isinstance(raw_items, list):
                        items = raw_items
                elif isinstance(raw_rew, list):
                    for entry in raw_rew:
                        if isinstance(entry, dict):
                            if entry.get("type") == "currency":
                                coins = max(coins, int(entry.get("coins", 0)))
                                gems = max(gems, int(entry.get("gems", 0)))
                            else:
                                if "coins" in entry:
                                    coins = max(coins, int(entry["coins"]))
                                if "gems" in entry:
                                    gems = max(gems, int(entry["gems"]))
                                items.append(entry)
                        elif isinstance(entry, int):
                            items.append({"item_id": entry, "count": 1, "type": 1})

                d["attachments"] = items
                d["rewards"] = items
                d["coins"] = coins
                d["gems"] = gems
                d["sender_nick"] = d.get("sender_name", "India V1 System")
                d["receive_time"] = d.get("created_at", int(time.time()))
                d["status"] = 2 if d["is_claimed"] else (1 if d["is_read"] else 0)
                d["type"] = int(d.get("type", 1))
                d["source"] = int(d.get("source", 1))
                d["action_type"] = int(d.get("action_type", 0))
                out.append(d)
            return out

    def save_mail(self, account_id: int, mail_dict: Dict[str, Any]) -> None:
        with self._lock:
            mid = int(mail_dict.get("mail_id", int(time.time())))
            sender = str(mail_dict.get("sender_name") or mail_dict.get("sender_nick") or "India V1 System")
            title = str(mail_dict.get("title", "Notice"))
            content = str(mail_dict.get("content", ""))

            raw_att = mail_dict.get("attachments")
            if raw_att is None:
                raw_att = mail_dict.get("rewards", [])

            rewards_list: List[Dict[str, Any]] = []
            for a in raw_att:
                if isinstance(a, dict):
                    rewards_list.append(dict(a))
                elif isinstance(a, int):
                    rewards_list.append({"item_id": a, "count": 1, "type": 1})

            coins = max(0, int(mail_dict.get("coins", 0)))
            gems = max(0, int(mail_dict.get("gems", 0)))
            if coins > 0 or gems > 0:
                if rewards_list:
                    rewards_list[0]["coins"] = coins
                    rewards_list[0]["gems"] = gems
                else:
                    rewards_list.append({
                        "item_id": 0,
                        "count": 0,
                        "coins": coins,
                        "gems": gems,
                        "type": "currency",
                    })

            rewards_json = json.dumps(rewards_list)
            read = 1 if mail_dict.get("is_read") else 0
            claimed = 1 if mail_dict.get("is_claimed") else 0
            created = int(mail_dict.get("created_at") or mail_dict.get("receive_time") or int(time.time()))

            self._get_conn().execute("""
                INSERT INTO mails (mail_id, account_id, sender_name, title, content, rewards_json, is_read, is_claimed, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(mail_id) DO UPDATE SET
                    is_read = excluded.is_read,
                    is_claimed = excluded.is_claimed;
            """, (mid, int(account_id), sender, title, content, rewards_json, read, claimed, created))

    def update_mail(self, mail_id: int, is_read: Optional[bool] = None, is_claimed: Optional[bool] = None) -> None:
        with self._lock:
            updates = []
            params = []
            if is_read is not None:
                updates.append("is_read = ?")
                params.append(1 if is_read else 0)
            if is_claimed is not None:
                updates.append("is_claimed = ?")
                params.append(1 if is_claimed else 0)
            if not updates:
                return
            params.append(int(mail_id))
            sql = f"UPDATE mails SET {', '.join(updates)} WHERE mail_id = ?;"
            self._get_conn().execute(sql, tuple(params))

    def delete_mail(self, mail_id: int) -> None:
        with self._lock:
            self._get_conn().execute("DELETE FROM mails WHERE mail_id = ?;", (int(mail_id),))

    # -------------------------------------------------------------------------
    # Claims (Rewards, Attendances, Quests, Fire Pass, Bingo)
    # -------------------------------------------------------------------------

    def record_claim(
        self,
        account_id: int,
        claim_type: str,
        target_id: int,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Record that a player claimed a reward. Returns True if newly claimed, False if already claimed."""
        with self._lock:
            now = int(time.time())
            details_str = json.dumps(details or {})
            try:
                self._get_conn().execute("""
                    INSERT INTO user_claims (account_id, claim_type, target_id, details_json, claimed_at)
                    VALUES (?, ?, ?, ?, ?);
                """, (int(account_id), str(claim_type), int(target_id), details_str, now))
                return True
            except sqlite3.IntegrityError:
                return False

    def is_claimed(self, account_id: int, claim_type: str, target_id: int) -> bool:
        with self._lock:
            cur = self._get_conn().cursor()
            cur.execute("""
                SELECT 1 FROM user_claims
                WHERE account_id = ? AND claim_type = ? AND target_id = ?;
            """, (int(account_id), str(claim_type), int(target_id)))
            return cur.fetchone() is not None

    def get_claims(self, account_id: int, claim_type: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            cur = self._get_conn().cursor()
            if claim_type:
                cur.execute("""
                    SELECT * FROM user_claims
                    WHERE account_id = ? AND claim_type = ?
                    ORDER BY id ASC;
                """, (int(account_id), str(claim_type)))
            else:
                cur.execute("""
                    SELECT * FROM user_claims
                    WHERE account_id = ?
                    ORDER BY id ASC;
                """, (int(account_id),))
            out = []
            for r in cur.fetchall():
                d = dict(r)
                d["details"] = json.loads(d.pop("details_json", "{}"))
                out.append(d)
            return out

    # -------------------------------------------------------------------------
    # Activity Runtime State Persistence (Attendance, Bingo Grid, Quests)
    # -------------------------------------------------------------------------

    def get_activity_state(self, account_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            cur = self._get_conn().cursor()
            cur.execute("SELECT state_json FROM activity_states WHERE account_id = ?;", (int(account_id),))
            row = cur.fetchone()
            if not row:
                return None
            try:
                return json.loads(row["state_json"])
            except Exception:
                return None

    def save_activity_state(self, account_id: int, state_dict: Dict[str, Any]) -> None:
        with self._lock:
            now = int(time.time())
            blob = json.dumps(state_dict)
            self._get_conn().execute("""
                INSERT INTO activity_states (account_id, state_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(account_id) DO UPDATE SET
                    state_json = excluded.state_json,
                    updated_at = excluded.updated_at;
            """, (int(account_id), blob, now))

    # -------------------------------------------------------------------------
    # Luck Royale / Gacha State Persistence
    # -------------------------------------------------------------------------

    def get_all_gacha_states(self, account_id: int) -> Dict[int, Dict[str, Any]]:
        with self._lock:
            cur = self._get_conn().cursor()
            cur.execute("SELECT chest_id, state_json FROM gacha_states WHERE account_id = ?;", (int(account_id),))
            rows = cur.fetchall()
            res: Dict[int, Dict[str, Any]] = {}
            for r in rows:
                try:
                    res[int(r["chest_id"])] = json.loads(r["state_json"])
                except Exception:
                    pass
            return res

    def save_gacha_state(self, account_id: int, chest_id: int, state_dict: Dict[str, Any]) -> None:
        with self._lock:
            now = int(time.time())
            blob = json.dumps(state_dict)
            self._get_conn().execute("""
                INSERT INTO gacha_states (account_id, chest_id, state_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(account_id, chest_id) DO UPDATE SET
                    state_json = excluded.state_json,
                    updated_at = excluded.updated_at;
            """, (int(account_id), int(chest_id), blob, now))

    def record_gacha_transaction(
        self,
        account_id: int,
        chest_id: int,
        gacha_type: int,
        consume_type: int,
        cost_type: int,
        cost_amount: int,
        reward_list: Sequence[Dict[str, Any]],
        lucky_before: int = 0,
        lucky_after: int = 0,
        has_big_reward: bool = False,
        timestamp: Optional[int] = None,
    ) -> int:
        with self._lock:
            ts = int(timestamp or time.time())
            reward_json = json.dumps(list(reward_list))
            cur = self._get_conn().cursor()
            cur.execute("""
                INSERT INTO gacha_transactions (
                    account_id, chest_id, gacha_type, consume_type,
                    cost_type, cost_amount, reward_list_json,
                    lucky_before, lucky_after, has_big_reward, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                int(account_id), int(chest_id), int(gacha_type), int(consume_type),
                int(cost_type), int(cost_amount), reward_json,
                int(lucky_before), int(lucky_after), 1 if has_big_reward else 0, ts
            ))
            return cur.lastrowid or 0

    def get_gacha_transactions(
        self,
        account_id: Optional[int] = None,
        chest_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            cur = self._get_conn().cursor()
            query = "SELECT * FROM gacha_transactions WHERE 1=1"
            params: List[Any] = []
            if account_id is not None:
                query += " AND account_id = ?"
                params.append(int(account_id))
            if chest_id is not None:
                query += " AND chest_id = ?"
                params.append(int(chest_id))
            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?;"
            params.extend([max(1, int(limit)), max(0, int(offset))])
            cur.execute(query, params)
            rows = cur.fetchall()
            results: List[Dict[str, Any]] = []
            for r in rows:
                results.append({
                    "trans_id": r["trans_id"],
                    "account_id": r["account_id"],
                    "chest_id": r["chest_id"],
                    "gacha_type": r["gacha_type"],
                    "consume_type": r["consume_type"],
                    "cost_type": r["cost_type"],
                    "cost_amount": r["cost_amount"],
                    "reward_list": json.loads(r["reward_list_json"]) if r["reward_list_json"] else [],
                    "lucky_before": r["lucky_before"],
                    "lucky_after": r["lucky_after"],
                    "has_big_reward": bool(r["has_big_reward"]),
                    "timestamp": r["timestamp"],
                })
            return results

    def record_special_exchange(
        self,
        account_id: int,
        forge_tab_id: int,
        item_id: int,
        count: int = 1,
        consumed_items: Optional[Sequence[Dict[str, Any]]] = None,
        timestamp: Optional[int] = None,
    ) -> int:
        with self._lock:
            ts = int(timestamp or time.time())
            consumed_json = json.dumps(list(consumed_items or []))
            cur = self._get_conn().cursor()
            cur.execute("""
                INSERT INTO gacha_special_exchanges (
                    account_id, forge_tab_id, item_id, count, consumed_json, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?);
            """, (int(account_id), int(forge_tab_id), int(item_id), int(count), consumed_json, ts))
            return cur.lastrowid or 0

    def get_special_exchange_purchases(self, account_id: int) -> Dict[Tuple[int, int], int]:
        with self._lock:
            cur = self._get_conn().cursor()
            cur.execute("""
                SELECT forge_tab_id, item_id, SUM(count) as total_count
                FROM gacha_special_exchanges
                WHERE account_id = ?
                GROUP BY forge_tab_id, item_id;
            """, (int(account_id),))
            rows = cur.fetchall()
            return {(int(r["forge_tab_id"]), int(r["item_id"])): int(r["total_count"]) for r in rows}

    # -------------------------------------------------------------------------
    # Audit Log
    # -------------------------------------------------------------------------

    def log_action(
        self,
        account_id: int,
        action_type: str,
        summary: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        with self._lock:
            now = int(time.time())
            payload_str = json.dumps(payload or {})
            self._get_conn().execute("""
                INSERT INTO audit_log (account_id, action_type, summary, payload_json, timestamp)
                VALUES (?, ?, ?, ?, ?);
            """, (int(account_id), str(action_type), str(summary), payload_str, now))

    def get_audit_logs(
        self,
        account_id: Optional[int] = None,
        action_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            cur = self._get_conn().cursor()
            query = "SELECT * FROM audit_log"
            params: List[Any] = []
            clauses = []
            if account_id:
                clauses.append("account_id = ?")
                params.append(int(account_id))
            if action_type:
                clauses.append("action_type = ?")
                params.append(str(action_type))
            if clauses:
                query += " WHERE " + " AND ".join(clauses)
            query += " ORDER BY id DESC LIMIT ?;"
            params.append(int(limit))

            cur.execute(query, tuple(params))
            out = []
            for r in cur.fetchall():
                d = dict(r)
                d["payload"] = json.loads(d.pop("payload_json", "{}"))
                out.append(d)
            return out

    # -------------------------------------------------------------------------
    # Multi-Player Account Discovery & Registration Queries
    # -------------------------------------------------------------------------

    def get_all_account_ids(self) -> List[int]:
        """Return list of all registered account IDs ordered ascending."""
        with self._lock:
            cur = self._get_conn().cursor()
            cur.execute("SELECT account_id FROM accounts ORDER BY account_id ASC;")
            return [int(r["account_id"]) for r in cur.fetchall()]

    def get_next_account_id(self) -> int:
        """Allocate next monotonically increasing dynamic account_id (>= 10001)."""
        with self._lock:
            cur = self._get_conn().cursor()
            cur.execute("SELECT MAX(account_id) AS max_id FROM accounts;")
            row = cur.fetchone()
            max_id = int(row["max_id"]) if (row and row["max_id"] is not None) else 10000
            return max(max_id + 1, 10001)

    def find_account_by_nickname(self, nickname: str) -> Optional[Dict[str, Any]]:
        """Case-insensitive exact nickname search in accounts store."""
        if not nickname:
            return None
        with self._lock:
            cur = self._get_conn().cursor()
            cur.execute("SELECT account_id FROM accounts WHERE LOWER(nickname) = LOWER(?);", (str(nickname).strip(),))
            row = cur.fetchone()
            if not row:
                return None
            return self.get_profile(int(row["account_id"]))

    def find_account_by_open_id(self, open_id: str) -> Optional[Dict[str, Any]]:
        """Lookup account by platform open_id stored in profile_data_json."""
        if not open_id:
            return None
        with self._lock:
            cur = self._get_conn().cursor()
            cur.execute("SELECT account_id FROM accounts WHERE json_extract(profile_data_json, '$.open_id') = ?;", (str(open_id),))
            row = cur.fetchone()
            if not row:
                return None
            return self.get_profile(int(row["account_id"]))

    def find_account_by_device_id(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Lookup account by client device_id stored in profile_data_json."""
        if not device_id:
            return None
        with self._lock:
            cur = self._get_conn().cursor()
            cur.execute("SELECT account_id FROM accounts WHERE json_extract(profile_data_json, '$.device_id') = ?;", (str(device_id),))
            row = cur.fetchone()
            if not row:
                return None
            return self.get_profile(int(row["account_id"]))

    def find_account_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Lookup account by active session token stored in profile_data_json."""
        if not token:
            return None
        with self._lock:
            cur = self._get_conn().cursor()
            cur.execute("SELECT account_id FROM accounts WHERE json_extract(profile_data_json, '$.token') = ?;", (str(token),))
            row = cur.fetchone()
            if not row:
                return None
            return self.get_profile(int(row["account_id"]))

    def search_accounts_by_nickname(self, query_str: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Fuzzy search accounts by nickname prefix or substring."""
        if not query_str:
            return []
        with self._lock:
            cur = self._get_conn().cursor()
            cur.execute(
                "SELECT account_id FROM accounts WHERE LOWER(nickname) LIKE LOWER(?) ORDER BY level DESC LIMIT ?;",
                (f"%{query_str}%", int(limit)),
            )
            out: List[Dict[str, Any]] = []
            for r in cur.fetchall():
                prof = self.get_profile(int(r["account_id"]))
                if prof:
                    out.append(prof)
            return out

    def delete_account(self, account_id: int) -> bool:
        """Purge account and related records from database."""
        with self._lock:
            conn = self._get_conn()
            aid = int(account_id)
            conn.execute("BEGIN IMMEDIATE;")
            try:
                conn.execute("DELETE FROM accounts WHERE account_id = ?;", (aid,))
                conn.execute("DELETE FROM inventory WHERE account_id = ?;", (aid,))
                conn.execute("DELETE FROM characters WHERE account_id = ?;", (aid,))
                conn.execute("DELETE FROM pets WHERE account_id = ?;", (aid,))
                conn.execute("DELETE FROM mails WHERE account_id = ?;", (aid,))
                conn.execute("DELETE FROM friends WHERE account_id = ? OR friend_id = ?;", (aid, aid))
                conn.execute("DELETE FROM user_claims WHERE account_id = ?;", (aid,))
                conn.execute("DELETE FROM activity_states WHERE account_id = ?;", (aid,))
                conn.execute("DELETE FROM gacha_states WHERE account_id = ?;", (aid,))
                conn.execute("COMMIT;")
                return True
            except Exception:
                conn.execute("ROLLBACK;")
                return False


# Global singleton database instance
db = Database()
