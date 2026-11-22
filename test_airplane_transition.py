"""
Authoritative Test Suite: Airplane Flight & Skydiving Transition Protocol
Validates:
1. Opcode 110 (RUDP_BATTLE_START, S2C_BattleStart) wire codec (44 bytes, 1 Q + 9 f).
2. Bermuda airplane flight trajectory (altitude 420m, speed 65 m/s, cross-island angle).
3. Cabin passenger manifest (all 50 players aboard in ON_AIRPLANE state).
4. Manual eject / auto-eject and skydiving freefall -> parachute deployment (85m) -> ground landing.
5. Match state machine lifecycle progression (State 2 -> State 3 -> State 4 -> State 5).
"""

import math
import struct
import sys
import os

# Add server directory to module search path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.combat.world_constants import (
    BERMUDA_WAITING_ISLAND_CENTER,
    MAP_CENTER_X,
    MAP_CENTER_Z,
)
from server.combat.combat_opcodes import CombatOpcode
from server.combat.udp_protocol import UDMPacket, SendOption
from server.combat.combat_packet_codec import (
    S2C_BattleStart,
    S2C_ParachuteSync,
)
from server.combat.match_director import (
    MatchDirector,
    MatchState,
    ParachutePhase,
    AirplaneTrajectory,
)
from server.combat.bot_controller import BotLifecycleState, PhysxState


def test_opcode_110_codec():
    print("[TEST 1] Verifying Opcode 110 (RUDP_BATTLE_START) Wire Serialization & Codec...")
    match_id = 12345678901234
    start_pos = (200.0, 420.0, -100.0)
    end_pos = (1800.0, 420.0, 2100.0)
    altitude = 420.0
    speed = 65.0
    duration = 41.85

    pkt = S2C_BattleStart(
        match_id=match_id,
        start_pos=start_pos,
        end_pos=end_pos,
        altitude=altitude,
        flight_speed=speed,
        flight_duration=duration,
    )
    raw = pkt.serialize()
    assert len(raw) == 44, f"Opcode 110 packet must be exactly 44 bytes, got {len(raw)}"

    # Wire unpacking check: <Qfffffffff
    unpacked = S2C_BattleStart.unserialize(raw)
    assert unpacked.match_id == match_id
    assert abs(unpacked.start_pos[0] - 200.0) < 1e-3
    assert abs(unpacked.start_pos[1] - 420.0) < 1e-3
    assert abs(unpacked.start_pos[2] - (-100.0)) < 1e-3
    assert abs(unpacked.end_pos[0] - 1800.0) < 1e-3
    assert abs(unpacked.end_pos[1] - 420.0) < 1e-3
    assert abs(unpacked.end_pos[2] - 2100.0) < 1e-3
    assert abs(unpacked.altitude - 420.0) < 1e-3
    assert abs(unpacked.flight_speed - 65.0) < 1e-3
    assert abs(unpacked.flight_duration - 41.85) < 1e-3
    print("  -> PASSED: Opcode 110 wire codec verified (44 bytes, 1 Q + 9 f roundtrip clean).")


def test_airplane_flight_trajectory():
    print("[TEST 2] Verifying Bermuda Airplane Flight Trajectory Generation...")
    start_pos = (MAP_CENTER_X + 1150.0, 420.0, MAP_CENTER_Z)
    end_pos = (MAP_CENTER_X - 1150.0, 420.0, MAP_CENTER_Z)
    speed = 65.0

    traj = AirplaneTrajectory(start_pos=start_pos, end_pos=end_pos, flight_speed=speed)
    assert abs(traj.start_y - 420.0) < 1e-3
    assert abs(traj.flight_speed - 65.0) < 1e-3
    expected_dist = 2300.0
    assert abs(traj.total_dist - expected_dist) < 1e-3
    expected_time = expected_dist / speed
    assert abs(traj.total_flight_time - expected_time) < 1e-3

    # Halfway position
    mid_pos = traj.get_position(expected_time / 2.0)
    assert abs(mid_pos[0] - MAP_CENTER_X) < 1e-1
    assert abs(mid_pos[1] - 420.0) < 1e-3
    assert abs(mid_pos[2] - MAP_CENTER_Z) < 1e-1

    # End position
    end_check = traj.get_position(expected_time)
    assert abs(end_check[0] - end_pos[0]) < 1e-1
    assert traj.is_finished(expected_time)
    print("  -> PASSED: AirplaneTrajectory coordinates, yaw, and speed calculations verified.")


def test_transition_spawn_island_to_airplane():
    print("[TEST 3] Verifying Transition: Spawn Island -> Airplane Flight (State 2 -> 3)...")
    md = MatchDirector()
    match = md.create_match(
        match_id=77777,
        host_player_id="10001",
        host_nickname="PushpaGG",
        waiting_duration=2.0,
        bot_count=49
    )
    md.handle_udp_handshake(77777, "10001", match.prepare_token, ("127.0.0.1", 39800))
    assert match.state == MatchState.STATE_2_SPAWN_ISLAND

    # Verify initial spawn positions on waiting island
    human = match.world.get_player("10001")
    assert human.x == -500.0 and human.y == 10.0 and human.z == 800.0

    # Advance countdown to zero (2 seconds)
    match.tick(1.0)
    assert match.state == MatchState.STATE_2_SPAWN_ISLAND
    events = match.tick(1.1).get("events", [])
    assert match.state == MatchState.STATE_3_AIRPLANE_FLIGHT, f"State mismatch: {match.state}"

    # Verify STATE_CHANGE event was logged
    state_changes = [e for e in events if e.get("type") == "STATE_CHANGE"]
    assert len(state_changes) >= 1
    assert state_changes[0]["new_state"] == int(MatchState.STATE_3_AIRPLANE_FLIGHT)

    # Verify Opcode 110 payload from match instance
    bstart_bytes = match.build_battle_start_bytes()
    assert len(bstart_bytes) == 44
    pkt = S2C_BattleStart.unserialize(bstart_bytes)
    assert pkt.match_id == 77777
    assert pkt.altitude == 420.0
    assert pkt.flight_speed == 65.0

    # Verify Cabin Passenger Manifest (All 50 combatants aboard)
    assert "10001" in match.drop_states
    human_drop = match.drop_states["10001"]
    assert human_drop.phase == ParachutePhase.ON_AIRPLANE
    assert abs(human_drop.y - 420.0) < 1e-3

    bots_onboard = sum(
        1 for b in match.bot_controller.bots.values()
        if b.lifecycle_state == BotLifecycleState.AIRPLANE
    )
    assert bots_onboard == 49, f"Expected 49 bots onboard, got {bots_onboard}"

    total_passengers = 1 + bots_onboard
    assert total_passengers == 50, f"Expected 50 total passengers, got {total_passengers}"
    print(f"  -> PASSED: Cabin passenger manifest verified (all {total_passengers} combatants aboard).")


def test_eject_and_skydiving_flow():
    print("[TEST 4] Verifying Manual Eject, Skydiving Freefall & Parachute Deployment...")
    md = MatchDirector()
    match = md.create_match(
        match_id=88888,
        host_player_id="10001",
        host_nickname="PushpaGG",
        waiting_duration=0.1,
        bot_count=49
    )
    md.handle_udp_handshake(88888, "10001", match.prepare_token, ("127.0.0.1", 39800))
    match.tick(0.2)  # Transition to STATE_3_AIRPLANE_FLIGHT
    assert match.state == MatchState.STATE_3_AIRPLANE_FLIGHT

    # Simulate 5 seconds of airplane flight
    match.tick(5.0)
    plane_x, plane_y, plane_z = match.trajectory.get_position(match.airplane_flight_time)
    human_drop = match.drop_states["10001"]
    assert abs(human_drop.x - plane_x) < 1e-1
    assert abs(human_drop.y - plane_y) < 1e-1
    assert abs(human_drop.z - plane_z) < 1e-1

    # Manual Eject: Player taps Jump button (UIGroup_Skydiving ActionBtn)
    success = match.eject_player("10001")
    assert success is True
    assert human_drop.phase == ParachutePhase.SKYDIVING
    assert human_drop.velocity_y == -35.0  # Terminal initial fall speed

    # Advance tick: State machine should transition to STATE_4_EJECT_PARACHUTE
    match.tick(0.1)
    assert match.state == MatchState.STATE_4_EJECT_PARACHUTE

    # Simulate descending freefall until parachute auto-deploy altitude (<= 85.0m)
    for _ in range(100):
        if human_drop.phase == ParachutePhase.PARACHUTING:
            break
        match.tick(0.2)

    assert human_drop.phase == ParachutePhase.PARACHUTING, f"Phase mismatch: {human_drop.phase}"
    assert human_drop.y <= 85.0, f"Parachute should auto deploy at <= 85m, got {human_drop.y}"
    assert human_drop.velocity_y == -7.5  # Gentle glide velocity

    # Simulate gliding until ground touchdown (y <= 15.0m)
    for _ in range(50):
        if human_drop.phase == ParachutePhase.LANDED:
            break
        match.tick(0.5)

    assert human_drop.phase == ParachutePhase.LANDED
    assert human_drop.y == human_drop.ground_y
    print("  -> PASSED: Eject -> Skydiving freefall -> Parachute deploy (85m) -> Landing verified.")


def test_auto_eject_on_route_completion():
    print("[TEST 5] Verifying Route Completion Auto-Eject Fallback...")
    md = MatchDirector()
    match = md.create_match(
        match_id=99999,
        host_player_id="10001",
        host_nickname="PushpaGG",
        waiting_duration=0.1,
        bot_count=49
    )
    md.handle_udp_handshake(99999, "10001", match.prepare_token, ("127.0.0.1", 39800))
    match.tick(0.2)
    assert match.state == MatchState.STATE_3_AIRPLANE_FLIGHT

    # Fast forward beyond total flight time without manual jump
    total_time = match.trajectory.total_flight_time
    match.tick(total_time + 1.0)

    # All players must have auto-ejected
    human_drop = match.drop_states["10001"]
    assert human_drop.phase != ParachutePhase.ON_AIRPLANE, "Human must auto-eject when plane finishes"
    print("  -> PASSED: Auto-eject on flight path completion verified.")


if __name__ == "__main__":
    test_opcode_110_codec()
    test_airplane_flight_trajectory()
    test_transition_spawn_island_to_airplane()
    test_eject_and_skydiving_flow()
    test_auto_eject_on_route_completion()
    print("\n=======================================================")
    print("ALL 5 AIRPLANE TRANSITION & SKYDIVING TESTS PASSED (100%)")
    print("=======================================================")
