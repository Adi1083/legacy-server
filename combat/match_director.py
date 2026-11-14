"""
Authoritative Match Lifecycle Director for Free Fire 1.39.
Orchestrates the authentic 7-state battle royale match flow:
  State 0: Matchmaking Queue & Handshake Token Prep (MatchmakingSussNtf)
  State 1: Client UDP Connect & Session Handshake
  State 2: Spawn Island (60-second waiting countdown, character synchronization)
  State 3: Airplane Flight Path Sequence across Bermuda Map
  State 4: Eject & Parachute Sequence (Skydiving -> Canopy Deploy -> Ground Landing)
  State 5: Active Combat & Safe Zone Looting Loop (coordinated with WorldEngine & BotController)
  State 6: Game Over / Booyah! Screen & Rank Point Settlement
"""

from __future__ import annotations

import enum
import math
import random
import time
from typing import Dict, Any, List, Optional, Tuple, Callable

from .world_constants import (
    BERMUDA_LANDMARKS,
    MAP_MIN_X, MAP_MAX_X, MAP_MIN_Z, MAP_MAX_Z, MAP_CENTER_X, MAP_CENTER_Z
)
from .world_engine import WorldEngine, CombatPlayer
from .bot_controller import BotController, Vector3, PhysxState, PhysxPose, BotLifecycleState
from .combat_packet_codec import (
    S2C_SyncSceneInfo,
    S2C_BattleStart,
    S2C_ParachuteSync,
    RUDP_SafeZoneChange,
)


class MatchState(enum.IntEnum):
    """Authentic Free Fire 1.39 Match Lifecycle States."""
    STATE_0_MATCHMAKING = 0      # Queue, matchmaking radar, MatchmakingSussNtf handoff
    STATE_1_UDP_CONNECT = 1      # UDP socket connect & auth token handshake
    STATE_2_SPAWN_ISLAND = 2     # Spawn Island pre-match area (60s countdown timer)
    STATE_3_AIRPLANE_FLIGHT = 3  # Cargo plane flying across Bermuda at high altitude
    STATE_4_EJECT_PARACHUTE = 4  # Skydiving free-fall -> Parachute open -> Landing
    STATE_5_COMBAT_LOOTING = 5   # Active battle royale, looting, safe zone shrinks
    STATE_6_GAME_OVER = 6        # Victory Booyah! / Defeat, stats, rank point settlement


class ParachutePhase(enum.IntEnum):
    """Sub-phases of the drop sequence."""
    ON_AIRPLANE = 0      # Sitting in the transport plane
    SKYDIVING = 1        # High-speed free-fall (skydive animation, trail effects)
    PARACHUTING = 2     # Parachute canopy deployed, gliding down
    LANDED = 3          # On ground, normal character controller enabled


class AirplaneTrajectory:
    """Calculates authoritative straight flight trajectory across Bermuda."""

    def __init__(self,
                 start_pos: Tuple[float, float, float],
                 end_pos: Tuple[float, float, float],
                 flight_speed: float = 65.0):
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.start_x, self.start_y, self.start_z = start_pos
        self.end_x, self.end_y, self.end_z = end_pos
        self.flight_speed = flight_speed
        
        # Calculate total vector and distance
        self.dx = self.end_x - self.start_x
        self.dz = self.end_z - self.start_z
        self.total_dist = math.hypot(self.dx, self.dz)
        self.total_flight_time = self.total_dist / max(flight_speed, 1.0)
        self.yaw = math.degrees(math.atan2(self.dx, self.dz))

    def get_position(self, elapsed_flight_time: float) -> Tuple[float, float, float]:
        """Get plane coordinates at a specific elapsed flight time."""
        progress = min(max(elapsed_flight_time / max(self.total_flight_time, 0.001), 0.0), 1.0)
        x = self.start_x + self.dx * progress
        y = self.start_y  # Plane maintains constant altitude
        z = self.start_z + self.dz * progress
        return (x, y, z)

    def is_finished(self, elapsed_flight_time: float) -> bool:
        """Whether the plane has crossed the entire island boundary."""
        return elapsed_flight_time >= self.total_flight_time


class PlayerDropState:
    """Tracks individual player trajectory during drop and parachute sequence."""

    def __init__(self, player_id: str, is_bot: bool = False):
        self.player_id: str = player_id
        self.is_bot: bool = is_bot
        self.phase: ParachutePhase = ParachutePhase.ON_AIRPLANE
        self.eject_time: float = 0.0
        
        # Position and drop physics
        self.x: float = 0.0
        self.y: float = 420.0  # Airplane altitude
        self.z: float = 0.0
        self.velocity_y: float = 0.0
        self.forward_speed: float = 20.0
        self.yaw: float = 0.0
        
        # Ground target elevation
        self.ground_y: float = 15.0
        self.target_landmark: Optional[str] = None
        self.target_x: float = 0.0
        self.target_z: float = 0.0
        
        # Parachute deploy parameters
        self.auto_deploy_altitude: float = 85.0
        self.manual_deploy_allowed: bool = True
        self.deploy_time: float = 0.0
        self.landed_time: float = 0.0


class MatchInstance:
    """An authoritative Free Fire match instance running on the game server."""

    def __init__(self,
                 match_id: int,
                 map_id: int = 1,
                 game_mode: int = 1,
                 match_mode: int = 1,
                 server_addr: str = "10.0.2.2:39800",
                 waiting_duration: float = 60.0,
                 bot_count: int = 2,
                 prepare_token: Optional[str] = None,
                 secret: Optional[str] = None):
        self.match_id: int = match_id
        self.map_id: int = map_id
        self.game_mode: int = game_mode
        self.match_mode: int = match_mode
        self.server_addr: str = server_addr
        
        # Match Lifecycle State
        self.state: MatchState = MatchState.STATE_0_MATCHMAKING
        self.state_start_time: float = time.time()
        self.elapsed_in_state: float = 0.0
        self.match_total_elapsed: float = 0.0
        
        # Durations & Parameters
        self.waiting_duration: float = waiting_duration  # 60s Spawn Island countdown
        self.airplane_flight_time: float = 0.0
        self.bot_count: int = bot_count
        
        # Security & Auth Tokens
        import hashlib
        self.prepare_token: str = prepare_token or f"prep_{match_id}_{int(time.time())}_{hashlib.md5(f'{time.time()}'.encode()).hexdigest()[:8]}"
        self.secret: str = secret or f"barbosa_sec_{match_id}_{hashlib.md5(f'{time.time()}'.encode()).hexdigest()[:8]}"
        self.connected_tokens: Dict[str, str] = {}  # player_id -> token
        self.client_endpoints: Dict[str, Tuple[str, int]] = {}  # player_id -> (ip, port)
        self.client_session_keys: Dict[str, int] = {}  # player_id -> session_key
        
        # Players & Drop States
        self.human_player_ids: List[str] = []
        self.drop_states: Dict[str, PlayerDropState] = {}
        
        # Spawn Island Definition
        self.spawn_island_center = (-500.0, 10.0, 800.0)
        self.spawn_island_radius = 60.0
        
        # Trajectory
        self.trajectory: Optional[AirplaneTrajectory] = None
        
        # Authoritative World Engine & Bot Controller
        self.world: WorldEngine = WorldEngine()
        self.bot_controller: BotController = BotController(match_id=match_id)
        
        # Match Statistics & Settlement Records
        self.placement_records: List[Dict[str, Any]] = []
        self.settlement_summary: Optional[Dict[str, Any]] = None
        
        # Event Notification log (for UDP broadcast)
        self.pending_broadcasts: List[Dict[str, Any]] = []

    def transition_to(self, new_state: MatchState) -> None:
        """Transitions match instance into a new state and triggers state entry actions."""
        old_state = self.state
        self.state = new_state
        self.state_start_time = time.time()
        self.elapsed_in_state = 0.0
        
        self.pending_broadcasts.append({
            "type": "STATE_CHANGE",
            "old_state": int(old_state),
            "new_state": int(new_state),
            "timestamp": time.time()
        })

        if new_state == MatchState.STATE_2_SPAWN_ISLAND:
            self._enter_spawn_island()
        elif new_state == MatchState.STATE_3_AIRPLANE_FLIGHT:
            self._enter_airplane_flight()
        elif new_state == MatchState.STATE_4_EJECT_PARACHUTE:
            self._enter_eject_parachute()
        elif new_state == MatchState.STATE_5_COMBAT_LOOTING:
            self._enter_combat_looting()
        elif new_state == MatchState.STATE_6_GAME_OVER:
            self._enter_game_over()

    def _enter_spawn_island(self) -> None:
        """State 2: Initialize Spawn Island waiting area & spawn 49 bots."""
        # 1. Teleport human players to Spawn Island
        sx, sy, sz = self.spawn_island_center
        for pid in self.human_player_ids:
            player = self.world.players.get(pid)
            if player:
                player.x = sx + random.uniform(-20.0, 20.0)
                player.y = sy
                player.z = sz + random.uniform(-20.0, 20.0)
                player.hp = 200.0
                player.is_alive = True

        # 2. Attach WorldEngine to BotController and spawn authentic bots
        self.bot_controller.attach_world_engine(self.world)
        self.bot_controller.spawn_bots(count=self.bot_count)
        self.bot_controller.start_island_phase()

        # Ensure all bots are in world.players
        for bot in self.bot_controller.bots.values():
            bid = str(bot.bot_id)
            if bid not in self.world.players:
                self.world.register_player(
                    player_id=bid,
                    nickname=bot.profile.nickname,
                    is_bot=True,
                    x=bot.position.x,
                    y=bot.position.y,
                    z=bot.position.z
                )

    def _enter_airplane_flight(self) -> None:
        """State 3: Generate authentic Bermuda cross-island flight trajectory."""
        angle = random.uniform(0.0, 2.0 * math.pi)
        dist = 1150.0  # Outside island boundary
        start_x = MAP_CENTER_X + math.cos(angle) * dist
        start_z = MAP_CENTER_Z + math.sin(angle) * dist
        end_x = MAP_CENTER_X - math.cos(angle) * dist
        end_z = MAP_CENTER_Z - math.sin(angle) * dist
        
        airplane_altitude = 420.0
        self.trajectory = AirplaneTrajectory(
            start_pos=(start_x, airplane_altitude, start_z),
            end_pos=(end_x, airplane_altitude, end_z),
            flight_speed=65.0
        )
        self.airplane_flight_time = 0.0

        # Board human players aboard airplane
        for pid in self.human_player_ids:
            drop = PlayerDropState(pid, is_bot=False)
            drop.phase = ParachutePhase.ON_AIRPLANE
            drop.x, drop.y, drop.z = self.trajectory.start_pos
            drop.yaw = self.trajectory.yaw
            self.drop_states[pid] = drop

        # Board bots aboard airplane via BotController
        start_vec = Vector3(start_x, airplane_altitude, start_z)
        end_vec = Vector3(end_x, airplane_altitude, end_z)
        self.bot_controller.start_airplane_phase(flight_start=start_vec, flight_end=end_vec)

    def _enter_eject_parachute(self) -> None:
        """State 4: Enable eject and skydiving sequence."""
        pass

    def _enter_combat_looting(self) -> None:
        """State 5: Active battle royale combat loop."""
        self.world.is_match_active = True
        self.world.match_time = 0.0

    def _enter_game_over(self) -> None:
        """State 6: Settle match rankings, Booyah status, and compute rewards."""
        self.settlement_summary = self.calculate_settlement()
        self.pending_broadcasts.append({
            "type": "MATCH_SETTLEMENT",
            "summary": self.settlement_summary
        })

    def eject_player(self, player_id: str) -> bool:
        """Human player initiates manual eject from the airplane."""
        drop = self.drop_states.get(player_id)
        if not drop or drop.phase != ParachutePhase.ON_AIRPLANE:
            return False
        
        if not self.trajectory:
            return False

        plane_x, plane_y, plane_z = self.trajectory.get_position(self.airplane_flight_time)
        drop.phase = ParachutePhase.SKYDIVING
        drop.eject_time = self.airplane_flight_time
        drop.x = plane_x
        drop.y = plane_y - 5.0
        drop.z = plane_z
        drop.velocity_y = -35.0  # Initial free-fall velocity
        drop.forward_speed = 22.0
        drop.yaw = self.trajectory.yaw
        
        self.world.update_player_pos(player_id, drop.x, drop.y, drop.z, yaw=drop.yaw)
        return True

    def deploy_parachute(self, player_id: str) -> bool:
        """Human player deploys parachute canopy manually."""
        drop = self.drop_states.get(player_id)
        if not drop or drop.phase != ParachutePhase.SKYDIVING:
            return False
            
        drop.phase = ParachutePhase.PARACHUTING
        drop.deploy_time = time.time()
        drop.velocity_y = -8.0  # Decelerate to gentle glide
        drop.forward_speed = 10.0
        return True

    def tick(self, delta_time: float) -> Dict[str, Any]:
        """Authoritative match update tick."""
        self.elapsed_in_state += delta_time
        self.match_total_elapsed += delta_time
        events: List[Dict[str, Any]] = []

        # Flush pending lifecycle broadcasts
        if self.pending_broadcasts:
            events.extend(self.pending_broadcasts)
            self.pending_broadcasts.clear()

        # -------------------------------------------------------------
        # STATE 0: MATCHMAKING QUEUE
        # -------------------------------------------------------------
        if self.state == MatchState.STATE_0_MATCHMAKING:
            pass

        # -------------------------------------------------------------
        # STATE 1: UDP CONNECT
        # -------------------------------------------------------------
        elif self.state == MatchState.STATE_1_UDP_CONNECT:
            if any(pid in self.connected_tokens for pid in self.human_player_ids):
                self.transition_to(MatchState.STATE_2_SPAWN_ISLAND)

        # -------------------------------------------------------------
        # STATE 2: SPAWN ISLAND COUNTDOWN (60 seconds)
        # -------------------------------------------------------------
        elif self.state == MatchState.STATE_2_SPAWN_ISLAND:
            remaining_waiting = max(self.waiting_duration - self.elapsed_in_state, 0.0)
            if remaining_waiting <= 0.0:
                self.transition_to(MatchState.STATE_3_AIRPLANE_FLIGHT)
            else:
                events.append({
                    "type": "WAITING_COUNTDOWN",
                    "remaining_seconds": int(remaining_waiting),
                    "total_seconds": int(self.waiting_duration)
                })

                # Tick bots on spawn island (roam, emote, punch)
                bot_tick = self.bot_controller.tick(
                    dt=delta_time,
                    safe_zone_center=Vector3(*self.spawn_island_center),
                    safe_zone_radius=self.spawn_island_radius
                )
                # Sync bot positions into WorldEngine
                for bot_state in bot_tick.get("bot_states", []):
                    pos = bot_state["position"]
                    bid = str(bot_state.get("entity_id", bot_state.get("account_id")))
                    self.world.update_player_pos(
                        player_id=bid,
                        x=pos["x"], y=pos["y"], z=pos["z"],
                        yaw=bot_state.get("yaw", 0.0)
                    )

        # -------------------------------------------------------------
        # STATE 3 & 4: AIRPLANE FLIGHT & PARACHUTE DROP
        # -------------------------------------------------------------
        elif self.state in (MatchState.STATE_3_AIRPLANE_FLIGHT, MatchState.STATE_4_EJECT_PARACHUTE):
            if self.trajectory:
                self.airplane_flight_time += delta_time
                plane_x, plane_y, plane_z = self.trajectory.get_position(self.airplane_flight_time)

                # Update BotController airplane flight progress
                if self.trajectory.total_flight_time > 0:
                    prog = min(self.airplane_flight_time / self.trajectory.total_flight_time, 1.0)
                    self.bot_controller.update_airplane_flight(prog)

                events.append({
                    "type": "AIRPLANE_POS",
                    "x": plane_x, "y": plane_y, "z": plane_z,
                    "yaw": self.trajectory.yaw,
                    "flight_time": self.airplane_flight_time,
                    "total_time": self.trajectory.total_flight_time
                })

                # Check auto-ejection if airplane flight path completes
                if self.trajectory.is_finished(self.airplane_flight_time):
                    for pid, drop in self.drop_states.items():
                        if drop.phase == ParachutePhase.ON_AIRPLANE:
                            self.eject_player(pid)

                # Tick bots through airplane / skydive / parachute sequence
                bot_tick = self.bot_controller.tick(
                    dt=delta_time,
                    safe_zone_center=Vector3(self.world.safe_zone.white_center_x, 20.0, self.world.safe_zone.white_center_z),
                    safe_zone_radius=self.world.safe_zone.white_radius
                )
                for bot_state in bot_tick.get("bot_states", []):
                    pos = bot_state["position"]
                    bid = str(bot_state.get("entity_id", bot_state.get("account_id")))
                    self.world.update_player_pos(
                        player_id=bid,
                        x=pos["x"], y=pos["y"], z=pos["z"],
                        yaw=bot_state.get("yaw", 0.0)
                    )

                # Update human descending physics
                for pid in self.human_player_ids:
                    drop = self.drop_states.get(pid)
                    if not drop:
                        continue
                    if drop.phase == ParachutePhase.ON_AIRPLANE:
                        drop.x, drop.y, drop.z = plane_x, plane_y, plane_z
                    elif drop.phase in (ParachutePhase.SKYDIVING, ParachutePhase.PARACHUTING):
                        if drop.phase == ParachutePhase.SKYDIVING:
                            drop.velocity_y = max(drop.velocity_y - 9.8 * delta_time, -48.0)
                            if drop.y <= drop.auto_deploy_altitude:
                                self.deploy_parachute(pid)
                        elif drop.phase == ParachutePhase.PARACHUTING:
                            drop.velocity_y = -7.5

                        drop.y += drop.velocity_y * delta_time
                        rad = math.radians(drop.yaw)
                        drop.x += math.sin(rad) * drop.forward_speed * delta_time
                        drop.z += math.cos(rad) * drop.forward_speed * delta_time

                        if drop.y <= drop.ground_y:
                            drop.y = drop.ground_y
                            drop.phase = ParachutePhase.LANDED
                            drop.landed_time = time.time()
                            events.append({
                                "type": "PLAYER_LANDED",
                                "player_id": pid,
                                "x": drop.x, "y": drop.y, "z": drop.z
                            })

                        self.world.update_player_pos(pid, drop.x, drop.y, drop.z, yaw=drop.yaw)

                all_humans_landed = bool(self.drop_states) and all(
                    d.phase == ParachutePhase.LANDED for d in self.drop_states.values()
                )

                # Transition checks
                if self.state == MatchState.STATE_3_AIRPLANE_FLIGHT:
                    if any(d.phase != ParachutePhase.ON_AIRPLANE for d in self.drop_states.values()):
                        self.transition_to(MatchState.STATE_4_EJECT_PARACHUTE)

                if self.state == MatchState.STATE_4_EJECT_PARACHUTE and all_humans_landed:
                    self.transition_to(MatchState.STATE_5_COMBAT_LOOTING)

        # -------------------------------------------------------------
        # STATE 5: ACTIVE COMBAT & SAFE ZONE LOOTING LOOP
        # -------------------------------------------------------------
        elif self.state == MatchState.STATE_5_COMBAT_LOOTING:
            # 1. Authoritative World Engine tick (safe zone, poison, airdrops, red zone)
            world_tick = self.world.tick(delta_time)
            events.extend(world_tick.get("events", []))

            # 2. Extract human player positions for bot AI target acquisition
            first_human = self.world.players.get(self.human_player_ids[0]) if self.human_player_ids else None
            human_pos = Vector3(first_human.x, first_human.y, first_human.z) if first_human and first_human.is_alive else None
            human_hp = int(first_human.hp) if first_human else 0

            # 3. Tick Bot Controller (roaming, looting, aiming, shooting)
            bot_tick = self.bot_controller.tick(
                dt=delta_time,
                safe_zone_center=Vector3(self.world.safe_zone.white_center_x, 20.0, self.world.safe_zone.white_center_z),
                safe_zone_radius=self.world.safe_zone.white_radius,
                player_position=human_pos,
                player_hp=human_hp
            )

            # 4. Process bot combat events (bot shooting human or other bots)
            for bot_event in bot_tick.get("events", []):
                events.append(bot_event)
                if bot_event.get("event") == "BOT_FIRE":
                    # Bot fired at human player!
                    target_id = bot_event.get("target_id")
                    if target_id and str(target_id) in self.world.players:
                        dmg = bot_event.get("damage", 25.0)
                        hit_res = self.world.combat.apply_damage(
                            victim=self.world.players[str(target_id)],
                            damage=dmg,
                            attacker=self.world.players.get(str(bot_event.get("attacker_id")))
                        )
                        events.append({"type": "DAMAGE_APPLIED", "data": hit_res})

            # 5. Sync bot positions and health into WorldEngine
            for bot_state in bot_tick.get("bot_states", []):
                bid = str(bot_state.get("entity_id", bot_state.get("account_id")))
                pos = bot_state["position"]
                p = self.world.players.get(bid) or self.world.players.get(str(bot_state.get("account_id")))
                if p:
                    p.x = pos["x"]
                    p.y = pos["y"]
                    p.z = pos["z"]
                    bot_ref = self.bot_controller.get_bot(bot_state.get("account_id")) or self.bot_controller.get_bot(bot_state.get("entity_id"))
                    if not p.is_alive or p.hp <= 0:
                        if bot_ref and bot_ref.lifecycle_state != BotLifecycleState.DEAD:
                            bot_ref.hp = 0
                            bot_ref.lifecycle_state = BotLifecycleState.DEAD
                            bot_ref.is_firing = False
                        p.hp = 0.0
                        p.is_alive = False
                    else:
                        p.hp = bot_state["hp"]
                        p.is_alive = bot_state["is_alive"]

            # 6. Check match termination condition
            alive_count = self.world.alive_player_count
            human_alive = any(
                p.is_alive for pid, p in self.world.players.items()
                if pid in self.human_player_ids
            )

            if alive_count <= 1 or not human_alive:
                self.transition_to(MatchState.STATE_6_GAME_OVER)

        # -------------------------------------------------------------
        # STATE 6: GAME OVER / BOOYAH SETTLEMENT
        # -------------------------------------------------------------
        elif self.state == MatchState.STATE_6_GAME_OVER:
            pass

        return {
            "match_id": self.match_id,
            "state": int(self.state),
            "state_name": self.state.name,
            "alive_players": self.world.alive_player_count,
            "match_elapsed": round(self.match_total_elapsed, 2),
            "events": events
        }

    def build_sync_scene_info_bytes(self) -> bytes:
        """Serialize State 2 Spawn Island countdown scene info frame."""
        countdown = max(self.waiting_duration - self.elapsed_in_state, 0.0)
        return S2C_SyncSceneInfo(
            match_id=self.match_id,
            elapsed_time=float(self.match_total_elapsed),
            countdown_seconds=float(countdown),
            alive_players=self.world.alive_player_count,
            spawn_island_x=self.spawn_island_center[0],
            spawn_island_y=self.spawn_island_center[1],
            spawn_island_z=self.spawn_island_center[2],
            spawn_island_radius=self.spawn_island_radius
        ).serialize()

    def build_battle_start_bytes(self) -> bytes:
        """Serialize State 3 Battle Start / Airplane flight trajectory frame."""
        if not self.trajectory:
            return b""
        return S2C_BattleStart(
            match_id=self.match_id,
            start_pos=self.trajectory.start_pos,
            end_pos=self.trajectory.end_pos,
            altitude=self.trajectory.start_y,
            flight_speed=self.trajectory.flight_speed,
            flight_duration=self.trajectory.total_flight_time
        ).serialize()

    def build_parachute_sync_bytes(self, player_id: str) -> bytes:
        """Serialize State 4 Drop & Parachute frame for a combatant."""
        drop = self.drop_states.get(player_id)
        if not drop:
            return b""
        pid_int = int(player_id) if player_id.isdigit() else 10001
        return S2C_ParachuteSync(
            player_id=pid_int,
            phase=int(drop.phase),
            x=drop.x,
            y=drop.y,
            z=drop.z,
            velocity_y=drop.velocity_y,
            forward_speed=drop.forward_speed,
            yaw=drop.yaw
        ).serialize()

    def build_safe_zone_bytes(self) -> bytes:
        """Serialize State 5 Safe Zone circle change frame."""
        sz = self.world.safe_zone
        return RUDP_SafeZoneChange(
            phase=sz.phase_idx,
            current_x=float(sz.blue_center_x),
            current_y=0.0,
            current_z=float(sz.blue_center_z),
            current_radius=float(sz.blue_radius),
            next_x=float(sz.white_center_x),
            next_y=0.0,
            next_z=float(sz.white_center_z),
            next_radius=float(sz.white_radius),
            shrink_duration=float(sz.timer),
            damage_per_second=float(sz.current_dps)
        ).serialize()

    def calculate_settlement(self) -> Dict[str, Any]:
        """Calculate authentic Free Fire post-match rewards and rank points."""
        settlements = []
        
        players = list(self.world.players.values())
        players.sort(key=lambda p: (1 if p.is_alive else 0, p.kills, p.damage_dealt), reverse=True)

        for rank_idx, player in enumerate(players, start=1):
            is_booyah = (rank_idx == 1 and player.is_alive)
            
            base_gold = 100
            kill_gold = player.kills * 25
            rank_gold = 250 if is_booyah else max(150 - rank_idx * 3, 20)
            total_gold = base_gold + kill_gold + rank_gold
            
            base_exp = 120
            survival_exp = int(min(self.match_total_elapsed * 1.2, 350))
            kill_exp = player.kills * 40
            total_exp = base_exp + survival_exp + kill_exp
            
            if is_booyah:
                rank_score_delta = 45 + min(player.kills * 5, 25)
            elif rank_idx <= 5:
                rank_score_delta = 25 + player.kills * 3
            elif rank_idx <= 10:
                rank_score_delta = 10 + player.kills * 2
            elif rank_idx <= 25:
                rank_score_delta = -5 + player.kills * 2
            else:
                rank_score_delta = -18 + player.kills * 2

            settlements.append({
                "rank": rank_idx,
                "player_id": player.player_id,
                "nickname": player.nickname,
                "is_bot": player.is_bot,
                "is_booyah": is_booyah,
                "kills": player.kills,
                "damage": int(player.damage_dealt),
                "survival_time_secs": int(self.match_total_elapsed),
                "gold_earned": total_gold,
                "exp_earned": total_exp,
                "rank_score_delta": rank_score_delta
            })

        return {
            "match_id": self.match_id,
            "total_players": len(players),
            "is_booyah": settlements[0]["is_booyah"] if settlements else False,
            "winner_nickname": settlements[0]["nickname"] if settlements else "Unknown",
            "settlements": settlements
        }

    def handle_player_damage_bot(self, victim_id: Any, attacker_id: Any, damage: float,
                                 body_part: int = 2, weapon_id: int = 101001,
                                 hit_pos: Optional[Tuple[float, float, float]] = None) -> Dict[str, Any]:
        """
        Authoritative processing when human player shoots/damages a bot.
        Handles damage mitigation, bot health update, death check, and Booyah condition.
        """
        try:
            v_int = int(victim_id)
        except (ValueError, TypeError):
            v_int = 0

        bot = None
        if v_int in (2, 2000001):
            bot = self.bot_controller.get_bot_by_account_id(2000001) or self.bot_controller.get_bot(1)
        elif v_int in (3, 2000002):
            bot = self.bot_controller.get_bot_by_account_id(2000002) or self.bot_controller.get_bot(2)
        else:
            bot = self.bot_controller.get_bot(v_int)

        if not bot and isinstance(victim_id, str):
            for b in self.bot_controller.bots.values():
                if b.nickname.lower() == victim_id.lower():
                    bot = b
                    break

        if not bot:
            return {"hit": False, "error": f"Bot {victim_id} not found", "is_dead": False}

        is_dead, death_ev = bot.take_damage(
            damage=int(damage),
            attacker_id=int(attacker_id) if str(attacker_id).isdigit() else 0,
            hit_part=body_part,
            weapon_id=weapon_id
        )

        # Sync into world.players
        p = (self.world.players.get(str(bot.bot_id)) or 
             self.world.players.get(str(bot.account_id)) or
             self.world.players.get(str(getattr(bot, "player_id", 0))))
        if p:
            p.hp = float(bot.hp)
            p.is_alive = (bot.hp > 0)

        # Attacker stats
        attacker_p = self.world.players.get(str(attacker_id))
        if attacker_p:
            attacker_p.damage_dealt += damage
            if is_dead:
                attacker_p.kills += 1

        res = {
            "hit": True,
            "victim_id": getattr(bot, "player_id", bot.bot_id),
            "account_id": bot.account_id,
            "bot_id": bot.bot_id,
            "nickname": bot.nickname,
            "damage": damage,
            "remaining_hp": bot.hp,
            "is_dead": is_dead,
            "death_event": death_ev
        }

        if is_dead:
            alive_bots = sum(1 for b in self.bot_controller.bots.values() if b.hp > 0)
            if alive_bots == 0 or self.world.alive_player_count <= 1:
                self.transition_to(MatchState.STATE_6_GAME_OVER)
                res["is_booyah"] = True

        return res

    def handle_player_kill_bot(self, victim_id: Any, killer_id: Any,
                               weapon_id: int = 101001, is_headshot: bool = False) -> Dict[str, Any]:
        """Direct authoritative lethal elimination of a bot (Opcode 107)."""
        return self.handle_player_damage_bot(
            victim_id=victim_id,
            attacker_id=killer_id,
            damage=9999.0,
            body_part=1 if is_headshot else 2,
            weapon_id=weapon_id
        )


class MatchDirector:
    """Master Match Director managing all active match instances and TCP/UDP handoffs."""

    def __init__(self, default_server_addr: str = "10.0.2.2:39800"):
        self.default_server_addr = default_server_addr
        self.active_matches: Dict[int, MatchInstance] = {}
        self.player_to_match: Dict[str, int] = {}

    def create_match(self,
                     match_id: int,
                     map_id: int = 1,
                     game_mode: int = 1,
                     match_mode: int = 1,
                     host_player_id: str = "10001",
                     host_nickname: str = "LO",
                     server_addr: Optional[str] = None,
                     waiting_duration: float = 60.0,
                     bot_count: int = 49,
                     prepare_token: Optional[str] = None,
                     secret: Optional[str] = None) -> MatchInstance:
        """Create and initialize a new Free Fire battle royale match instance."""
        addr = server_addr or self.default_server_addr
        match = MatchInstance(
            match_id=match_id,
            map_id=map_id,
            game_mode=game_mode,
            match_mode=match_mode,
            server_addr=addr,
            waiting_duration=waiting_duration,
            bot_count=bot_count,
            prepare_token=prepare_token,
            secret=secret
        )
        
        match.human_player_ids.append(host_player_id)
        match.world.register_player(host_player_id, host_nickname, is_bot=False)
        self.player_to_match[host_player_id] = match_id
        
        self.active_matches[match_id] = match
        return match

    def get_match(self, match_id: int) -> Optional[MatchInstance]:
        """Look up match instance by ID."""
        return self.active_matches.get(match_id)

    def get_match_for_player(self, player_id: str) -> Optional[MatchInstance]:
        """Look up match instance currently containing a player."""
        mid = self.player_to_match.get(player_id)
        return self.active_matches.get(mid) if mid else None

    def handle_udp_handshake(self, match_id: int, player_id: str, token: str, client_endpoint: Tuple[str, int], session_key: Optional[int] = None) -> bool:
        """Authenticate and link a connecting UDP client to a match instance."""
        match = self.get_match(match_id)
        if not match:
            return False
        
        if match.prepare_token and token and token != match.prepare_token and not match.prepare_token.startswith(token) and not token.startswith(match.prepare_token):
            return False

        match.connected_tokens[player_id] = token
        match.client_endpoints[player_id] = client_endpoint
        if session_key is not None:
            match.client_session_keys[player_id] = session_key
        
        if match.state == MatchState.STATE_1_UDP_CONNECT:
            match.transition_to(MatchState.STATE_2_SPAWN_ISLAND)
            
        return True

    def tick_all(self, delta_time: float) -> List[Dict[str, Any]]:
        """Advance authoritative simulation for all active matches."""
        results = []
        for mid, match in list(self.active_matches.items()):
            res = match.tick(delta_time)
            results.append(res)
        return results


    def handle_player_damage_bot(self, match_id: int, victim_id: Any, attacker_id: Any, damage: float,
                                 body_part: int = 2, weapon_id: int = 101001) -> Dict[str, Any]:
        match = self.get_match(match_id)
        if match:
            return match.handle_player_damage_bot(victim_id, attacker_id, damage, body_part, weapon_id)
        return {"hit": False, "error": "Match not found"}

    def handle_player_kill_bot(self, match_id: int, victim_id: Any, killer_id: Any,
                               weapon_id: int = 101001, is_headshot: bool = False) -> Dict[str, Any]:
        match = self.get_match(match_id)
        if match:
            return match.handle_player_kill_bot(victim_id, killer_id, weapon_id, is_headshot)
        return {"hit": False, "error": "Match not found"}


# Global singleton instance
global_match_director = MatchDirector()
