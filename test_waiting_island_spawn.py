"""
Verification Test for Bermuda Waiting Island Spawns, Entity Placement, and Opcode 1014 Sync.
"""

import math
import struct
import sys
import os

# Ensure server package is discoverable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.combat.world_constants import (
    BERMUDA_LANDMARKS,
    BERMUDA_WAITING_ISLAND_CENTER,
    BERMUDA_WAITING_ISLAND_RADIUS,
    BERMUDA_WAITING_ISLAND_SPAWN_RADIUS,
)
from server.combat.world_engine import WorldEngine, CombatPlayer
from server.combat.loot_spawner import LootSpawner
from server.combat.match_director import MatchDirector, MatchState, global_match_director
from server.combat.combat_packet_codec import (
    PlayerPosItem,
    UDP_PlayerPositionBatch,
    UDP_PlayerPositionOnly,
    S2C_SyncSceneInfo,
)


def test_waiting_island_constants():
    print("[TEST 1] Verifying Bermuda Waiting Island Constants...")
    assert BERMUDA_WAITING_ISLAND_CENTER == (-500.0, 10.0, 800.0), f"Center mismatch: {BERMUDA_WAITING_ISLAND_CENTER}"
    assert BERMUDA_WAITING_ISLAND_RADIUS == 60.0, f"Radius mismatch: {BERMUDA_WAITING_ISLAND_RADIUS}"
    assert BERMUDA_WAITING_ISLAND_SPAWN_RADIUS == 25.0, f"Spawn radius mismatch: {BERMUDA_WAITING_ISLAND_SPAWN_RADIUS}"
    assert "Waiting_Island" in BERMUDA_LANDMARKS, "Waiting_Island missing from BERMUDA_LANDMARKS"
    wi = BERMUDA_LANDMARKS["Waiting_Island"]
    assert wi["x"] == -500.0 and wi["y"] == 10.0 and wi["z"] == 800.0
    print("  -> PASSED: Waiting Island constants verified.")


def test_world_engine_waiting_island():
    print("[TEST 2] Verifying WorldEngine Player Registration on Waiting Island...")
    world = WorldEngine()
    
    # 1. Human player registration without explicit coords -> should land on Waiting Island
    human = world.register_player(player_id="10001", nickname="PushpaGG", is_bot=False)
    assert human.entity_id == 1, f"Expected entity_id 1, got {human.entity_id}"
    assert abs(human.x - (-500.0)) <= 5.0, f"Human x={human.x} not near -500.0"
    assert human.y == 10.0, f"Human y={human.y} not 10.0"
    assert abs(human.z - 800.0) <= 5.0, f"Human z={human.z} not near 800.0"
    assert human.hp == 200.0
    assert human.is_alive is True
    assert human.weapons["melee"] is not None
    print(f"  -> Human registered at ({human.x:.2f}, {human.y:.2f}, {human.z:.2f})")

    # 2. Verify alias lookup
    assert world.get_player("10001") is human
    assert world.get_player("1") is human
    assert world.get_player(1) is human

    # 3. Bot registration
    bot = world.register_player(player_id="2", nickname="Bot_Kelly", is_bot=True, entity_id=2)
    assert bot.entity_id == 2
    assert bot.y == 10.0
    dist_bot = math.hypot(bot.x - (-500.0), bot.z - 800.0)
    assert dist_bot <= 30.0, f"Bot distance from center {dist_bot} > 30.0"
    print(f"  -> Bot registered at ({bot.x:.2f}, {bot.y:.2f}, {bot.z:.2f}), dist={dist_bot:.2f}m")

    # 4. Position update
    world.update_player_pos("1", -499.5, 10.0, 801.2, yaw=45.0)
    assert human.x == -499.5 and human.z == 801.2 and human.yaw == 45.0
    print("  -> PASSED: WorldEngine Waiting Island placement verified.")


def test_loot_spawner_waiting_island():
    print("[TEST 3] Verifying LootSpawner on Waiting Island...")
    spawner = LootSpawner(seed=123)
    count = spawner.populate_waiting_island_loot()
    assert count > 0, "No loot spawned on Waiting Island"
    
    # Query items near Waiting Island center
    items = spawner.get_items_near(-500.0, 800.0, radius=50.0)
    assert len(items) > 0, "No items found in Waiting Island radius"
    print(f"  -> Spawned {count} Waiting Island practice items ({len(items)} within 50m radius).")
    
    # Check item types
    names = [i.name for i in items]
    assert any("Pan" in n or "Bat" in n or "Katana" in n for n in names), f"No melee weapons: {names}"
    assert any("M4A1" in n or "MP40" in n or "M1014" in n for n in names), f"No firearms: {names}"
    print("  -> PASSED: Waiting Island loot verified.")


def test_match_director_waiting_island_lifecycle():
    print("[TEST 4] Verifying MatchDirector Waiting Island Lifecycle & Opcode 1014 Batch...")
    director = MatchDirector()
    match = director.create_match(
        match_id=99001,
        map_id=1,
        game_mode=1,
        match_mode=1,
        host_player_id="10001",
        host_nickname="PushpaGG",
        waiting_duration=60.0,
        bot_count=49
    )

    # 1. Initial State
    assert match.state == MatchState.STATE_0_MATCHMAKING
    h_player = match.world.get_player("10001")
    assert h_player is not None
    assert abs(h_player.x - (-500.0)) <= 5.0
    assert h_player.y == 10.0
    assert abs(h_player.z - 800.0) <= 5.0

    # 2. Transition to State 2 (Spawn Island)
    match.transition_to(MatchState.STATE_2_SPAWN_ISLAND)
    assert match.state == MatchState.STATE_2_SPAWN_ISLAND
    assert match.world.alive_player_count == 50, f"Expected 50 alive players, got {match.world.alive_player_count}"

    # 3. Verify Opcode 116 Scene Info
    scene_bytes = match.build_sync_scene_info_bytes()
    assert len(scene_bytes) == 36, f"Expected 36 bytes for Opcode 116, got {len(scene_bytes)}"
    scene_unpacked = S2C_SyncSceneInfo.unserialize(scene_bytes)
    assert scene_unpacked.spawn_island_x == -500.0
    assert scene_unpacked.spawn_island_y == 10.0
    assert scene_unpacked.spawn_island_z == 800.0
    assert scene_unpacked.spawn_island_radius == 60.0
    assert scene_unpacked.alive_players == 50
    print(f"  -> Opcode 116 S2C_SyncSceneInfo verified: {scene_unpacked}")

    # 4. Verify Opcode 1014 Initial Waiting Island Batch
    init_batch_bytes = match.build_waiting_island_position_batch_bytes()
    assert len(init_batch_bytes) > 0
    batch_unpacked = UDP_PlayerPositionBatch.unserialize(init_batch_bytes)
    assert len(batch_unpacked.players) == 50, f"Expected 50 players in batch, got {len(batch_unpacked.players)}"
    
    # Entity 1 must be human at center
    p1 = batch_unpacked.players[0]
    assert p1.player_id == 1, f"Expected entity 1, got {p1.player_id}"
    assert p1.x == -500.0 and p1.y == 10.0 and p1.z == 800.0
    print(f"  -> Entity 1 (Human) on Waiting Island: ({p1.x}, {p1.y}, {p1.z})")

    # Entities 2..50 must all be within Waiting Island radius
    for idx, p in enumerate(batch_unpacked.players[1:], start=2):
        assert p.player_id == idx, f"Expected entity {idx}, got {p.player_id}"
        assert 10.0 <= p.y <= 10.5, f"Entity {p.player_id} y={p.y} outside pedestal range [10.0, 10.5]"
        dist = math.hypot(p.x - (-500.0), p.z - 800.0)
        assert dist <= 55.0, f"Entity {p.player_id} dist={dist:.2f} > 55.0"

    print(f"  -> All 50 entities placed within Waiting Island radius.")

    # 5. Verify MatchInstance.tick() emits PLAYER_POSITION_SYNC
    tick_res = match.tick(0.1)
    ev_types = [e.get("type") for e in tick_res.get("events", [])]
    assert "PLAYER_POSITION_SYNC" in ev_types or "INITIAL_SPAWN_POSITION" in ev_types, f"Events: {ev_types}"
    print(f"  -> Tick emitted events: {ev_types}")

    # 6. Verify live player position batch bytes
    live_batch_bytes = match.build_player_position_batch_bytes()
    live_batch = UDP_PlayerPositionBatch.unserialize(live_batch_bytes)
    assert len(live_batch.players) == 50
    assert live_batch.players[0].player_id == 1
    print("  -> PASSED: MatchDirector Waiting Island Lifecycle verified.")


if __name__ == "__main__":
    print("=== BEGIN WAITING ISLAND SPATIAL & POSITION VERIFICATION ===")
    test_waiting_island_constants()
    test_world_engine_waiting_island()
    test_loot_spawner_waiting_island()
    test_match_director_waiting_island_lifecycle()
    print("=== ALL 4 VERIFICATION SUITES PASSED SUCCESSFULLY ===")
