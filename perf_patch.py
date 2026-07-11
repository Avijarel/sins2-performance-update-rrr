"""
Performance Patch Script for Multiplayer Performance Update RRR
Applies performance optimizations to fresh RRR base files.
"""
import json
import os
import sys
import re

ENTITIES = os.path.join(os.path.dirname(__file__), "entities")

def load_json(path):
    """Load JSON with comment tolerance and trailing comma removal."""
    with open(path, 'r', encoding='utf-8-sig') as f:
        text = f.read()
    # Remove trailing commas before ] or }
    text = re.sub(r',\s*([}\]])', r'\1', text)
    return json.loads(text)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def deep_set(data, key_path, value):
    """Set a nested key. key_path is dot-separated, e.g. 'strikecraft.squadron_size'"""
    keys = key_path.split('.')
    obj = data
    for k in keys[:-1]:
        if isinstance(obj, dict) and k in obj:
            obj = obj[k]
        else:
            return False
    if isinstance(obj, dict) and keys[-1] in obj:
        obj[keys[-1]] = value
        return True
    return False

def deep_get(data, key_path, default=None):
    keys = key_path.split('.')
    obj = data
    for k in keys:
        if isinstance(obj, dict) and k in obj:
            obj = obj[k]
        else:
            return default
    return obj

def patch_file(filename, patches):
    path = os.path.join(ENTITIES, filename)
    if not os.path.exists(path):
        print(f"  SKIP (not found): {filename}")
        return False
    try:
        data = load_json(path)
    except Exception as e:
        print(f"  ERROR loading {filename}: {e}")
        return False

    changed = False
    for key_path, value in patches:
        if deep_set(data, key_path, value):
            changed = True

    if changed:
        save_json(path, data)
        print(f"  PATCHED: {filename}")
    return changed

def patch_strikecraft_unit(filename, squadron_size=1):
    """Patch a strikecraft unit: squadron_size -> 1, adjust build time."""
    path = os.path.join(ENTITIES, filename)
    if not os.path.exists(path):
        print(f"  SKIP: {filename}")
        return
    data = load_json(path)

    # Get original squadron size for scaling
    orig_size = deep_get(data, 'strikecraft.squadron_size', 4)
    scale = orig_size / squadron_size if orig_size > squadron_size else 1

    # Set squadron size
    if 'strikecraft' in data:
        data['strikecraft']['squadron_size'] = squadron_size

    # Scale HP up
    for key in ['hull', 'armor', 'shields']:
        if key in data:
            hp_key = 'max_points' if key != 'armor' else 'max_points'
            if 'max_points' in data[key]:
                data[key]['max_points'] = round(data[key]['max_points'] * scale, 1)

    # Reduce build time (faster since fewer entities)
    if 'build' in data and 'build_time' in data['build']:
        data['build']['build_time'] = round(data['build']['build_time'] * 0.65, 1)

    save_json(path, data)
    print(f"  PATCHED strikecraft: {filename} (scale={scale:.1f}x, squad {orig_size}->{squadron_size})")

def patch_strikecraft_weapon(filename, cooldown_mult=2.0, damage_mult=2.0):
    """Double cooldown and damage for DPS-neutral fewer projectiles."""
    path = os.path.join(ENTITIES, filename)
    if not os.path.exists(path):
        print(f"  SKIP: {filename}")
        return
    data = load_json(path)

    # Scale cooldown
    if 'cooldown_duration' in data:
        data['cooldown_duration'] = round(data['cooldown_duration'] * cooldown_mult, 2)

    # Scale damage
    if 'damage' in data:
        if isinstance(data['damage'], (int, float)):
            data['damage'] = round(data['damage'] * damage_mult, 2)
        elif isinstance(data['damage'], list):
            data['damage'] = [round(d * damage_mult, 2) for d in data['damage']]

    # Scale penetration slightly
    if 'penetration' in data:
        if isinstance(data['penetration'], (int, float)):
            data['penetration'] = round(data['penetration'] * 1.3, 1)
        elif isinstance(data['penetration'], list):
            data['penetration'] = [round(p * 1.3, 1) for p in data['penetration']]

    save_json(path, data)
    print(f"  PATCHED weapon: {filename} (cd x{cooldown_mult}, dmg x{damage_mult})")

def patch_debris(filename):
    """Set debris lifetime to 5 seconds."""
    path = os.path.join(ENTITIES, filename)
    if not os.path.exists(path):
        return
    data = load_json(path)
    if 'debris' in data and 'lifetime' in data['debris']:
        data['debris']['lifetime'] = [5.0, 5.0]
        save_json(path, data)
        print(f"  PATCHED debris: {filename}")

def patch_carrier_capacity(filename, capacity):
    """Reduce carrier/starbase squadron capacity."""
    path = os.path.join(ENTITIES, filename)
    if not os.path.exists(path):
        return
    data = load_json(path)
    if 'carrier' in data and 'base_max_squadron_capacity' in data['carrier']:
        data['carrier']['base_max_squadron_capacity'] = capacity
        save_json(path, data)
        print(f"  PATCHED carrier cap: {filename} -> {capacity}")

def patch_trade_structure(filename):
    """Reduce trade ship counts and slow construction."""
    path = os.path.join(ENTITIES, filename)
    if not os.path.exists(path):
        return
    data = load_json(path)
    changed = False

    if 'trade_port' in data:
        tp = data['trade_port']
        if 'max_trade_ship_count' in tp:
            tp['max_trade_ship_count'] = 1
            changed = True
        if 'trade_ship_construction_time' in tp:
            tp['trade_ship_construction_time'] = 10000.0
            changed = True

    if 'traffic_port' in data:
        tfp = data['traffic_port']
        if 'max_traffic_ship_count' in tfp:
            tfp['max_traffic_ship_count'] = 1
            changed = True
        if 'traffic_ship_construction_time' in tfp:
            tfp['traffic_ship_construction_time'] = 60.0
            changed = True

    if changed:
        save_json(path, data)
        print(f"  PATCHED trade: {filename}")

def patch_hangar_defense(filename):
    """Make hangar defense very expensive to effectively disable it."""
    path = os.path.join(ENTITIES, filename)
    if not os.path.exists(path):
        return
    data = load_json(path)

    # Increase cost 10x
    if 'build' in data and 'price' in data['build']:
        for res in ['credits', 'metal', 'crystal']:
            if res in data['build']['price']:
                data['build']['price'][res] = round(data['build']['price'][res] * 10, 0)

    # Increase slot cost
    if 'structure' in data and 'slot_count' in data['structure']:
        data['structure']['slot_count'] = 7

    # AI won't build
    if 'player_ai' not in data:
        data['player_ai'] = {}
    data['player_ai']['max_count_at_planet'] = 0.0

    # Reduce carrier capacity
    if 'carrier' in data and 'base_max_squadron_capacity' in data['carrier']:
        data['carrier']['base_max_squadron_capacity'] = 1

    save_json(path, data)
    print(f"  PATCHED hangar defense: {filename}")


# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("PERFORMANCE PATCH - Applying optimizations to RRR base files")
    print("=" * 60)

    # --- STRIKECRAFT UNITS ---
    print("\n[1/7] STRIKECRAFT UNITS (squadron_size -> 1)")
    strikecraft_units = [
        "advent_beam_corvette_strikecraft.unit",
        "advent_beam_corvette_strikecraft_loyalist.unit",
        "advent_bomber_strikecraft.unit",
        "advent_bomber_strikecraft_loyalist.unit",
        "advent_interceptor_strikecraft.unit",
        "advent_interceptor_strikecraft_loyalist.unit",
        "advent_mine_strikecraft.unit",
        "trader_bomber_strikecraft.unit",
        "trader_bomber_strikecraft_loyalist.unit",
        "trader_bomber_strikecraft_rebel.unit",
        "trader_interceptor_strikecraft.unit",
        "trader_interceptor_strikecraft_loyalist.unit",
        "trader_interceptor_strikecraft_rebel.unit",
        "trader_missile_corvette_strikecraft.unit",
        "vasari_bomber_strikecraft.unit",
        "vasari_bomber_strikecraft_loyalist.unit",
        "vasari_interceptor_strikecraft.unit",
        "vasari_raider_corvette_strikecraft.unit",
    ]
    for f in strikecraft_units:
        patch_strikecraft_unit(f)

    # --- STRIKECRAFT WEAPONS ---
    print("\n[2/7] STRIKECRAFT WEAPONS (cooldown x2, damage x2)")
    strikecraft_weapons = [
        "advent_beam_corvette_beam_strikecraft.weapon",
        "advent_beam_corvette_plasma_strikecraft.weapon",
        "advent_bomber_strikecraft_heavy_beam.weapon",
        "advent_interceptor_strikecraft_light_laser.weapon",
        "advent_mine_strikecraft_bait.weapon",
        "trader_bomber_strikecraft_heavy_missile.weapon",
        "trader_bomber_strikecraft_light_gauss.weapon",
        "trader_interceptor_strikecraft_beam.weapon",
        "trader_interceptor_strikecraft_light_autocannon.weapon",
        "trader_interceptor_strikecraft_light_autocannon_rebel.weapon",
        "trader_missile_corvette_missile_strikecraft.weapon",
        "trader_missile_corvette_missile.weapon",
        "vasari_bomber_strikecraft_heavy_phase_missile.weapon",
        "vasari_bomber_strikecraft_heavy_wave_cannon.weapon",
        "vasari_interceptor_strikecraft_beam.weapon",
        "vasari_raider_corvette_medium_pulse_strikecraft.weapon",
        "vasari_raider_corvette_phase_missile_strikecraft.weapon",
    ]
    for f in strikecraft_weapons:
        patch_strikecraft_weapon(f)

    # --- DEBRIS ---
    print("\n[3/7] DEBRIS (lifetime -> 5s)")
    debris_files = [
        "advent_generic_large_debris.unit",
        "advent_generic_small_debris.unit",
        "generic_large_debris.unit",
        "generic_small_debris.unit",
        "trader_generic_large_debris.unit",
        "trader_generic_small_debris.unit",
        "vasari_generic_large_debris.unit",
        "vasari_generic_small_debris.unit",
    ]
    for f in debris_files:
        patch_debris(f)

    # --- STARBASES (squadron cap -> 0) ---
    print("\n[4/7] STARBASES (squadron capacity -> 0)")
    starbase_units = [
        "advent_starbase.unit",
        "advent_starbase_loyalist.unit",
        "advent_starbase_n.unit",
        "advent_starbase_rebel.unit",
        "trader_starbase.unit",
        "trader_starbase_loyalist.unit",
        "trader_starbase_n.unit",
        "trader_starbase_rebel.unit",
        "vasari_starbase.unit",
        "vasari_starbase_loyalist.unit",
        "vasari_starbase_n.unit",
        "vasari_starbase_rebel.unit",
    ]
    for f in starbase_units:
        patch_carrier_capacity(f, 0)

    # --- CARRIERS (squadron cap -> 1) ---
    print("\n[5/7] CARRIERS (squadron capacity -> 1)")
    carrier_units = [
        "advent_carrier_cruiser.unit",
        "advent_carrier_cruiser_loyalist.unit",
        "trader_carrier_cruiser.unit",
        "trader_carrier_cruiser_insurgency.unit",
        "vasari_carrier_cruiser.unit",
    ]
    for f in carrier_units:
        patch_carrier_capacity(f, 1)

    # --- TRADE/TRAFFIC ---
    print("\n[6/7] TRADE/TRAFFIC (reduced counts)")
    trade_files = [
        "trader_trade_port_structure.unit",
        "vasari_trader_trade_port_structure.unit",
        "npc_trader_trade_port_structure.unit",
        "advent_population_structure.unit",
        "danoba_population_structure.unit",
        "trader_population_structure.unit",
        "vasari_population_structure.unit",
        "advent_exotic_factory_structure.unit",
        "advent_exotic_factory_structure_loyalist.unit",
        "trader_exotic_factory_structure.unit",
        "vasari_exotic_factory_structure.unit",
        "trader_colony_capital_ship.unit",
        "trader_colony_capital_ship_loyalist.unit",
        "trader_colony_capital_ship_n.unit",
        "trader_colony_capital_ship_rebel.unit",
        "trader_starbase.unit",
        "trader_starbase_loyalist.unit",
        "trader_starbase_n.unit",
        "trader_starbase_rebel.unit",
    ]
    for f in trade_files:
        patch_trade_structure(f)

    # --- HANGAR DEFENSE ---
    print("\n[7/7] HANGAR DEFENSE (effectively disabled)")
    hangar_files = [
        "advent_hangar_defense_structure.unit",
        "advent_hangar_defense_structure_loyalist.unit",
        "trader_hangar_defense_structure.unit",
        "trader_hangar_defense_structure_loyalist.unit",
        "trader_hangar_defense_structure_rebel.unit",
        "vasari_hangar_defense_structure.unit",
    ]
    for f in hangar_files:
        patch_hangar_defense(f)

    print("\n" + "=" * 60)
    print("DONE! All performance patches applied.")
    print("=" * 60)
