#!/usr/bin/env python3
"""
EasyEDA Parser - PCB to YAML Converter
Converts EasyEDA Pro exports (BOM + Pick & Place + Netlist) to YAML for AI analysis.

Algorithm: Progressive verbosity reduction
- Start at maximum verbosity (5)
- Generate YAML, count tokens
- If over token limit, reduce verbosity by 1
- Repeat until under limit or at minimum (1)

Usage:
  python easyparser.py BOM.xlsx PickPlace.xlsx Netlist.enet
  python easyparser.py BOM.xlsx PickPlace.xlsx Netlist.enet --token-limit 50000
  python easyparser.py BOM.xlsx PickPlace.xlsx Netlist.enet --verbosity 3
"""

import pandas as pd
import json
import yaml
import tiktoken
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import traceback
from datetime import datetime

# ============================================================================
# PARSING FUNCTIONS
# ============================================================================
def parse_bom(bom_file: str) -> Dict[str, Dict]:
    """Parse BOM Excel file with comma-separated designators."""
    try:
        df = pd.read_excel(bom_file, dtype=str)
        bom_data = {}
        
        # Find designator column (case-insensitive)
        designator_col = None
        for col in df.columns:
            if 'designator' in col.lower():
                designator_col = col
                break
        
        if not designator_col:
            print("Error: No 'Designator' column found in BOM")
            print(f"Available columns: {list(df.columns)}")
            return {}
        
        for idx, row in df.iterrows():
            designator_str = str(row.get(designator_col, '')).strip()
            if not designator_str or designator_str.lower() == 'nan':
                continue
                
            designators = [d.strip() for d in designator_str.split(',')]
            
            for designator in designators:
                if designator:
                    row_dict = {}
                    for col in df.columns:
                        value = row[col]
                        if pd.isna(value):
                            row_dict[col] = None
                        else:
                            row_dict[col] = str(value)
                    
                    bom_data[designator] = row_dict
        
        return bom_data
        
    except Exception as e:
        print(f"Error parsing BOM: {e}")
        traceback.print_exc()
        return {}

def parse_pickplace(pp_file: str) -> Dict[str, Dict]:
    """Parse Pick & Place Excel file."""
    try:
        df = pd.read_excel(pp_file, dtype=str)
        pp_data = {}
        
        designator_col = None
        for col in df.columns:
            if 'designator' in col.lower():
                designator_col = col
                break
        
        if not designator_col:
            designator_col = df.columns[0]
        
        for idx, row in df.iterrows():
            designator = str(row.get(designator_col, '')).strip()
            if not designator or designator.lower() == 'nan':
                continue
            
            row_dict = {}
            for col in df.columns:
                value = row[col]
                if pd.isna(value):
                    row_dict[col] = None
                else:
                    try:
                        if 'x' in col.lower() or 'y' in col.lower():
                            str_val = str(value).replace('mm', '').strip()
                            row_dict[col] = float(str_val)
                        elif 'rotation' in col.lower():
                            row_dict[col] = float(str(value))
                        else:
                            row_dict[col] = str(value)
                    except:
                        row_dict[col] = str(value)
            
            pp_data[designator] = row_dict
        
        return pp_data
        
    except Exception as e:
        print(f"Error parsing PickPlace: {e}")
        traceback.print_exc()
        return {}

def parse_netlist(netlist_file: str) -> Dict[str, Dict]:
    """Parse Netlist JSON file."""
    try:
        with open(netlist_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                lines = content.split('\n')
                data = {}
                for line in lines:
                    line = line.strip()
                    if line:
                        try:
                            item = json.loads(line)
                            if isinstance(item, dict):
                                data.update(item)
                        except:
                            continue
        
        netlist_data = {}
        
        for uid, component_data in data.items():
            props = component_data.get('props', {})
            designator = props.get('Designator', '')
            
            if not designator:
                for key in ['designator', 'Designator', 'Name']:
                    if key in props:
                        designator = props[key]
                        break
            
            if designator:
                designator = str(designator).strip()
                netlist_data[designator] = {
                    'unique_id': uid,
                    'props': props,
                    'pins': component_data.get('pins', {})
                }
        
        return netlist_data
        
    except Exception as e:
        print(f"Error parsing netlist: {e}")
        traceback.print_exc()
        return {}

def calculate_board_dimensions(pp_data: Dict) -> Dict:
    """Calculate approximate board size from placement coordinates."""
    if not pp_data:
        return {}
    
    all_x = []
    all_y = []
    
    for designator, placement in pp_data.items():
        if 'Mid X' in placement and 'Mid Y' in placement:
            try:
                x = float(str(placement['Mid X']))
                y = float(str(placement['Mid Y']))
                all_x.append(x)
                all_y.append(y)
            except:
                pass
    
    if all_x and all_y:
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        
        # Add 5mm margin for board outline
        margin = 5.0
        min_x -= margin
        max_x += margin
        min_y -= margin
        max_y += margin
        
        return {
            'width_mm': round(max_x - min_x, 1),
            'height_mm': round(max_y - min_y, 1),
            'estimated_board_size': f"{round(max_x - min_x, 1)}mm × {round(max_y - min_y, 1)}mm",
            'component_extent': {
                'min_x_mm': round(min(all_x), 1),
                'max_x_mm': round(max(all_x), 1),
                'min_y_mm': round(min(all_y), 1),
                'max_y_mm': round(max(all_y), 1),
                'width_mm': round(max(all_x) - min(all_x), 1),
                'height_mm': round(max(all_y) - min(all_y), 1),
            },
            'note': "Dimensions estimated from component placement with 5mm margin"
        }
    
    return {}

def check_bom_fields(bom_data: Dict, verbose: bool = True) -> Dict:
    """Check what fields are actually present in the BOM."""
    if not bom_data:
        return {}
    
    sample_component = next(iter(bom_data.values()))
    actual_columns = list(sample_component.keys())
    
    print(f"\n📊 BOM Analysis")
    print(f"   Found {len(actual_columns)} columns, {len(bom_data)} components")
    
    if verbose:
        print("\n" + "="*60)
        print("BOM COLUMNS FOUND")
        print("="*60)
        
        # Group columns
        key_columns = []
        data_columns = []
        
        for col in sorted(actual_columns):
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['designator', 'value', 'footprint', 'comment']):
                key_columns.append(col)
            else:
                data_columns.append(col)
        
        # Key columns with samples
        if key_columns:
            print("\n🔑 KEY COLUMNS:")
            for col in sorted(key_columns):
                samples = []
                for i, (designator, row) in enumerate(bom_data.items()):
                    if i >= 2:
                        break
                    val = row.get(col)
                    if val and str(val).strip() and str(val).lower() != 'nan':
                        samples.append(str(val)[:30])
                sample_str = f" → Samples: {', '.join(samples)}" if samples else ""
                print(f"  • {col}{sample_str}")
        
        # Data columns with completeness
        if data_columns:
            print("\n📋 DATA COLUMNS (completeness):")
            for col in sorted(data_columns):
                populated = sum(1 for row in bom_data.values() 
                              if row.get(col) and str(row.get(col)).strip() 
                              and str(row.get(col)).lower() != 'nan')
                percent = (populated / len(bom_data) * 100) if bom_data else 0
                print(f"  • {col}: {populated}/{len(bom_data)} ({percent:.1f}%)")
        
        print("\n" + "="*60)
        print("ANALYSIS READINESS")
        print("="*60)
        
        # Check minimum fields
        required_fields = ['Designator', 'Value', 'Footprint']
        missing_required = [f for f in required_fields if f not in actual_columns]
        
        if not missing_required:
            print("✅ Has minimum required fields for analysis")
        else:
            print(f"❌ Missing required fields: {', '.join(missing_required)}")
        
        # Check enhanced fields
        enhanced_fields = ['Manufacturer Part', 'Manufacturer', 'Supplier Part']
        missing_enhanced = [f for f in enhanced_fields if f not in actual_columns]
        
        if not missing_enhanced:
            print("✅ Has enhanced fields for better analysis")
        else:
            print(f"⚠️  Missing enhanced fields: {', '.join(missing_enhanced)}")
        
        print("="*60)
    
    # Return statistics
    stats = {}
    for col in actual_columns:
        populated = sum(1 for row in bom_data.values() 
                       if row.get(col) and str(row.get(col)).strip() 
                       and str(row.get(col)).lower() != 'nan')
        stats[col] = {
            'total': len(bom_data),
            'populated': populated,
            'percent': (populated / len(bom_data) * 100) if bom_data else 0
        }
    
    return stats

# ============================================================================
# VERBOSITY-CONTROLLED GENERATION
# ============================================================================
encoding = tiktoken.get_encoding("cl100k_base")

def infer_component_type(designator: str, bom_data: Dict) -> str:
    """Infer component type from designator."""
    prefix = ''.join([c for c in designator if c.isalpha()])
    
    type_map = {
        'R': 'resistor', 'C': 'capacitor', 'L': 'inductor',
        'D': 'diode', 'Q': 'transistor', 'U': 'ic', 'IC': 'ic',
        'J': 'connector', 'CN': 'connector', 'USB': 'connector',
        'SW': 'switch', 'TP': 'test_point', 'M': 'mechanical',
        'X': 'crystal', 'Y': 'crystal', 'LED': 'led',
        'F': 'fuse', 'BT': 'battery', 'RN': 'resistor_array'
    }
    
    return type_map.get(prefix, 'unknown')

def generate_component(designator: str, bom_data: Dict, pp_data: Dict, 
                      netlist_data: Dict, verbosity: int) -> Dict:
    """Generate component entry at specified verbosity level."""
    comp = {'designator': designator}
    
    bom = bom_data.get(designator, {})
    pp = pp_data.get(designator, {})
    netlist = netlist_data.get(designator, {})
    
    # ESSENTIAL: Type and value
    if verbosity >= 1:
        comp['type'] = infer_component_type(designator, bom)
        comp['value'] = bom.get('Value') or bom.get('Comment') or ''
    
    # IMPORTANT: Basic BOM fields
    if verbosity >= 2:
        for field in ['Footprint', 'Comment']:
            if field in bom and bom[field]:
                comp[field.lower()] = bom[field]
    
    # USEFUL: Manufacturer and placement
    if verbosity >= 3:
        for field in ['Manufacturer', 'Manufacturer Part', 'Supplier Part']:
            if field in bom and bom[field]:
                comp[field.lower().replace(' ', '_')] = bom[field]
        
        if pp and 'Mid X' in pp and 'Mid Y' in pp:
            try:
                x = float(str(pp['Mid X']).replace('mm', ''))
                y = float(str(pp['Mid Y']).replace('mm', ''))
                comp['placement'] = {
                    'x_mm': round(x, 3),
                    'y_mm': round(y, 3)
                }
                
                # Add rotation if available
                if 'Rotation' in pp:
                    try:
                        comp['placement']['rotation_deg'] = float(str(pp['Rotation']))
                    except:
                        pass
                
                # Add layer if available
                if 'Layer' in pp and pp['Layer']:
                    comp['placement']['layer'] = str(pp['Layer'])
                    
            except:
                pass
        
        if netlist and 'pins' in netlist:
            pins = netlist['pins']
            if pins:
                comp['pins'] = {pin: net for pin, net in pins.items() if net}
    
    # DETAILED: Additional fields
    if verbosity >= 4:
        for field in ['Tolerance', 'JLCPCB Part Class', 'LCSC Part Name']:
            if field in bom and bom[field]:
                comp[field.lower().replace(' ', '_')] = bom[field]
    
    # EXHAUSTIVE: All original data
    if verbosity >= 5:
        if bom:
            comp['bom_data'] = {k: v for k, v in bom.items() if v is not None}
    
    return comp

def generate_nets(netlist_data: Dict, verbosity: int) -> List[Dict]:
    """Generate net list at specified verbosity."""
    nets_dict = {}
    
    for designator, data in netlist_data.items():
        pins = data.get('pins', {})
        for pin_num, net_name in pins.items():
            if net_name and str(net_name).strip():
                net_name = str(net_name).strip()
                if net_name not in nets_dict:
                    nets_dict[net_name] = []
                nets_dict[net_name].append(f"{designator}-{pin_num}")
    
    nets = []
    for net_name, connections in sorted(nets_dict.items()):
        net_info = {'name': net_name}
        
        if verbosity >= 3:
            net_info['connections'] = sorted(connections)
        elif verbosity >= 2:
            net_info['connection_count'] = len(connections)
            
        nets.append(net_info)
    
    return nets

def get_verbosity_description(level: int) -> str:
    """Get human-readable description of verbosity level."""
    descriptions = {
        1: "ESSENTIAL: Designator, type, value only",
        2: "IMPORTANT: + Footprint, comment",
        3: "USEFUL: + Manufacturer, placement, pin connections",
        4: "DETAILED: + Tolerance, JLCPCB/LCSC details",
        5: "EXHAUSTIVE: + All original BOM fields",
    }
    return descriptions.get(level, f"Level {level}")

def generate_yaml_at_verbosity(bom_data: Dict, pp_data: Dict, 
                              netlist_data: Dict, verbosity: int) -> str:
    """Generate complete YAML at specified verbosity level."""
    all_designators = set(bom_data.keys()) | set(pp_data.keys()) | set(netlist_data.keys())
    
    components = []
    for designator in sorted(all_designators, 
                           key=lambda x: (''.join(filter(str.isalpha, x)),
                                        int(''.join(filter(str.isdigit, x)) or 0))):
        comp = generate_component(designator, bom_data, pp_data, netlist_data, verbosity)
        components.append(comp)
    
    nets = generate_nets(netlist_data, verbosity)
    
    # Build comprehensive metadata
    board_dims = calculate_board_dimensions(pp_data)
    
    metadata = {
        'component_count': len(components),
        'net_count': len(nets),
        'verbosity_level': verbosity,
        'verbosity_description': get_verbosity_description(verbosity),
        'generation_timestamp': datetime.now().isoformat(),
        'generator': 'EasyEDA Parser v1.0',
        
        'data_sources': {
            'bom': 'Bill of Materials: Component specifications, values, manufacturers',
            'pickplace': 'Pick & Place: Physical coordinates, rotation, layer for assembly',
            'netlist': 'Netlist: Electrical pin-to-pin connectivity',
        },
        
        'coordinate_system': {
            'units': 'millimeters (mm)',
            'origin': 'Bottom-left corner of PCB (standard PCB manufacturing coordinates)',
            'x_axis': 'Horizontal, increasing to the right',
            'y_axis': 'Vertical, increasing upward',
            'rotation': 'Degrees, counter-clockwise positive (0° = component oriented as in datasheet)',
            'placement_reference': 'Coordinates are from the component center (Mid X, Mid Y)',
        },
        
        'layer_codes': {
            'T': 'Top layer (components on top side of PCB)',
            'B': 'Bottom layer (components on bottom side)',
        },
        
        'interpretation_notes': [
            'Component types (R=resistor, C=capacitor, L=inductor, U=IC, etc.) are inferred from designator prefixes',
            'Placement coordinates show physical layout - components near each other are functionally related',
            'Net connections show electrical connectivity - components on same net are electrically connected',
            'Rotation 0° means component oriented as shown in datasheet, 90° means rotated 90° counter-clockwise',
            'This data comes from EasyEDA Pro exports and preserves all original information',
        ],
    }
    
    # Add board dimensions if available
    if board_dims:
        metadata['board_dimensions'] = board_dims
        metadata['coordinate_system']['estimated_board_size'] = board_dims['estimated_board_size']
        metadata['coordinate_system']['component_extent'] = board_dims['component_extent']
    
    # Build output structure
    output = {
        'metadata': metadata,
        'components': components,
        'nets': nets
    }
    
    # Add statistics if verbosity is high enough
    if verbosity >= 2:
        type_counts = {}
        for comp in components:
            comp_type = comp.get('type', 'unknown')
            type_counts[comp_type] = type_counts.get(comp_type, 0) + 1
        output['statistics'] = {'component_types': type_counts}
    
    return yaml.dump(output, default_flow_style=False, allow_unicode=True, width=120, sort_keys=False)

def count_tokens(yaml_text: str) -> int:
    """Count tokens using tiktoken cl100k_base encoding (GPT-4o, o1, etc.)."""
    return len(encoding.encode(yaml_text))

# ============================================================================
# PROGRESSIVE REDUCTION LOOP
# ============================================================================
def generate_within_token_limit(bom_data: Dict, pp_data: Dict, 
                               netlist_data: Dict, token_limit: int) -> tuple:
    """
    Generate YAML within token limit using progressive verbosity reduction.
    Returns: (yaml_text, final_verbosity_level, token_count)
    """
    print(f"\nTarget token limit: {token_limit:,}")
    print("Generating with progressive verbosity reduction...")
    print("-" * 50)
    
    # Start at maximum verbosity (5)
    current_verbosity = 5
    
    while current_verbosity >= 1:
        yaml_text = generate_yaml_at_verbosity(bom_data, pp_data, netlist_data, current_verbosity)
        token_count = count_tokens(yaml_text)
        
        print(f"Verbosity {current_verbosity}: {token_count:,} tokens")
        
        if token_count <= token_limit:
            print(f"✓ Success at verbosity {current_verbosity}")
            return yaml_text, current_verbosity, token_count
        
        current_verbosity -= 1
    
    # If we get here, even verbosity 1 is too high
    print(f"✗ Even minimal verbosity exceeds limit")
    return yaml_text, 1, token_count

# ============================================================================
# MAIN FUNCTION
# ============================================================================
def main():
    parser = argparse.ArgumentParser(
        description='Convert EasyEDA Pro exports to YAML for AI analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s BOM.xlsx PickPlace.xlsx Netlist.enet
  %(prog)s BOM.xlsx PickPlace.xlsx Netlist.enet --token-limit 50000
  %(prog)s BOM.xlsx PickPlace.xlsx Netlist.enet --verbosity 3 -o output.yaml
        """
    )
    parser.add_argument('bom_file', help='BOM Excel file (.xlsx)')
    parser.add_argument('pickplace_file', help='Pick & Place Excel file (.xlsx)')
    parser.add_argument('netlist_file', help='Netlist JSON file (.json, .enet)')
    parser.add_argument('--token-limit', '-t', type=int, default=100000,
                       help='Token limit (default: 100,000)')
    parser.add_argument('--output', '-o', default='pcb_analysis.yaml',
                       help='Output YAML file (default: pcb_analysis.yaml)')
    parser.add_argument('--verbosity', '-V', type=int, choices=range(1, 6),
                       help='Force specific verbosity level (1-5, disables token limiting)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed progress information')
    parser.add_argument('--check-only', action='store_true',
                       help='Only check BOM fields, don\'t generate YAML')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("EasyEDA Parser - PCB to YAML Converter")
    print("=" * 60)
    
    # Check files
    for f in [args.bom_file, args.pickplace_file, args.netlist_file]:
        if not Path(f).exists():
            print(f"Error: File not found: {f}")
            sys.exit(1)
    
    print(f"\nInput files:")
    print(f"  BOM:         {args.bom_file}")
    print(f"  Pick & Place: {args.pickplace_file}")
    print(f"  Netlist:     {args.netlist_file}")
    
    # Parse files
    print("\nParsing input files...")
    bom_data = parse_bom(args.bom_file)
    pp_data = parse_pickplace(args.pickplace_file)
    netlist_data = parse_netlist(args.netlist_file)
    
    if not any([bom_data, pp_data, netlist_data]):
        print("Error: No data parsed from any file!")
        sys.exit(1)
    
    print(f"  BOM: {len(bom_data)} designators")
    print(f"  PickPlace: {len(pp_data)} designators")
    print(f"  Netlist: {len(netlist_data)} designators")
    
    # Check BOM fields
    if bom_data:
        check_bom_fields(bom_data, verbose=args.verbose)
    
    # Stop here if check-only mode
    if args.check_only:
        print("\nCheck complete. Exiting without YAML generation.")
        sys.exit(0)
    
    # Generate YAML
    if args.verbosity:
        print(f"\nGenerating at fixed verbosity {args.verbosity}...")
        yaml_text = generate_yaml_at_verbosity(bom_data, pp_data, netlist_data, args.verbosity)
        token_count = count_tokens(yaml_text)
        final_verbosity = args.verbosity
    else:
        yaml_text, final_verbosity, token_count = generate_within_token_limit(
            bom_data, pp_data, netlist_data, args.token_limit
        )
    
    # Save output
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(yaml_text)
    
    # Final report
    print("\n" + "="*60)
    print("CONVERSION COMPLETE")
    print("="*60)
    
    file_size = Path(args.output).stat().st_size
    
    print(f"\nOutput file: {args.output}")
    print(f"File size: {file_size:,} bytes")
    print(f"Token count: {token_count:,}")
    print(f"Verbosity level: {final_verbosity}")
    print(f"  {get_verbosity_description(final_verbosity)}")
    
    if not args.verbosity:
        print(f"\nToken limit: {args.token_limit:,}")
        utilization = token_count / args.token_limit * 100
        print(f"Utilization: {utilization:.1f}%")
        
        if token_count > args.token_limit:
            print("⚠️  Even minimal verbosity exceeds limit")
        elif final_verbosity < 5:
            print(f"✓ Using maximum fitting verbosity")
    
    print(f"\nComponents: {len(set(bom_data.keys()) | set(pp_data.keys()) | set(netlist_data.keys())):,}")
    print(f"Nets: {len(generate_nets(netlist_data, 1)):,}")
    
    print("\n" + "="*60)
    print("Ready for AI analysis!")
    print("="*60)

if __name__ == "__main__":
    main()
