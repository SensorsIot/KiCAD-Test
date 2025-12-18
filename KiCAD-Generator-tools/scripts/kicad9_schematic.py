#!/usr/bin/env python3
"""
KiCad 9 Schematic Generator

Generates .kicad_sch files with:
- Embedded symbol definitions (lib_symbols)
- Part grouping by belongs_to attribute
- Net labels on all pins (no wire routing between parts)

All connections use net labels instead of wire routing. This avoids issues
where long wires could accidentally pass through pin coordinates and cause
KiCad to merge unrelated nets.

This is a standalone module that can be integrated into SKiDL.
"""

import json
import math
import re
import uuid
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime


# =============================================================================
# S-Expression Writer
# =============================================================================

class SexpWriter:
    """Helper class for writing KiCad S-expression format."""

    def __init__(self):
        self.lines = []
        self.indent_level = 0
        self.indent_char = "\t"

    def _indent(self) -> str:
        return self.indent_char * self.indent_level

    def line(self, text: str):
        """Add a line with current indentation."""
        self.lines.append(f"{self._indent()}{text}")

    def open(self, name: str, *args, newline: bool = True):
        """Open an S-expression block: (name args..."""
        parts = [name] + [self._format_arg(a) for a in args]
        if newline:
            self.line("(" + " ".join(parts))
            self.indent_level += 1
        else:
            return "(" + " ".join(parts) + ")"

    def close(self):
        """Close an S-expression block."""
        self.indent_level -= 1
        self.line(")")

    def atom(self, name: str, *args):
        """Write a single-line S-expression: (name args...)"""
        parts = [name] + [self._format_arg(a) for a in args]
        self.line("(" + " ".join(parts) + ")")

    # Keywords that should not be quoted
    KEYWORDS = {'yes', 'no', 'default', 'none', 'left', 'right', 'top', 'bottom',
                'center', 'hide', 'input', 'output', 'bidirectional', 'passive',
                'power_in', 'power_out', 'open_collector', 'open_emitter',
                'unconnected', 'unspecified', 'line', 'inverted', 'clock'}

    def _format_arg(self, arg) -> str:
        """Format an argument for S-expression."""
        if isinstance(arg, str):
            if arg.startswith('"') or arg in self.KEYWORDS or re.match(r'^-?\d+\.?\d*$', arg):
                return arg
            return f'"{arg}"'
        elif isinstance(arg, bool):
            return 'yes' if arg else 'no'
        elif isinstance(arg, float):
            return f"{arg:.4f}".rstrip('0').rstrip('.')
        elif isinstance(arg, int):
            return str(arg)
        else:
            return str(arg)

    def get_output(self) -> str:
        return "\n".join(self.lines)


def generate_uuid() -> str:
    """Generate a UUID for KiCad elements."""
    return str(uuid.uuid4())


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class Point:
    """2D point with grid snapping."""
    x: float
    y: float

    def snap(self, grid: float = 2.54) -> 'Point':
        """Snap to grid using round-half-away-from-zero (not Python's banker's rounding)."""
        # Python's round() uses banker's rounding which rounds .5 to nearest even.
        # This causes bugs when two adjacent grid points round to the same value.
        # Use floor(x + 0.5) for proper rounding behavior.
        def round_half_up(x):
            if x >= 0:
                return math.floor(x + 0.5)
            else:
                return math.ceil(x - 0.5)
        return Point(
            round_half_up(self.x / grid) * grid,
            round_half_up(self.y / grid) * grid
        )

    def __add__(self, other: 'Point') -> 'Point':
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: 'Point') -> 'Point':
        return Point(self.x - other.x, self.y - other.y)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Point):
            return False
        return abs(self.x - other.x) < 0.001 and abs(self.y - other.y) < 0.001

    def __hash__(self):
        return hash((round(self.x, 2), round(self.y, 2)))


@dataclass
class SymbolPin:
    """Pin from symbol definition."""
    name: str
    number: str
    x: float  # Relative to symbol origin
    y: float
    rotation: int  # 0=right, 90=up, 180=left, 270=down
    length: float
    electrical_type: str = "passive"


@dataclass
class SymbolDef:
    """Symbol definition from library."""
    name: str
    lib_name: str
    pins: Dict[str, SymbolPin]  # Keyed by pin name
    properties: Dict[str, str]
    raw_sexp: str  # Original S-expression for embedding
    width: float = 20.0
    height: float = 20.0
    # Asymmetric extents from origin (in symbol coordinates, Y+ = up)
    # y_extent_up: how far symbol extends UP from origin (in symbol coords)
    # y_extent_down: how far symbol extends DOWN from origin (in symbol coords)
    # In schematic (Y inverted): y_extent_up becomes extent toward smaller Y (toward top)
    y_extent_up: float = 10.0
    y_extent_down: float = 10.0


@dataclass
class PartInstance:
    """Placed part instance."""
    ref: str
    value: str
    symbol: SymbolDef
    position: Point
    rotation: int = 0
    belongs_to: Optional[str] = None
    pins: Dict[str, str] = field(default_factory=dict)  # pin_name -> net_name
    lcsc: str = ""
    footprint: str = ""


@dataclass
class Wire:
    """Wire segment."""
    start: Point
    end: Point

    def __hash__(self):
        # Normalize wire direction for deduplication
        if (self.start.x, self.start.y) > (self.end.x, self.end.y):
            return hash((self.end.x, self.end.y, self.start.x, self.start.y))
        return hash((self.start.x, self.start.y, self.end.x, self.end.y))

    def __eq__(self, other):
        if not isinstance(other, Wire):
            return False
        return (self.start == other.start and self.end == other.end) or \
               (self.start == other.end and self.end == other.start)


# =============================================================================
# Symbol Library Parser
# =============================================================================

def parse_kicad_sym(lib_path: Path) -> Dict[str, SymbolDef]:
    """Parse a .kicad_sym file and extract symbol definitions."""

    content = lib_path.read_text(encoding='utf-8')
    symbols = {}

    # Find top-level symbol definitions
    # Pattern: (symbol "NAME" (in_bom ...) (on_board ...) ... )
    # We need to find balanced parentheses

    def find_matching_paren(text: str, start: int) -> int:
        """Find the matching closing parenthesis."""
        depth = 0
        i = start
        while i < len(text):
            if text[i] == '(':
                depth += 1
            elif text[i] == ')':
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        return -1

    # Find all top-level symbols (handle both tab and space indentation)
    # Note: Some symbols have extra spaces before (in_bom, so we use \s+ instead of single space
    pattern = re.compile(r'\n(\s+)\(symbol "([^"]+)"\s+\(in_bom')
    for match in pattern.finditer(content):
        indent = match.group(1)
        sym_name = match.group(2)
        # Find the opening paren of (symbol
        paren_pos = match.start() + 1 + len(indent)  # Skip newline and indent
        end_pos = find_matching_paren(content, paren_pos)

        if end_pos == -1:
            continue

        sym_content = content[paren_pos:end_pos + 1]

        # Skip sub-units (symbols containing _ followed by number_number)
        if re.search(r'_\d+_\d+$', sym_name):
            continue

        # Parse pins
        pins = {}
        pin_pattern = re.compile(
            r'\(pin\s+(\w+)\s+\w+\s*\(at\s+([-\d.]+)\s+([-\d.]+)\s+(\d+)\)\s*\(length\s+([-\d.]+)\).*?\(name\s+"([^"]*)".*?\(number\s+"([^"]*)"',
            re.DOTALL
        )

        for pin_match in pin_pattern.finditer(sym_content):
            elec_type = pin_match.group(1)
            x = float(pin_match.group(2))
            y = float(pin_match.group(3))
            rot = int(pin_match.group(4))
            length = float(pin_match.group(5))
            name = pin_match.group(6)
            number = pin_match.group(7)

            pins[name] = SymbolPin(
                name=name,
                number=number,
                x=x,
                y=y,
                rotation=rot,
                length=length,
                electrical_type=elec_type
            )

        # Parse properties
        properties = {}
        prop_pattern = re.compile(r'\(property "(\w+)" "([^"]*)"')
        for prop_match in prop_pattern.finditer(sym_content):
            properties[prop_match.group(1)] = prop_match.group(2)

        # Calculate bounding box and asymmetric extents from pins
        y_extent_up = 10.0  # Default
        y_extent_down = 10.0
        if pins:
            xs = [p.x for p in pins.values()]
            ys = [p.y for p in pins.values()]
            width = max(xs) - min(xs) + 10 if xs else 20
            height = max(ys) - min(ys) + 10 if ys else 20
            # Calculate how far symbol extends from origin
            y_extent_up = max(ys) + 5 if ys else 10  # Extent UP in symbol coords (+ margin)
            y_extent_down = -min(ys) + 5 if ys else 10  # Extent DOWN (negative Y becomes positive)
            if y_extent_down < 0:
                y_extent_down = 0  # Symbol doesn't extend below origin
        else:
            rect_pattern = re.compile(r'\(rectangle\s+\(start\s+([-\d.]+)\s+([-\d.]+)\)\s*\(end\s+([-\d.]+)\s+([-\d.]+)\)')
            rect_match = rect_pattern.search(sym_content)
            if rect_match:
                x1, y1 = float(rect_match.group(1)), float(rect_match.group(2))
                x2, y2 = float(rect_match.group(3)), float(rect_match.group(4))
                width = abs(x2 - x1)
                height = abs(y2 - y1)
                y_extent_up = max(y1, y2) + 5
                y_extent_down = -min(y1, y2) + 5 if min(y1, y2) < 0 else 0
            else:
                width, height = 20, 20

        # Determine library name from symbol name
        lib_name = "JLCPCB"  # Default

        symbols[sym_name] = SymbolDef(
            name=sym_name,
            lib_name=lib_name,
            pins=pins,
            properties=properties,
            raw_sexp=sym_content,
            width=width,
            height=height,
            y_extent_up=y_extent_up,
            y_extent_down=y_extent_down
        )

    return symbols


def build_lcsc_to_symbol(symbols: Dict[str, SymbolDef]) -> Dict[str, str]:
    """Build LCSC part number to symbol name mapping from parsed symbols."""
    mapping = {}
    for sym_name, sym in symbols.items():
        lcsc = sym.properties.get('LCSC', '')
        if lcsc:
            mapping[lcsc] = sym_name
    return mapping


# Minimum pin count to trigger Y spacing doubling
# Parts with 3+ pins get doubled Y spacing for better label readability
MIN_PINS_FOR_SCALING = 3


def scale_symbol_y(symbol: SymbolDef, scale: float) -> SymbolDef:
    """
    Scale Y coordinates in a symbol definition.

    Modifies pin Y positions. Box size stays minimal, value text rotated 90°.
    """
    # Scale pin Y positions
    scaled_pins = {}
    for name, pin in symbol.pins.items():
        scaled_pins[name] = SymbolPin(
            name=pin.name,
            number=pin.number,
            x=pin.x,
            y=pin.y * scale,
            rotation=pin.rotation,
            length=pin.length,
            electrical_type=pin.electrical_type
        )

    # Calculate new box size based on where pins ENTER the body, not connection points
    # Pin entry point = connection point + pin length in pin direction
    # The box edge should be at the entry point (no extra margin needed)
    if scaled_pins:
        entry_ys = []
        for p in scaled_pins.values():
            # Calculate Y where pin enters body based on rotation
            if p.rotation == 90:  # Pin points UP, enters body above connection
                entry_y = p.y + p.length
            elif p.rotation == 270:  # Pin points DOWN, enters body below connection
                entry_y = p.y - p.length
            else:  # Horizontal pins (0, 180) - entry Y same as connection Y
                entry_y = p.y
            entry_ys.append(entry_y)
        max_y = max(entry_ys)
        min_y = min(entry_ys)
        # Box edge is at the entry point - connection points are outside the box
        box_top = max_y
        box_bottom = min_y
    else:
        box_top = symbol.height / 2
        box_bottom = -symbol.height / 2

    # Scale Y in pin (at X Y angle) - only within pin definitions
    def scale_pin_at(m):
        x = m.group(1)
        y = float(m.group(2)) * scale
        angle = m.group(3)
        return f'(at {x} {y:.2f} {angle})'

    scaled_sexp = re.sub(
        r'\(pin\s+\w+\s+\w+\s+\(at\s+([-\d.]+)\s+([-\d.]+)\s+(\d+)\)',
        lambda m: f'(pin {m.group(0).split()[1]} {m.group(0).split()[2]} (at {m.group(0).split("(at ")[1].split()[0]} {float(m.group(0).split("(at ")[1].split()[1]) * scale:.2f} {m.group(0).split("(at ")[1].split()[2].rstrip(")")})',
        symbol.raw_sexp
    )

    # Simpler approach: process line by line
    lines = symbol.raw_sexp.split('\n')
    new_lines = []
    for line in lines:
        # Scale pin Y coordinates
        if '(pin ' in line and '(at ' in line:
            def scale_pin_y(m):
                x = m.group(1)
                y = float(m.group(2)) * scale
                angle = m.group(3)
                return f'(at {x} {y:.2f} {angle})'
            line = re.sub(r'\(at\s+([-\d.]+)\s+([-\d.]+)\s+(\d+)\)', scale_pin_y, line)
        # Update rectangle to fit pins (not scaled, recalculated)
        elif '(rectangle' in line and '(start' in line:
            # Extract X coordinates, use new Y bounds
            start_match = re.search(r'\(start\s+([-\d.]+)\s+([-\d.]+)\)', line)
            end_match = re.search(r'\(end\s+([-\d.]+)\s+([-\d.]+)\)', line)
            if start_match and end_match:
                x1 = start_match.group(1)
                x2 = end_match.group(1)
                line = re.sub(r'\(start\s+[-\d.]+\s+[-\d.]+\)', f'(start {x1} {box_top:.2f})', line)
                line = re.sub(r'\(end\s+[-\d.]+\s+[-\d.]+\)', f'(end {x2} {box_bottom:.2f})', line)
        # Rotate Value property 90 degrees
        elif '(property "Value"' in line:
            line = re.sub(r'\(at\s+([-\d.]+)\s+([-\d.]+)\s+0\)', r'(at \1 \2 90)', line)
        new_lines.append(line)

    scaled_sexp = '\n'.join(new_lines)

    # Calculate y extents from scaled pins
    if scaled_pins:
        ys = [p.y for p in scaled_pins.values()]
        y_extent_up = max(ys) + 5  # How far symbol extends UP from origin
        y_extent_down = -min(ys) + 5 if min(ys) < 0 else 0  # How far DOWN
    else:
        y_extent_up = symbol.y_extent_up * scale
        y_extent_down = symbol.y_extent_down * scale

    return SymbolDef(
        name=symbol.name,
        lib_name=symbol.lib_name,
        pins=scaled_pins,
        properties=symbol.properties,
        raw_sexp=scaled_sexp,
        width=symbol.width,
        height=box_top - box_bottom,
        y_extent_up=y_extent_up,
        y_extent_down=y_extent_down
    )


# =============================================================================
# Part Placement with Force-Directed Algorithm (SKiDL-inspired)
# =============================================================================

# A3 sheet size in mm (landscape)
SHEET_WIDTH = 420.0
SHEET_HEIGHT = 297.0
SHEET_MARGIN = 20.0  # Margin from edges
POWER_NETS = {'+3V3', 'VBAT', 'VBUS', 'VCC', '+5V', 'GND'}  # Power nets
GRID_SIZE = 2.54  # KiCad grid in mm
ROUTING_CHANNEL = 5.0  # Extra space around parts for routing

# Reserved area for decoupling capacitors (bottom of sheet)
DECOUPLING_AREA_HEIGHT = 50.0  # mm reserved at bottom for decoupling caps
DECOUPLING_AREA_TOP = SHEET_HEIGHT - SHEET_MARGIN - DECOUPLING_AREA_HEIGHT  # Y where decoupling area starts

import random


@dataclass
class Vector:
    """2D vector for force calculations."""
    x: float
    y: float

    def __add__(self, other: 'Vector') -> 'Vector':
        return Vector(self.x + other.x, self.y + other.y)

    def __sub__(self, other: 'Vector') -> 'Vector':
        return Vector(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> 'Vector':
        return Vector(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar: float) -> 'Vector':
        if scalar == 0:
            return Vector(0, 0)
        return Vector(self.x / scalar, self.y / scalar)

    @property
    def magnitude(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y)

    def normalize(self) -> 'Vector':
        mag = self.magnitude
        if mag < 0.001:
            return Vector(0, 0)
        return Vector(self.x / mag, self.y / mag)


def get_part_bbox(part: PartInstance) -> Tuple[float, float, float, float]:
    """Get bounding box (x1, y1, x2, y2) for a part with spacing.

    Uses asymmetric y extents since symbols may not be centered at origin.
    In schematic coords (Y+ down): y_extent_up goes toward smaller Y (top),
    y_extent_down goes toward larger Y (bottom).
    """
    w = part.symbol.width / 2 + ROUTING_CHANNEL
    # Use asymmetric Y extents
    y_up = part.symbol.y_extent_up + ROUTING_CHANNEL  # Toward smaller Y (top)
    y_down = part.symbol.y_extent_down + ROUTING_CHANNEL  # Toward larger Y (bottom)
    return (
        part.position.x - w,
        part.position.y - y_up,  # Top edge (smaller Y)
        part.position.x + w,
        part.position.y + y_down  # Bottom edge (larger Y)
    )


def bboxes_intersect(b1: Tuple[float, float, float, float],
                     b2: Tuple[float, float, float, float]) -> bool:
    """Check if two bounding boxes intersect."""
    if b1[2] <= b2[0] or b2[2] <= b1[0]:  # No horizontal overlap
        return False
    if b1[3] <= b2[1] or b2[3] <= b1[1]:  # No vertical overlap
        return False
    return True


def compute_overlap_force(part: PartInstance, all_parts: List[PartInstance]) -> Vector:
    """
    Compute repulsive force from overlapping parts.

    When parts overlap, compute the minimum movement to separate them,
    and return that as a force vector.
    """
    total_force = Vector(0, 0)
    part_bbox = get_part_bbox(part)

    for other in all_parts:
        if other is part:
            continue

        other_bbox = get_part_bbox(other)

        if bboxes_intersect(part_bbox, other_bbox):
            # Compute movements needed to separate in each direction
            # Move part's right edge to other's left edge (negative x direction)
            move_left = other_bbox[0] - part_bbox[2]
            # Move part's left edge to other's right edge (positive x direction)
            move_right = other_bbox[2] - part_bbox[0]
            # Move part's top to other's bottom (negative y)
            move_up = other_bbox[1] - part_bbox[3]
            # Move part's bottom to other's top (positive y)
            move_down = other_bbox[3] - part_bbox[1]

            # Add small random offset to break symmetry
            rand_offset = Vector(random.random() * 0.5 - 0.25,
                                 random.random() * 0.5 - 0.25)

            # Choose the smallest move
            moves = [
                (abs(move_left), Vector(move_left, 0)),
                (abs(move_right), Vector(move_right, 0)),
                (abs(move_up), Vector(0, move_up)),
                (abs(move_down), Vector(0, move_down)),
            ]
            _, min_move = min(moves, key=lambda m: m[0])
            total_force = total_force + min_move + rand_offset

    return total_force


def compute_net_attraction(part: PartInstance, all_parts: List[PartInstance],
                           net_connections: Dict[str, List[Tuple[str, str]]]) -> Vector:
    """
    Compute attractive force from net connections.

    Parts connected by the same net attract each other.
    """
    total_force = Vector(0, 0)

    # Build set of parts this part is connected to
    connected_refs = set()
    for net_name, connections in net_connections.items():
        refs_in_net = {ref for ref, pin in connections}
        if part.ref in refs_in_net:
            connected_refs.update(refs_in_net - {part.ref})

    if not connected_refs:
        return total_force

    # Compute force toward each connected part
    part_by_ref = {p.ref: p for p in all_parts}
    force_count = 0

    for ref in connected_refs:
        other = part_by_ref.get(ref)
        if other and other is not part:
            # Vector from this part to the other part
            dx = other.position.x - part.position.x
            dy = other.position.y - part.position.y
            total_force = total_force + Vector(dx, dy)
            force_count += 1

    # Normalize by number of connections to prevent large parts from dominating
    if force_count > 0:
        total_force = total_force / force_count

    return total_force


def snap_to_grid(pos: Point) -> Point:
    """Snap position to KiCad grid."""
    return pos.snap(GRID_SIZE)


def constrain_to_sheet(pos: Point, allow_decoupling_area: bool = True,
                       half_width: float = 0, y_extent_up: float = 0,
                       y_extent_down: float = 0) -> Point:
    """Keep position within sheet bounds, accounting for asymmetric part size.

    Args:
        y_extent_up: How far part extends toward TOP of schematic (smaller Y)
        y_extent_down: How far part extends toward BOTTOM of schematic (larger Y)
    """
    # Ensure part edges stay within bounds
    x_min = SHEET_MARGIN + half_width
    x_max = SHEET_WIDTH - SHEET_MARGIN - half_width
    x = max(x_min, min(x_max, pos.x))

    # y_extent_up is toward smaller Y (top), so anchor Y must be >= margin + y_extent_up
    y_min = SHEET_MARGIN + y_extent_up
    if allow_decoupling_area:
        # y_extent_down is toward larger Y (bottom)
        y_max = SHEET_HEIGHT - SHEET_MARGIN - y_extent_down
    else:
        # Keep out of decoupling area at bottom
        y_max = DECOUPLING_AREA_TOP - y_extent_down
    y = max(y_min, min(y_max, pos.y))
    return Point(x, y)


def random_placement(parts: List[PartInstance], area_factor: float = 2.0):
    """
    Randomly place parts within an area sized to accommodate them.

    Args:
        parts: List of parts to place
        area_factor: Multiplier for the placement area (larger = more spread out)
    """
    if not parts:
        return

    # Calculate total area needed
    total_area = 0
    for part in parts:
        bbox = get_part_bbox(part)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        total_area += w * h

    # Size the placement area (use larger of calculated or usable sheet area fraction)
    side = math.sqrt(total_area) * area_factor
    usable_width = SHEET_WIDTH - 2 * SHEET_MARGIN
    usable_height = SHEET_HEIGHT - 2 * SHEET_MARGIN

    # Use at least 70% of the sheet for many parts
    if len(parts) > 30:
        side = max(side, min(usable_width, usable_height) * 0.8)

    # Center placement area on the sheet
    center_x = SHEET_WIDTH / 2
    center_y = SHEET_HEIGHT / 2

    # Place parts randomly across the area
    for part in parts:
        x = center_x + (random.random() - 0.5) * min(side, usable_width * 0.9)
        y = center_y + (random.random() - 0.5) * min(side, usable_height * 0.9)
        part.position = constrain_to_sheet(
            Point(x, y),
            half_width=part.symbol.width / 2,
            y_extent_up=part.symbol.y_extent_up,
            y_extent_down=part.symbol.y_extent_down
        )


def force_directed_placement(
    parts: List[PartInstance],
    net_connections: Dict[str, List[Tuple[str, str]]],
    max_iterations: int = 500,
    stability_threshold: float = 0.5,
    verbose: bool = True
):
    """
    Force-directed placement algorithm inspired by SKiDL.

    Uses physics simulation where:
    - Net connections create attractive forces between parts
    - Overlapping parts create repulsive forces
    - Alpha parameter transitions from attraction-dominated to repulsion-dominated

    Args:
        parts: Parts to place (positions will be modified)
        net_connections: Net name -> [(ref, pin_name), ...]
        max_iterations: Maximum iterations per alpha phase
        stability_threshold: Force threshold below which placement is stable
        verbose: Print progress info
    """
    if len(parts) <= 1:
        return

    # Force schedule: (speed, alpha, stability_coef)
    # alpha=0: pure attraction, alpha=1: pure repulsion
    # Modified: more aggressive repulsion phases
    force_schedule = [
        (0.4, 0.0, 0.1),    # Attractive forces only - bring connected parts together
        (0.3, 0.3, 0.05),   # Some repulsion
        (0.25, 0.6, 0.02),  # Balanced, more repulsion
        (0.2, 0.85, 0.01),  # Strong repulsion - spread overlapping parts
        (0.15, 1.0, 0.002), # Pure repulsion - final overlap removal
        (0.1, 1.0, 0.001),  # Extra pure repulsion pass
    ]

    if verbose:
        print(f"    Force-directed placement for {len(parts)} parts...")

    for phase, (speed, alpha, stability_coef) in enumerate(force_schedule):
        # Compute scale factor to balance attraction and repulsion
        # (simplified - SKiDL does this more elaborately)
        scale = 1.0

        stable_threshold = -1
        initial_force_sum = 0

        for iteration in range(max_iterations):
            # Compute forces on all parts
            forces = []
            total_force_magnitude = 0

            for part in parts:
                # Attractive force from net connections (weighted by 1-alpha)
                attr_force = compute_net_attraction(part, parts, net_connections)

                # Repulsive force from overlapping parts (weighted by alpha)
                repel_force = compute_overlap_force(part, parts)

                # Combined force with higher repulsion multiplier for large overlap forces
                # This helps push apart badly overlapping parts faster
                repel_mult = 1.5 if repel_force.magnitude > 10 else 1.0
                combined = attr_force * (scale * (1 - alpha)) + repel_force * (alpha * repel_mult)
                forces.append(combined)
                total_force_magnitude += combined.magnitude

            # Apply forces to positions
            for part, force in zip(parts, forces):
                new_x = part.position.x + force.x * speed
                new_y = part.position.y + force.y * speed
                part.position = constrain_to_sheet(
                    Point(new_x, new_y),
                    half_width=part.symbol.width / 2,
                    y_extent_up=part.symbol.y_extent_up,
                    y_extent_down=part.symbol.y_extent_down
                )

            # Check for stability
            if stable_threshold < 0:
                initial_force_sum = total_force_magnitude
                stable_threshold = total_force_magnitude * stability_coef
            elif total_force_magnitude <= stable_threshold:
                break
            elif total_force_magnitude > 10 * initial_force_sum:
                # Forces are increasing - reduce speed
                speed *= 0.5

        if verbose:
            print(f"      Phase {phase+1}: alpha={alpha:.1f}, iterations={iteration+1}, force={total_force_magnitude:.1f}")

    # Final snap to grid
    for part in parts:
        part.position = snap_to_grid(part.position)


def place_parts_by_group(
    parts: List[dict],
    symbols: Dict[str, SymbolDef],
    lcsc_to_symbol: Dict[str, str],
    **kwargs
) -> List[PartInstance]:
    """
    Place parts using semantic grouping (belongs_to attribute).

    Strategy:
    1. Create PartInstance objects for all parts
    2. Identify main parts (belongs_to=None) and peripheral parts
    3. Spread main parts across the sheet in a grid
    4. Place peripheral parts around their parent main part
    5. Use force-directed placement to resolve overlaps within each group
    6. Final overlap resolution pass
    """

    random.seed(42)  # Reproducible placement

    # Track symbols not found in library (populated by create_part_instance)
    missing_symbols: List[dict] = []

    # Helper function to create a PartInstance
    def create_part_instance(part_data: dict, position: Point) -> PartInstance:
        ref = part_data.get('ref', 'X?')
        value = part_data.get('value', '')
        lcsc = part_data.get('lcsc', '')
        footprint = part_data.get('footprint', '')
        pins = part_data.get('pins', {})
        belongs_to = part_data.get('belongs_to')

        sym_name = lcsc_to_symbol.get(lcsc, value)
        symbol = symbols.get(sym_name)

        if not symbol:
            # Track missing symbols for validation
            missing_symbols.append({
                'ref': ref,
                'lcsc': lcsc,
                'value': value,
                'sym_name': sym_name
            })
            symbol = SymbolDef(
                name=sym_name or "Unknown",
                lib_name="JLCPCB",
                pins={},
                properties={},
                raw_sexp="",
                width=20,
                height=20
            )

        # Scale Y coordinates for parts with multiple pins
        if len(symbol.pins) >= MIN_PINS_FOR_SCALING:
            symbol = scale_symbol_y(symbol, 2.0)

        return PartInstance(
            ref=ref,
            value=value,
            symbol=symbol,
            position=position,
            belongs_to=belongs_to,
            pins=pins,
            lcsc=lcsc,
            footprint=footprint
        )

    # ==========================================================================
    # Step 1: Create all PartInstances
    # ==========================================================================

    print(f"  Creating {len(parts)} part instances...")

    placed_parts: List[PartInstance] = []
    for part_data in parts:
        initial_pos = Point(SHEET_WIDTH / 2, SHEET_HEIGHT / 2)
        instance = create_part_instance(part_data, initial_pos)
        placed_parts.append(instance)

    # Validate: fail early if symbols are missing
    if missing_symbols:
        print("\n" + "="*60)
        print("  ERROR: Missing symbols in library!")
        print("="*60)
        print("\n  The following parts have no symbols in JLCPCB.kicad_sym:")
        for m in missing_symbols:
            print(f"    - {m['ref']}: LCSC={m['lcsc']}, value={m['value']}")
        print("\n  Run ensure_symbols.py first to download missing symbols:")
        print("    python scripts/ensure_symbols.py --parts work/step2_parts_complete.yaml")
        print("\n  Or manually add symbols using JLC2KiCadLib:")
        for m in missing_symbols:
            if m['lcsc']:
                print(f"    JLC2KiCadLib {m['lcsc']} -dir /tmp/jlc_temp")
        print("="*60 + "\n")
        raise ValueError(f"Missing {len(missing_symbols)} symbol(s) in library - cannot generate schematic")

    part_by_ref = {p.ref: p for p in placed_parts}

    # ==========================================================================
    # Step 2: Separate main parts from peripheral parts
    # ==========================================================================

    # Build mapping from semantic id to ref from parts data
    semantic_to_ref = {}
    for part_data in parts:
        part_id = part_data.get('id', '')
        ref = part_data.get('ref', '')
        if part_id and ref:
            semantic_to_ref[part_id] = ref

    # Main parts (belongs_to=None) - will be placed in grid
    main_parts: List[PartInstance] = []
    # Peripheral parts grouped by their parent's ref
    peripheral_groups: Dict[str, List[PartInstance]] = {}

    for part in placed_parts:
        if part.belongs_to is None:
            main_parts.append(part)
        else:
            parent_ref = semantic_to_ref.get(part.belongs_to)
            if parent_ref:
                if parent_ref not in peripheral_groups:
                    peripheral_groups[parent_ref] = []
                peripheral_groups[parent_ref].append(part)
            else:
                # Unknown belongs_to - treat as main part
                main_parts.append(part)

    print(f"  Main parts: {len(main_parts)}")
    print(f"  Peripheral groups: {len(peripheral_groups)}")
    for parent_ref, periph_list in peripheral_groups.items():
        print(f"    {parent_ref}: {len(periph_list)} parts")

    # ==========================================================================
    # Step 3: Place main parts in a grid across the sheet
    # ==========================================================================

    num_main = len(main_parts)
    if num_main == 0:
        print("  Warning: No main parts found!")
        return placed_parts

    # Calculate grid layout
    cols = max(1, int(math.ceil(math.sqrt(num_main * 1.5))))  # Wider than tall
    rows = max(1, int(math.ceil(num_main / cols)))

    # Use sheet area EXCLUDING the decoupling cap zone at bottom
    usable_width = SHEET_WIDTH - 2 * SHEET_MARGIN
    usable_height = DECOUPLING_AREA_TOP - SHEET_MARGIN  # Stop before decoupling area
    cell_width = usable_width / cols
    cell_height = usable_height / rows

    print(f"  Grid: {cols}x{rows}, cell size: {cell_width:.1f}x{cell_height:.1f}mm")

    # Sort main parts for consistent placement (ICs first, then connectors, etc.)
    def sort_key(p):
        ref = p.ref
        if ref.startswith('U'):
            return (0, ref)
        elif ref.startswith('J'):
            return (1, ref)
        elif ref.startswith('D'):
            return (2, ref)
        elif ref.startswith('ENC'):
            return (3, ref)
        elif ref.startswith('SW'):
            return (4, ref)
        elif ref.startswith('TP'):
            return (5, ref)
        else:
            return (6, ref)

    main_parts.sort(key=sort_key)

    main_positions: Dict[str, Point] = {}

    for idx, part in enumerate(main_parts):
        col = idx % cols
        row = idx // cols

        # Place at cell center
        x = SHEET_MARGIN + col * cell_width + cell_width / 2
        y = SHEET_MARGIN + row * cell_height + cell_height / 2

        # Constrain to sheet bounds accounting for asymmetric symbol size
        half_w = part.symbol.width / 2 + 5
        part.position = snap_to_grid(constrain_to_sheet(
            Point(x, y),
            allow_decoupling_area=False,
            half_width=half_w,
            y_extent_up=part.symbol.y_extent_up + 5,
            y_extent_down=part.symbol.y_extent_down + 5
        ))
        main_positions[part.ref] = part.position
        print(f"    {part.ref} at ({part.position.x:.1f}, {part.position.y:.1f})")

    # ==========================================================================
    # Step 4: Place peripheral parts near the pins they connect to
    # ==========================================================================

    print("  Placing peripheral parts near connected pins...")

    # Build net -> [(ref, pin_name)] mapping
    net_to_pins: Dict[str, List[Tuple[str, str]]] = {}
    for part in placed_parts:
        for pin_name, net_name in part.pins.items():
            if net_name:
                if net_name not in net_to_pins:
                    net_to_pins[net_name] = []
                net_to_pins[net_name].append((part.ref, pin_name))

    for parent_ref, periph_list in peripheral_groups.items():
        parent = part_by_ref.get(parent_ref)
        parent_pos = main_positions.get(parent_ref)
        if not parent or not parent_pos:
            print(f"    Warning: Parent {parent_ref} not found, skipping peripherals")
            continue

        num_periph = len(periph_list)
        print(f"    Placing {num_periph} parts around {parent_ref}")

        for p_idx, periph in enumerate(periph_list):
            # Find which nets connect this peripheral to the parent
            connected_pins = []
            for periph_pin, net_name in periph.pins.items():
                if not net_name:
                    continue
                # Check if parent has a pin on the same net
                for ref, pin_name in net_to_pins.get(net_name, []):
                    if ref == parent_ref:
                        # Get pin position on parent
                        pin_pos = get_pin_position(parent, pin_name)
                        if pin_pos:
                            connected_pins.append((pin_pos, pin_name))

            if connected_pins:
                # Place peripheral near the first connected pin
                target_pin_pos, pin_name = connected_pins[0]

                # Get pin info to determine direction to offset
                parent_pin = parent.symbol.pins.get(pin_name)
                offset_x, offset_y = -25.0, 0  # Default: place to the left

                if parent_pin:
                    # Pin rotation is direction FROM connection point TOWARD IC body
                    # Place peripheral in OPPOSITE direction (away from IC)
                    rot = parent_pin.rotation
                    if rot == 0:    # Pin goes right toward IC -> place LEFT of pin
                        offset_x, offset_y = -30.0, (p_idx % 3 - 1) * 10
                    elif rot == 180:  # Pin goes left toward IC -> place RIGHT of pin
                        offset_x, offset_y = 30.0, (p_idx % 3 - 1) * 10
                    elif rot == 90:   # Pin goes up toward IC -> place BELOW pin
                        offset_x, offset_y = (p_idx % 3 - 1) * 10, 30.0
                    elif rot == 270:  # Pin goes down toward IC -> place ABOVE pin
                        offset_x, offset_y = (p_idx % 3 - 1) * 10, -30.0

                px = target_pin_pos.x + offset_x
                py = target_pin_pos.y + offset_y
            else:
                # No direct connection found - place in circle around parent
                angle_deg = (360 / max(num_periph, 1)) * p_idx
                radius = 35.0 + (p_idx % 2) * 10
                angle_rad = math.radians(angle_deg)
                px = parent_pos.x + radius * math.cos(angle_rad)
                py = parent_pos.y + radius * math.sin(angle_rad)

            periph.position = snap_to_grid(constrain_to_sheet(
                Point(px, py),
                allow_decoupling_area=False,
                half_width=periph.symbol.width / 2,
                y_extent_up=periph.symbol.y_extent_up,
                y_extent_down=periph.symbol.y_extent_down
            ))

    # ==========================================================================
    # Step 5: Build net connections for force-directed refinement
    # ==========================================================================

    net_connections: Dict[str, List[Tuple[str, str]]] = {}
    for part in placed_parts:
        for pin_name, net_name in part.pins.items():
            if net_name:
                if net_name not in net_connections:
                    net_connections[net_name] = []
                net_connections[net_name].append((part.ref, pin_name))

    # ==========================================================================
    # Step 6: Force-directed refinement for peripherals only (parent stays fixed)
    # ==========================================================================

    print("  Force-directed refinement for peripherals (parents stay fixed)...")

    for parent_ref, periph_list in peripheral_groups.items():
        parent = part_by_ref.get(parent_ref)
        if not parent or len(periph_list) < 2:
            continue

        # Save parent position - it should NOT move
        parent_original_pos = parent.position

        # Only run force-directed on peripherals (not parent)
        # Get nets connecting peripherals to each other
        periph_refs = {p.ref for p in periph_list}
        periph_nets = {}
        for net_name, connections in net_connections.items():
            periph_conns = [(ref, pin) for ref, pin in connections if ref in periph_refs]
            if len(periph_conns) >= 2:
                periph_nets[net_name] = periph_conns

        if len(periph_list) > 1 and periph_nets:
            force_directed_placement(periph_list, periph_nets, max_iterations=100, verbose=False)

        # Ensure parent position is restored (should not have changed, but just in case)
        parent.position = parent_original_pos

    # ==========================================================================
    # Step 7: Final overlap check (NO force-directed - it breaks grouping)
    # ==========================================================================

    # Skip global force-directed placement - it moves peripherals away from parents
    # Only use deterministic overlap resolution below
    print("  Skipping global force-directed (preserves grouping)...")

    # ==========================================================================
    # Step 8: Place decoupling capacitors in a separate area
    # ==========================================================================

    print("  Placing decoupling capacitors in separate area...")

    # Power nets that indicate decoupling caps
    POWER_NETS = {'+3V3', 'VBAT', 'VBUS', 'VCC', '+5V'}

    # Identify decoupling caps
    decoupling_caps = []
    for part in placed_parts:
        if not part.ref.startswith('C'):
            continue
        nets = set(part.pins.values())
        has_gnd = 'GND' in nets
        has_power = bool(nets & POWER_NETS)
        if has_gnd and has_power:
            decoupling_caps.append(part)

    if decoupling_caps:
        print(f"    Found {len(decoupling_caps)} decoupling caps")

        # Place them in a row at the bottom of the sheet
        num_caps = len(decoupling_caps)
        caps_per_row = min(num_caps, 12)  # Max 12 per row
        cap_spacing = 15.0  # mm between caps

        start_x = SHEET_MARGIN + 20
        start_y = SHEET_HEIGHT - SHEET_MARGIN - 20  # Near bottom

        for i, cap in enumerate(decoupling_caps):
            row = i // caps_per_row
            col = i % caps_per_row
            cap.position = snap_to_grid(Point(
                start_x + col * cap_spacing,
                start_y - row * 12  # Stack rows upward if needed
            ))

    # ==========================================================================
    # Step 9: Restore main parts to their grid positions
    # ==========================================================================

    print("  Restoring main parts to grid positions...")

    # Restore main parts to their grid positions (they may have been moved by force-directed)
    for part in main_parts:
        if part.ref in main_positions:
            part.position = main_positions[part.ref]

    # ==========================================================================
    # Step 10: Guarantee no overlaps (must complete before routing)
    # ==========================================================================

    print("  Resolving ALL overlaps (required before routing)...")

    # Main parts should not be moved
    main_refs = {p.ref for p in main_parts}

    def get_overlapping_parts(part: PartInstance, all_parts: List[PartInstance]) -> List[PartInstance]:
        """Get list of parts that overlap with the given part."""
        result = []
        b1 = get_part_bbox(part)
        for other in all_parts:
            if other is part:
                continue
            b2 = get_part_bbox(other)
            if bboxes_intersect(b1, b2):
                result.append(other)
        return result

    def find_free_position(part: PartInstance, all_parts: List[PartInstance],
                           start_pos: Point, search_radius: float = 300.0,
                           allow_decoupling_area: bool = False) -> Point:
        """Find a position where part doesn't overlap with any other part.

        Args:
            allow_decoupling_area: If False, keeps part out of the reserved decoupling cap zone
        """
        step = 2.54  # Use grid step for precision

        # Try the start position first
        part.position = start_pos
        if not get_overlapping_parts(part, all_parts):
            return start_pos

        # Try positions in expanding spiral around start position
        for distance in range(int(step), int(search_radius), int(step)):
            # Try all positions at this distance
            for angle in range(0, 360, 15):
                angle_rad = math.radians(angle)
                dx = distance * math.cos(angle_rad)
                dy = distance * math.sin(angle_rad)
                test_pos = snap_to_grid(constrain_to_sheet(
                    Point(start_pos.x + dx, start_pos.y + dy),
                    allow_decoupling_area=allow_decoupling_area,
                    half_width=part.symbol.width / 2,
                    y_extent_up=part.symbol.y_extent_up,
                    y_extent_down=part.symbol.y_extent_down
                ))
                part.position = test_pos
                if not get_overlapping_parts(part, all_parts):
                    return test_pos

        # If spiral search fails, try grid search
        for dx in range(-int(search_radius), int(search_radius), int(step * 4)):
            for dy in range(-int(search_radius), int(search_radius), int(step * 4)):
                test_pos = snap_to_grid(constrain_to_sheet(
                    Point(start_pos.x + dx, start_pos.y + dy),
                    allow_decoupling_area=allow_decoupling_area,
                    half_width=part.symbol.width / 2,
                    y_extent_up=part.symbol.y_extent_up,
                    y_extent_down=part.symbol.y_extent_down
                ))
                part.position = test_pos
                if not get_overlapping_parts(part, all_parts):
                    return test_pos

        return start_pos  # Fallback (shouldn't happen)

    # Process parts - movable parts only
    movable_parts = [p for p in placed_parts if p.ref not in main_refs]

    # Identify decoupling cap refs (already placed in decoupling area)
    decoupling_refs = {cap.ref for cap in decoupling_caps}

    # Sort by size (larger parts first - harder to place)
    def part_area(p):
        b = get_part_bbox(p)
        return (b[2] - b[0]) * (b[3] - b[1])
    movable_parts.sort(key=part_area, reverse=True)

    for iteration in range(50):
        total_overlaps = 0

        for part in movable_parts:
            overlapping = get_overlapping_parts(part, placed_parts)
            if overlapping:
                total_overlaps += len(overlapping)
                # Find a free position
                # Decoupling caps can be placed in decoupling area; others cannot
                is_decoupling = part.ref in decoupling_refs
                original_pos = part.position
                new_pos = find_free_position(part, placed_parts, original_pos,
                                             allow_decoupling_area=is_decoupling)
                part.position = new_pos

        if total_overlaps == 0:
            print(f"    All overlaps resolved after {iteration + 1} iterations")
            break
    else:
        # Final check
        remaining = sum(1 for p in placed_parts
                       for _ in get_overlapping_parts(p, placed_parts)) // 2
        if remaining > 0:
            print(f"    Warning: {remaining} overlaps remain after {iteration + 1} iterations")

    # ==========================================================================
    # Step 9: Ensure all parts are within sheet bounds
    # ==========================================================================

    print("  Constraining all parts to sheet bounds...")
    for part in placed_parts:
        half_w = part.symbol.width / 2 + 5  # Add margin for labels
        is_decoupling = part.ref in decoupling_refs
        part.position = snap_to_grid(constrain_to_sheet(
            part.position,
            allow_decoupling_area=is_decoupling,
            half_width=half_w,
            y_extent_up=part.symbol.y_extent_up + 5,
            y_extent_down=part.symbol.y_extent_down + 5
        ))

    # Resolve any new overlaps caused by constraining
    for iteration in range(20):
        total_overlaps = 0
        for part in movable_parts:
            overlapping = get_overlapping_parts(part, placed_parts)
            if overlapping:
                total_overlaps += len(overlapping)
                is_decoupling = part.ref in decoupling_refs
                half_w = part.symbol.width / 2 + 5
                original_pos = part.position
                new_pos = find_free_position(part, placed_parts, original_pos,
                                             allow_decoupling_area=is_decoupling)
                # Re-constrain to sheet bounds
                part.position = snap_to_grid(constrain_to_sheet(
                    new_pos,
                    allow_decoupling_area=is_decoupling,
                    half_width=half_w,
                    y_extent_up=part.symbol.y_extent_up + 5,
                    y_extent_down=part.symbol.y_extent_down + 5
                ))
        if total_overlaps == 0:
            break

    # ==========================================================================
    # Step 10: Report final state
    # ==========================================================================

    overlap_count = 0
    for i, p1 in enumerate(placed_parts):
        b1 = get_part_bbox(p1)
        for p2 in placed_parts[i+1:]:
            b2 = get_part_bbox(p2)
            if bboxes_intersect(b1, b2):
                overlap_count += 1

    if overlap_count > 0:
        print(f"  Warning: {overlap_count} overlapping part pairs detected")
    else:
        print(f"  All {len(placed_parts)} parts placed without overlaps")

    return placed_parts


# =============================================================================
# Pin Position and Net Label Support
# =============================================================================

def get_pin_position(part: PartInstance, pin_name: str) -> Optional[Point]:
    """Get the absolute position of a pin on a placed part.

    IMPORTANT: Returns exact position, NOT snapped.
    KiCad requires wire endpoints to be at exact pin positions.
    """

    if pin_name not in part.symbol.pins:
        return None

    pin = part.symbol.pins[pin_name]

    # In KiCad symbol definitions, pin (at x y) IS the connection point (tip of pin)
    # The pin extends FROM this point TOWARD the symbol body
    # Symbol coordinate system: Y increases upward
    # Schematic coordinate system: Y increases downward
    # So we need to invert Y when converting from symbol to schematic coords

    pin_x = part.position.x + pin.x
    pin_y = part.position.y - pin.y  # Y is inverted

    return Point(pin_x, pin_y)  # No snapping - exact position!


def route_nets(
    parts: List[PartInstance],
    nets: Dict[str, List[Tuple[str, str]]]  # net_name -> [(ref, pin_name), ...]
) -> Tuple[List[Wire], Set[Point], Dict[str, List[Point]]]:
    """
    Collect pin positions for net labels.

    All nets use labels instead of wire routing. This avoids wire routing issues
    where wires could accidentally pass through pin positions and cause KiCad
    to merge unrelated nets.

    Returns:
        wires: Empty list (no wire routing)
        junctions: Empty set (no junctions needed)
        label_positions: Dict of net_name -> [pin_positions] for label placement
    """
    label_positions: Dict[str, List[Point]] = {}

    # Build ref -> part lookup
    part_by_ref = {p.ref: p for p in parts}

    print(f"    Collecting pin positions for {len(parts)} parts")

    for net_name, connections in nets.items():
        if len(connections) < 2:
            continue

        # Get pin positions for this net
        pin_positions = []
        for ref, pin_name in connections:
            part = part_by_ref.get(ref)
            if not part:
                continue
            pin_pos = get_pin_position(part, pin_name)
            if pin_pos:
                pin_positions.append(pin_pos)

        if len(pin_positions) >= 2:
            # Use labels for all nets - cleaner and avoids routing issues
            label_positions[net_name] = pin_positions

    return [], set(), label_positions


def build_net_connections(parts: List[PartInstance]) -> Dict[str, List[Tuple[str, str]]]:
    """Build net -> [(ref, pin_name), ...] mapping from parts."""

    nets: Dict[str, List[Tuple[str, str]]] = {}

    for part in parts:
        for pin_name, net_name in part.pins.items():
            if net_name:
                if net_name not in nets:
                    nets[net_name] = []
                nets[net_name].append((part.ref, pin_name))

    return nets


# =============================================================================
# Schematic Generator
# =============================================================================

MAX_LABEL_LENGTH = 10  # Maximum characters for net labels


def shorten_net_names(net_names: List[str]) -> Dict[str, str]:
    """Create mapping from full net names to shortened names (max 10 chars).

    Ensures uniqueness by appending numbers if needed.
    """
    mapping = {}
    used_names = set()

    for net in net_names:
        if len(net) <= MAX_LABEL_LENGTH:
            short = net
        else:
            # Truncate to max length
            short = net[:MAX_LABEL_LENGTH]

        # Ensure uniqueness
        if short in used_names:
            # Try adding numbers
            base = short[:MAX_LABEL_LENGTH - 2]
            for i in range(1, 100):
                candidate = f"{base}{i:02d}"
                if candidate not in used_names:
                    short = candidate
                    break

        mapping[net] = short
        used_names.add(short)

    return mapping


def generate_schematic(
    parts: List[PartInstance],
    wires: List[Wire],
    junctions: Set[Point],
    symbols: Dict[str, SymbolDef],
    label_positions: Dict[str, List[Point]] = None,
    title: str = "SKiDL Generated Schematic",
    output_path: Path = None
) -> str:
    """Generate complete KiCad 9 schematic file."""
    if label_positions is None:
        label_positions = {}

    # Build shortened net name mapping
    net_name_map = shorten_net_names(list(label_positions.keys()))

    # Identify power nets that need PWR_FLAG
    # Only add PWR_FLAG to GND and input power nets from connectors
    # Only GND needs PWR_FLAG - other power nets already have power output pins:
    # - +3V3: AMS1117 VOUT (power output)
    # - VBAT: TP4056 BAT (power output)
    # - VBUS: USB connector VBUS (power output in symbol)
    POWER_NETS_NEED_FLAG = {'GND'}  # Only GND has no power output pin
    power_nets_used = set()
    for net_name in label_positions.keys():
        if net_name in POWER_NETS_NEED_FLAG:
            power_nets_used.add(net_name)

    # Find pins that need no-connect flags
    # These are pins that exist in the symbol but have no net assignment
    no_connect_positions = []
    for part in parts:
        # Get all pin names from the symbol definition
        symbol_pin_names = set(part.symbol.pins.keys())
        # Get pin names that have net assignments
        connected_pin_names = set(part.pins.keys())
        # Unconnected pins are in symbol but not in part.pins
        unconnected_pin_names = symbol_pin_names - connected_pin_names

        for pin_name in unconnected_pin_names:
            pin_pos = get_pin_position(part, pin_name)
            if pin_pos:
                no_connect_positions.append(pin_pos)

    sexp = SexpWriter()

    # Generate root UUID for the schematic
    root_uuid = generate_uuid()

    # Header
    sexp.open("kicad_sch")
    sexp.atom("version", "20250114")
    sexp.atom("generator", "eeschema")
    sexp.atom("generator_version", '"9.0"')
    sexp.atom("uuid", root_uuid)
    sexp.atom("paper", "A3")

    # Title block
    sexp.open("title_block")
    sexp.atom("title", title)
    sexp.atom("date", datetime.now().strftime("%Y-%m-%d"))
    sexp.atom("rev", '"1.0"')
    sexp.atom("comment", "1", "Generated by SKiDL KiCad 9 Generator")
    sexp.close()

    # Lib symbols - embed all used symbols
    sexp.open("lib_symbols")
    used_symbols = set()
    for part in parts:
        lib_sym_name = f"{part.symbol.lib_name}:{part.symbol.name}"
        if lib_sym_name not in used_symbols and part.symbol.raw_sexp:
            # Rewrite the symbol with library prefix and proper format
            raw = part.symbol.raw_sexp.strip()

            # Replace symbol name with prefixed version and fix attribute ordering
            # KiCad 9 expects: (symbol "LIB:NAME" \n (exclude_from_sim no) \n (in_bom yes) \n (on_board yes)
            # Our source has: (symbol "NAME" (in_bom yes) (on_board yes)

            # First, extract in_bom and on_board values
            in_bom_match = re.search(r'\(in_bom\s+(\w+)\)', raw)
            on_board_match = re.search(r'\(on_board\s+(\w+)\)', raw)
            in_bom = in_bom_match.group(1) if in_bom_match else 'yes'
            on_board = on_board_match.group(1) if on_board_match else 'yes'

            # Remove in_bom and on_board from the first line
            raw = re.sub(r'\s*\(in_bom\s+\w+\)', '', raw)
            raw = re.sub(r'\s*\(on_board\s+\w+\)', '', raw)

            # Replace symbol name with prefixed version
            raw = re.sub(
                r'\(symbol\s+"' + re.escape(part.symbol.name) + r'"',
                f'(symbol "{lib_sym_name}"',
                raw
            )

            # Insert properly formatted attributes after the symbol opening line
            # Find the first newline after (symbol "NAME" and insert attributes
            first_newline = raw.find('\n')
            if first_newline > 0:
                raw = (raw[:first_newline] +
                       '\n\t\t\t(exclude_from_sim no)' +
                       f'\n\t\t\t(in_bom {in_bom})' +
                       f'\n\t\t\t(on_board {on_board})' +
                       raw[first_newline:])

            # Write with proper indentation (convert 2-space to tabs)
            for line in raw.split('\n'):
                # Count leading spaces and convert to tabs
                stripped = line.lstrip()
                if not stripped:
                    continue
                spaces = len(line) - len(stripped)
                tabs = "\t\t" + "\t" * (spaces // 2)  # Base indent + converted spaces
                sexp.lines.append(tabs + stripped)

            used_symbols.add(lib_sym_name)

    # Add PWR_FLAG symbol if we have power nets
    if power_nets_used:
        pwr_flag_sym = '''		(symbol "power:PWR_FLAG"
			(power)
			(pin_numbers hide)
			(pin_names (offset 0) hide)
			(exclude_from_sim no)
			(in_bom no)
			(on_board yes)
			(property "Reference" "#FLG" (at 0 1.905 0) (effects (font (size 1.27 1.27)) hide))
			(property "Value" "PWR_FLAG" (at 0 3.81 0) (effects (font (size 1.27 1.27))))
			(property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
			(property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
			(property "Description" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
			(symbol "PWR_FLAG_0_0"
				(pin power_out line (at 0 0 90) (length 0)
					(name "pwr" (effects (font (size 1.27 1.27))))
					(number "1" (effects (font (size 1.27 1.27))))
				)
			)
			(symbol "PWR_FLAG_0_1"
				(polyline
					(pts (xy 0 0) (xy 0 1.27) (xy -1.016 1.905) (xy 0 2.54) (xy 1.016 1.905) (xy 0 1.27))
					(stroke (width 0) (type default))
					(fill (type none))
				)
			)
		)'''
        sexp.lines.append(pwr_flag_sym)

    sexp.close()  # lib_symbols

    # No-connect flags for unconnected pins
    for pos in no_connect_positions:
        sexp.open("no_connect")
        sexp.atom("at", f"{pos.x:.2f}", f"{pos.y:.2f}")
        sexp.atom("uuid", generate_uuid())
        sexp.close()

    # Junctions
    for junction in junctions:
        sexp.open("junction")
        sexp.atom("at", f"{junction.x:.2f}", f"{junction.y:.2f}")
        sexp.atom("diameter", "0")
        sexp.atom("color", "0", "0", "0", "0")
        sexp.atom("uuid", generate_uuid())
        sexp.close()

    # Wires
    for wire in wires:
        sexp.open("wire")
        sexp.open("pts")
        sexp.atom("xy", f"{wire.start.x:.2f}", f"{wire.start.y:.2f}")
        sexp.atom("xy", f"{wire.end.x:.2f}", f"{wire.end.y:.2f}")
        sexp.close()  # pts
        sexp.open("stroke")
        sexp.atom("width", "0")
        sexp.atom("type", "default")  # KiCad expects unquoted
        sexp.close()  # stroke
        sexp.atom("uuid", generate_uuid())
        sexp.close()  # wire

    # Net labels for multi-pin nets (these use labels instead of wires)
    # Add short wire stubs from pins with labels at the end
    # Direction is determined by pin orientation to place label outside IC
    STUB_LENGTH = 2.54  # 1 grid unit stub length (minimum)

    for net_name, positions in label_positions.items():
        for pos in positions:
            # Determine stub direction based on which part this pin belongs to
            # Default: extend to the right
            stub_dx, stub_dy = STUB_LENGTH, 0
            label_angle = 0
            justify = "left"

            # Find which part owns this pin position to get pin orientation
            vjustify = "bottom"  # Vertical justify for label
            for part in parts:
                for pin_name, pnet in part.pins.items():
                    if pnet == net_name:
                        pin_pos = get_pin_position(part, pin_name)
                        if pin_pos and abs(pin_pos.x - pos.x) < 0.1 and abs(pin_pos.y - pos.y) < 0.1:
                            # Found the pin - get its orientation
                            pin = part.symbol.pins.get(pin_name)
                            if pin:
                                rot = pin.rotation
                                # Pin rotation is direction FROM connection point TOWARD IC body
                                # Stub should go in OPPOSITE direction (away from IC)
                                if rot == 0:    # Pin goes right toward IC -> stub goes LEFT
                                    stub_dx, stub_dy = -STUB_LENGTH, 0
                                    label_angle = 0
                                    justify = "right"
                                elif rot == 180:  # Pin goes left toward IC -> stub goes RIGHT
                                    stub_dx, stub_dy = STUB_LENGTH, 0
                                    label_angle = 0
                                    justify = "left"
                                elif rot == 90:   # Pin goes up toward IC -> stub goes DOWN (below part)
                                    stub_dx, stub_dy = 0, STUB_LENGTH  # Y increases downward in schematic
                                    label_angle = 90
                                    justify = "right"  # Text flows away from stub end
                                    vjustify = "bottom"
                                elif rot == 270:  # Pin goes down toward IC -> stub goes UP (above part)
                                    stub_dx, stub_dy = 0, -STUB_LENGTH
                                    label_angle = 90
                                    justify = "left"  # Text flows away from stub end
                                    vjustify = "bottom"
                            break

            stub_end_x = pos.x + stub_dx
            stub_end_y = pos.y + stub_dy

            # Wire stub
            sexp.open("wire")
            sexp.open("pts")
            sexp.atom("xy", f"{pos.x:.2f}", f"{pos.y:.2f}")
            sexp.atom("xy", f"{stub_end_x:.2f}", f"{stub_end_y:.2f}")
            sexp.close()  # pts
            sexp.open("stroke")
            sexp.atom("width", "0")
            sexp.atom("type", "default")
            sexp.close()  # stroke
            sexp.atom("uuid", generate_uuid())
            sexp.close()  # wire

            # Label at end of stub (use shortened name)
            short_name = net_name_map.get(net_name, net_name)
            sexp.open("label", short_name)
            sexp.atom("at", f"{stub_end_x:.2f}", f"{stub_end_y:.2f}", str(label_angle))
            sexp.open("effects")
            sexp.open("font")
            sexp.atom("size", "1.27", "1.27")
            sexp.close()  # font
            sexp.atom("justify", justify, vjustify)
            sexp.close()  # effects
            sexp.atom("uuid", generate_uuid())
            sexp.close()  # label

    # Symbol instances
    for part in parts:
        sym = part.symbol
        lib_sym_name = f"{sym.lib_name}:{sym.name}"
        sexp.open("symbol")
        sexp.atom("lib_id", lib_sym_name)
        sexp.atom("at", f"{part.position.x:.2f}", f"{part.position.y:.2f}", str(part.rotation))
        sexp.atom("unit", "1")
        sexp.atom("exclude_from_sim", "no")
        sexp.atom("in_bom", "yes")
        sexp.atom("on_board", "yes")
        sexp.atom("dnp", "no")
        sexp.atom("uuid", generate_uuid())

        # Properties
        sexp.open("property", "Reference", part.ref)
        sexp.atom("at", f"{part.position.x:.2f}", f"{part.position.y - 5:.2f}", "0")
        sexp.open("effects")
        sexp.open("font")
        sexp.atom("size", "1.27", "1.27")
        sexp.close()
        sexp.close()
        sexp.close()  # property Reference

        sexp.open("property", "Value", part.value)
        sexp.atom("at", f"{part.position.x:.2f}", f"{part.position.y + 5:.2f}", "0")
        sexp.open("effects")
        sexp.open("font")
        sexp.atom("size", "1.27", "1.27")
        sexp.close()
        sexp.close()
        sexp.close()  # property Value

        sexp.open("property", "Footprint", part.footprint)
        sexp.atom("at", f"{part.position.x:.2f}", f"{part.position.y:.2f}", "0")
        sexp.open("effects")
        sexp.open("font")
        sexp.atom("size", "1.27", "1.27")
        sexp.close()
        sexp.atom("hide", "yes")
        sexp.close()
        sexp.close()  # property Footprint

        sexp.open("property", "Datasheet", "")
        sexp.atom("at", f"{part.position.x:.2f}", f"{part.position.y:.2f}", "0")
        sexp.open("effects")
        sexp.open("font")
        sexp.atom("size", "1.27", "1.27")
        sexp.close()
        sexp.atom("hide", "yes")
        sexp.close()
        sexp.close()  # property Datasheet

        sexp.open("property", "Description", "")
        sexp.atom("at", f"{part.position.x:.2f}", f"{part.position.y:.2f}", "0")
        sexp.open("effects")
        sexp.open("font")
        sexp.atom("size", "1.27", "1.27")
        sexp.close()
        sexp.atom("hide", "yes")
        sexp.close()
        sexp.close()  # property Description

        # Pin UUIDs
        for pin_name in sym.pins:
            sexp.open("pin", f'"{sym.pins[pin_name].number}"')
            sexp.atom("uuid", generate_uuid())
            sexp.close()

        # Instances
        sexp.open("instances")
        sexp.open("project", '""')
        sexp.open("path", f'"/{root_uuid}"')
        sexp.atom("reference", part.ref)
        sexp.atom("unit", "1")
        sexp.close()  # path
        sexp.close()  # project
        sexp.close()  # instances

        sexp.close()  # symbol

    # PWR_FLAG symbol instances for power nets
    # Place them in a dedicated row at the top of the sheet with their own labels
    pwr_flag_num = 1
    pwr_flag_start_x = SHEET_MARGIN + 30
    pwr_flag_y = SHEET_MARGIN + 10  # Near top of sheet
    pwr_flag_spacing = 25.0

    for idx, net_name in enumerate(sorted(power_nets_used)):
        flag_x = pwr_flag_start_x + idx * pwr_flag_spacing
        flag_y = pwr_flag_y

        # PWR_FLAG symbol (pin at bottom, pointing down)
        sexp.open("symbol")
        sexp.atom("lib_id", "power:PWR_FLAG")
        sexp.atom("at", f"{flag_x:.2f}", f"{flag_y:.2f}", "180")  # Rotated 180 so pin points down
        sexp.atom("unit", "1")
        sexp.atom("exclude_from_sim", "no")
        sexp.atom("in_bom", "no")
        sexp.atom("on_board", "yes")
        sexp.atom("dnp", "no")
        sexp.atom("uuid", generate_uuid())

        sexp.open("property", "Reference", f"#FLG{pwr_flag_num:02d}")
        sexp.atom("at", f"{flag_x:.2f}", f"{flag_y - 5:.2f}", "0")
        sexp.open("effects")
        sexp.open("font")
        sexp.atom("size", "1.27", "1.27")
        sexp.close()
        sexp.atom("hide", "yes")
        sexp.close()
        sexp.close()

        sexp.open("property", "Value", "PWR_FLAG")
        sexp.atom("at", f"{flag_x:.2f}", f"{flag_y - 7:.2f}", "0")
        sexp.open("effects")
        sexp.open("font")
        sexp.atom("size", "1.27", "1.27")
        sexp.close()
        sexp.close()
        sexp.close()

        sexp.open("property", "Footprint", "")
        sexp.atom("at", f"{flag_x:.2f}", f"{flag_y:.2f}", "0")
        sexp.open("effects")
        sexp.open("font")
        sexp.atom("size", "1.27", "1.27")
        sexp.close()
        sexp.atom("hide", "yes")
        sexp.close()
        sexp.close()

        sexp.open("property", "Datasheet", "")
        sexp.atom("at", f"{flag_x:.2f}", f"{flag_y:.2f}", "0")
        sexp.open("effects")
        sexp.open("font")
        sexp.atom("size", "1.27", "1.27")
        sexp.close()
        sexp.atom("hide", "yes")
        sexp.close()
        sexp.close()

        sexp.open("property", "Description", "")
        sexp.atom("at", f"{flag_x:.2f}", f"{flag_y:.2f}", "0")
        sexp.open("effects")
        sexp.open("font")
        sexp.atom("size", "1.27", "1.27")
        sexp.close()
        sexp.atom("hide", "yes")
        sexp.close()
        sexp.close()

        sexp.open("pin", '"1"')
        sexp.atom("uuid", generate_uuid())
        sexp.close()

        sexp.open("instances")
        sexp.open("project", '""')
        sexp.open("path", f'"/{root_uuid}"')
        sexp.atom("reference", f"#FLG{pwr_flag_num:02d}")
        sexp.atom("unit", "1")
        sexp.close()
        sexp.close()
        sexp.close()

        sexp.close()  # symbol

        # Add short wire stub from PWR_FLAG (pointing down from rotated symbol)
        wire_end_y = flag_y + 5.08
        sexp.open("wire")
        sexp.open("pts")
        sexp.atom("xy", f"{flag_x:.2f}", f"{flag_y:.2f}")
        sexp.atom("xy", f"{flag_x:.2f}", f"{wire_end_y:.2f}")
        sexp.close()
        sexp.open("stroke")
        sexp.atom("width", "0")
        sexp.atom("type", "default")
        sexp.close()
        sexp.atom("uuid", generate_uuid())
        sexp.close()

        # Add label for the power net at end of wire
        short_name = net_name_map.get(net_name, net_name)
        sexp.open("label", short_name)
        sexp.atom("at", f"{flag_x:.2f}", f"{wire_end_y:.2f}", "270")
        sexp.open("effects")
        sexp.open("font")
        sexp.atom("size", "1.27", "1.27")
        sexp.close()
        sexp.atom("justify", "left")
        sexp.close()
        sexp.atom("uuid", generate_uuid())
        sexp.close()

        pwr_flag_num += 1

    # Footer
    sexp.open("sheet_instances")
    sexp.open("path", '"/"')
    sexp.atom("page", '"1"')
    sexp.close()
    sexp.close()

    sexp.atom("embedded_fonts", "no")
    sexp.close()  # kicad_sch

    output = sexp.get_output()

    if output_path:
        output_path.write_text(output, encoding='utf-8')
        print(f"Generated: {output_path}")

    return output


# =============================================================================
# Main Entry Point
# =============================================================================

def generate_from_pin_model(
    pin_model_path: Path,
    symbol_lib_path: Path,
    output_path: Path,
    title: str = "SKiDL Generated Schematic"
):
    """
    Generate KiCad 9 schematic from pin_model.json.

    Args:
        pin_model_path: Path to pin_model.json
        symbol_lib_path: Path to .kicad_sym library
        output_path: Output .kicad_sch path
        title: Schematic title
    """

    # Load pin model
    with open(pin_model_path, 'r', encoding='utf-8') as f:
        model = json.load(f)

    parts_data = model.get('parts', [])
    nets_list = model.get('nets', [])

    # Parse symbol library
    print(f"Parsing symbol library: {symbol_lib_path}")
    symbols = parse_kicad_sym(symbol_lib_path)
    print(f"  Found {len(symbols)} symbols")

    # Build LCSC to symbol mapping dynamically from library
    lcsc_to_symbol = build_lcsc_to_symbol(symbols)

    # Place parts with grouping
    print(f"Placing {len(parts_data)} parts...")
    placed_parts = place_parts_by_group(parts_data, symbols, lcsc_to_symbol)

    # Build net connections
    net_connections = build_net_connections(placed_parts)
    print(f"  Found {len(net_connections)} nets")

    # Collect pin positions for net labels
    print("Generating net labels...")
    wires, junctions, label_positions = route_nets(placed_parts, net_connections)
    print(f"  Nets with labels: {len(label_positions)}")

    # Generate schematic
    print("Generating schematic...")
    generate_schematic(
        placed_parts,
        wires,
        junctions,
        symbols,
        label_positions=label_positions,
        title=title,
        output_path=output_path
    )

    print(f"\nDone! Output: {output_path}")
    print(f"  Parts: {len(placed_parts)}")
    print(f"  Net labels: {sum(len(positions) for positions in label_positions.values())}")


def generate_debug_schematic(
    pin_model_path: Path,
    symbol_lib_path: Path,
    output_dir: Path,
    filter_refs: List[str] = None,
    title: str = "Debug Schematic"
):
    """
    Generate debug schematic with optional connection filtering.

    Always outputs to Debug.kicad_sch and debug.csv in output_dir.

    Args:
        pin_model_path: Path to pin_model.json
        symbol_lib_path: Path to .kicad_sym library
        output_dir: Directory for Debug.kicad_sch and debug.csv
        filter_refs: If provided, only include connections involving these refs (e.g., ["ENC1"])
        title: Schematic title
    """
    import csv

    # Load pin model
    with open(pin_model_path, 'r', encoding='utf-8') as f:
        model = json.load(f)

    parts_data = model.get('parts', [])

    # Parse symbol library
    print(f"Parsing symbol library: {symbol_lib_path}")
    symbols = parse_kicad_sym(symbol_lib_path)
    print(f"  Found {len(symbols)} symbols")

    # Build dynamic LCSC to symbol mapping from parsed symbols
    lcsc_to_symbol = build_lcsc_to_symbol(symbols)
    print(f"  LCSC mappings: {len(lcsc_to_symbol)}")

    # Place ALL parts (keep all parts in schematic)
    print(f"Placing {len(parts_data)} parts...")
    placed_parts = place_parts_by_group(parts_data, symbols, lcsc_to_symbol)

    # Build ALL net connections
    all_net_connections = build_net_connections(placed_parts)

    # Filter connections if filter_refs specified
    if filter_refs:
        filtered_nets = {}
        for net_name, connections in all_net_connections.items():
            # Check if any connection involves a filtered ref
            filtered_conns = [c for c in connections if c[0] in filter_refs]
            if filtered_conns:
                # Include all connections for this net (not just filtered ones)
                filtered_nets[net_name] = connections
        net_connections = filtered_nets
        print(f"  Filtered to {len(net_connections)} nets involving {filter_refs}")
    else:
        net_connections = all_net_connections

    print(f"  Total nets: {len(net_connections)}")

    # Generate net labels
    print("Generating net labels...")
    wires, junctions, label_positions = route_nets(placed_parts, net_connections)
    print(f"  Nets with labels: {len(label_positions)}")

    # Build ref -> part lookup for CSV generation
    part_by_ref = {p.ref: p for p in placed_parts}

    # Generate CSV with connection details
    csv_path = output_dir / "debug.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['net', 'ref', 'chip', 'pin_name', 'pin_number', 'x', 'y'])

        for net_name, connections in sorted(net_connections.items()):
            for ref, pin_name in connections:
                part = part_by_ref.get(ref)
                if part:
                    pos = get_pin_position(part, pin_name)
                    pin = part.symbol.pins.get(pin_name)
                    pin_num = pin.number if pin else '?'
                    x = f"{pos.x:.2f}" if pos else '?'
                    y = f"{pos.y:.2f}" if pos else '?'
                    writer.writerow([net_name, ref, part.symbol.name, pin_name, pin_num, x, y])

    print(f"Generated: {csv_path}")

    # Generate schematic
    sch_path = output_dir / "Debug.kicad_sch"
    print("Generating schematic...")
    generate_schematic(
        placed_parts,
        wires,
        junctions,
        symbols,
        label_positions=label_positions,
        title=title,
        output_path=sch_path
    )

    print(f"\nDebug output complete!")
    print(f"  Schematic: {sch_path}")
    print(f"  CSV: {csv_path}")
    print(f"  Parts: {len(placed_parts)}")
    print(f"  Nets with labels: {len(label_positions)}")
    if filter_refs:
        print(f"  Filtered by: {filter_refs}")


if __name__ == "__main__":
    import sys

    script_dir = Path(__file__).parent
    tools_dir = script_dir.parent  # KiCAD-Generator-tools directory

    # Try to find project directory (check cwd first, then tools_dir)
    cwd = Path.cwd()
    if (cwd / "work" / "pin_model.json").exists():
        base_dir = cwd
    else:
        base_dir = tools_dir

    pin_model = base_dir / "work" / "pin_model.json"
    output_dir = base_dir / "output"

    # Use central library (shared across all projects)
    central_library = tools_dir / "libs" / "JLCPCB" / "symbol" / "JLCPCB.kicad_sym"
    if central_library.exists():
        symbol_lib = central_library
    else:
        # Fall back to project-local library
        symbol_lib = base_dir / "output" / "libs" / "JLCPCB" / "symbol" / "JLCPCB.kicad_sym"

    # Check for debug mode with optional filter
    if len(sys.argv) > 1 and sys.argv[1] == "--debug":
        # Debug mode: generate Debug.kicad_sch and debug.csv
        filter_refs = sys.argv[2:] if len(sys.argv) > 2 else None
        generate_debug_schematic(
            pin_model,
            symbol_lib,
            output_dir,
            filter_refs=filter_refs,
            title="Debug - " + (", ".join(filter_refs) if filter_refs else "All Connections")
        )
    else:
        # Normal mode: generate full schematic
        output = output_dir / "Schematic.kicad_sch"
        generate_from_pin_model(
            pin_model,
            symbol_lib,
            output,
            title="Generated Schematic"
        )
