#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Xiao Jiang
# MIT License
# 
# Description:
# This script processes XCrySDen Structure Format (XSF) files.
# It recenters a specified 3D datagrid using periodic boundary conditions
# and removes atomic force components from the PRIMCOORD block.

import numpy as np
import sys # For command line arguments (optional)

# Add Periodic Table Mapping - Atomic Number to Element Symbol
ELEMENTS = {
    1: 'H', 2: 'He', 3: 'Li', 4: 'Be', 5: 'B', 6: 'C', 7: 'N', 8: 'O', 9: 'F', 10: 'Ne',
    11: 'Na', 12: 'Mg', 13: 'Al', 14: 'Si', 15: 'P', 16: 'S', 17: 'Cl', 18: 'Ar', 19: 'K', 20: 'Ca',
    21: 'Sc', 22: 'Ti', 23: 'V', 24: 'Cr', 25: 'Mn', 26: 'Fe', 27: 'Co', 28: 'Ni', 29: 'Cu', 30: 'Zn',
    31: 'Ga', 32: 'Ge', 33: 'As', 34: 'Se', 35: 'Br', 36: 'Kr', 37: 'Rb', 38: 'Sr', 39: 'Y', 40: 'Zr',
    41: 'Nb', 42: 'Mo', 43: 'Tc', 44: 'Ru', 45: 'Rh', 46: 'Pd', 47: 'Ag', 48: 'Cd', 49: 'In', 50: 'Sn',
    51: 'Sb', 52: 'Te', 53: 'I', 54: 'Xe', 55: 'Cs', 56: 'Ba', 57: 'La', 58: 'Ce', 59: 'Pr', 60: 'Nd',
    61: 'Pm', 62: 'Sm', 63: 'Eu', 64: 'Gd', 65: 'Tb', 66: 'Dy', 67: 'Ho', 68: 'Er', 69: 'Tm', 70: 'Yb',
    71: 'Lu', 72: 'Hf', 73: 'Ta', 74: 'W', 75: 'Re', 76: 'Os', 77: 'Ir', 78: 'Pt', 79: 'Au', 80: 'Hg',
    81: 'Tl', 82: 'Pb', 83: 'Bi', 84: 'Po', 85: 'At', 86: 'Rn', 87: 'Fr', 88: 'Ra', 89: 'Ac', 90: 'Th',
    91: 'Pa', 92: 'U', 93: 'Np', 94: 'Pu', 95: 'Am', 96: 'Cm', 97: 'Bk', 98: 'Cf', 99: 'Es', 100: 'Fm',
    101: 'Md', 102: 'No', 103: 'Lr', 104: 'Rf', 105: 'Db', 106: 'Sg', 107: 'Bh', 108: 'Hs', 109: 'Mt', 110: 'Ds',
    111: 'Rg', 112: 'Cn', 113: 'Nh', 114: 'Fl', 115: 'Mc', 116: 'Lv', 117: 'Ts', 118: 'Og'
}

def process_xsf(input_filename, output_filename, datagrid_name=None, scale_factor=None):
    """
    Reads an XSF file, periodically shifts the specified 3D datagrid to center it,
    removes force components from PRIMCOORD, and writes the result to a new file.

    Args:
        input_filename (str): Path to the input XSF file.
        output_filename (str): Path to the output XSF file.
        datagrid_name (str, optional): If the file contains multiple DATAGRID_3D blocks,
                                       specify the name of the block to process (e.g., 'charge_density').
                                       If None or the file has only one block, the first found block is processed.
        scale_factor (float, optional): If provided, multiply all datagrid values by this factor to scale them.
                                        If None, auto-scaling will be applied to bring maximum value to ~1.0.
    """
    try:
        with open(input_filename, 'r') as infile:
            # Read lines, stripping trailing whitespace and newlines
            lines = [line.rstrip() for line in infile]
    except FileNotFoundError:
        print(f"Error: Input file '{input_filename}' not found.")
        return

    header_lines = []
    datagrid_block_start = None  # Store the BEGIN_BLOCK_DATAGRID_3D line
    datagrid_header = []  # Store header info for the target DATAGRID_3D
    datagrid_block_end = None  # Store the END_BLOCK_DATAGRID_3D line
    datagrid_data_str = []
    footer_lines = []
    grid_dimensions = None
    target_grid_name = None # Store the name of the grid actually found and processed

    # Parsing state
    in_datagrid_block = False
    in_target_block = False
    found_target_grid = False
    current_block_lines = []  # Temporarily store lines of the current data block

    # 1. Parse the XSF file
    i = 0
    while i < len(lines):
        line = lines[i]

        if "BEGIN_BLOCK_DATAGRID_3D" in line:
            in_datagrid_block = True
            current_block_lines = [line]  # Start recording the current block
            
            # Check if the next line is the grid name
            grid_name = None
            if i + 1 < len(lines):
                potential_grid_name_line = lines[i+1]
                # Heuristic: Grid name is usually a single word or simple identifier
                if len(potential_grid_name_line.split()) == 1 and "BEGIN_DATAGRID_3D" not in potential_grid_name_line:
                    grid_name = potential_grid_name_line.strip()
                    current_block_lines.append(grid_name)
                    
                    # Check if this is the grid we are looking for
                    if not found_target_grid and (datagrid_name is None or grid_name == datagrid_name):
                        in_target_block = True
                        found_target_grid = True
                        target_grid_name = grid_name
                        datagrid_block_start = line  # Store block start marker
                    else:
                        in_target_block = False
                    i += 1 # Move past the grid name line
                else:
                    # No separate grid name line found, assume default behavior or handle error
                    if not found_target_grid and datagrid_name is None:
                         # If searching for the first grid and no name is found here, assume this block is it.
                         in_target_block = True
                         found_target_grid = True
                         target_grid_name = "DATAGRID_3D" # Assign a default name
                         datagrid_block_start = line
                    else:
                         in_target_block = False

            i += 1 # Move past BEGIN_BLOCK_DATAGRID_3D
            continue
            
        elif "BEGIN_DATAGRID_3D" in line and in_datagrid_block:
            current_block_lines.append(line)
            
            if in_target_block:
                # If target_grid_name wasn't set earlier (no separate name line)
                if target_grid_name is None or target_grid_name == "DATAGRID_3D":
                    target_grid_name = "DATAGRID_3D" # Use default name
                datagrid_header.append(line)  # BEGIN_DATAGRID_3D line
                
                # Read dimensions and vectors
                if i + 5 < len(lines):  # Check for enough lines
                    # Read dimension line
                    dim_line = lines[i + 1]
                    datagrid_header.append(dim_line)
                    grid_dimensions = tuple(map(int, dim_line.split()))
                    
                    # Read origin and vectors
                    for j in range(2, 6):
                        datagrid_header.append(lines[i + j])
                        current_block_lines.append(lines[i + j])
                    
                    i += 6  # Skip these 5 lines plus the BEGIN_DATAGRID_3D line
                    
                    # Read data until END_DATAGRID_3D
                    while i < len(lines) and "END_DATAGRID_3D" not in lines[i]:
                        current_block_lines.append(lines[i])
                        values = [val for val in lines[i].split() if val.strip()]
                        datagrid_data_str.extend(values)
                        i += 1
                    
                    if i < len(lines):  # Found END_DATAGRID_3D
                        datagrid_header.append(lines[i])  # END_DATAGRID_3D line
                        current_block_lines.append(lines[i])
                        i += 1
                    else:
                        print("Error: XSF file format error, missing END_DATAGRID_3D")
                        return # Or handle differently
                else:
                    print("Error: XSF file format error, missing grid dimension/vector info")
                    return
            else:
                # Non-target block, skip until END_DATAGRID_3D
                i += 1 # Move past BEGIN_DATAGRID_3D
                while i < len(lines) and "END_DATAGRID_3D" not in lines[i]:
                    current_block_lines.append(lines[i])
                    i += 1
                
                if i < len(lines):  # Found END_DATAGRID_3D
                    current_block_lines.append(lines[i])
                    i += 1
                else:
                    print("Warning: Non-target DATAGRID_3D block seems incomplete.")
            
            continue # Continue outer loop
            
        elif "END_BLOCK_DATAGRID_3D" in line and in_datagrid_block:
            current_block_lines.append(line)
            
            if in_target_block:
                datagrid_block_end = line  # Store block end marker
                in_target_block = False # Target block processed
            else:
                # If it was a non-target block, add its lines to header/footer
                # Decide whether to put in header or footer based on whether target was found yet
                if found_target_grid:
                    footer_lines.extend(current_block_lines)
                else:
                    header_lines.extend(current_block_lines)
            
            in_datagrid_block = False
            current_block_lines = []
            i += 1 # Move past END_BLOCK
            
        elif in_datagrid_block:
            # Lines within a block but before/after specific markers
            current_block_lines.append(line)
            # Only add to header/footer if it's definitely not the target block being processed
            # This case might need refinement depending on exact XSF structure variants
            i += 1
                
        elif not in_datagrid_block:
            # Lines outside any DATAGRID block
            if found_target_grid:
                footer_lines.append(line)
            else:
                header_lines.append(line)
            i += 1
        else:
            # Should not happen, advance index to prevent infinite loop
             i += 1

    if not found_target_grid:
        print(f"Error: Target datagrid '{datagrid_name or '(any)'}' not found in '{input_filename}'.")
        return
    if grid_dimensions is None:
        print(f"Error: Dimensions for target datagrid '{target_grid_name}' could not be parsed.")
        return

    Nx, Ny, Nz = grid_dimensions
    total_data_points = Nx * Ny * Nz
    print(f"Processing target grid: '{target_grid_name}', Dimensions: {Nx}x{Ny}x{Nz}")

    # 2. Data Loading and Reshaping
    try:
        # Data point count correction
        if len(datagrid_data_str) != total_data_points:
            # Print the warning message about the mismatch
            print(f"Warning: Data point mismatch ({len(datagrid_data_str)} read vs {total_data_points} expected). Adjusting...")
            if len(datagrid_data_str) > total_data_points:
                # Truncate extra data if more points were read
                datagrid_data_str = datagrid_data_str[:total_data_points]
            else:
                # Pad with zeros if fewer points were read
                missing_points = total_data_points - len(datagrid_data_str)
                datagrid_data_str.extend(['0.0'] * missing_points)

        data_flat = np.array(datagrid_data_str, dtype=float)

        # Reshape to 3D (Nx, Ny, Nz) with order='F' (Fortran-like, Z-axis changes fastest)
        data_3d = data_flat.reshape((Nx, Ny, Nz), order='F')

    except ValueError as e:
        print(f"Error during data processing: {e}")
        print("Possible cause: Non-numeric values in the datagrid or incorrect data format.")
        return
    except Exception as e:
        print(f"An unexpected error occurred during data processing: {e}")
        return

    # 3. Calculate Shift Amount
    shift_x = Nx // 2
    shift_y = Ny // 2
    shift_z = Nz // 2

    # 4. Perform Circular Shift
    # Assume axes 0, 1, 2 correspond to X, Y, Z (determined by reshape)
    shifted_data_3d = np.roll(data_3d, shift=(shift_x, shift_y, shift_z), axis=(0, 1, 2))

    # 5. Scale the data
    # Determine max value for scaling info
    max_value = np.max(np.abs(shifted_data_3d))
    print(f"Original data maximum value: {max_value:.6E}")
    
    # Determine scale factor
    if scale_factor is None:
        # Auto-scaling: target maximum value of ~10.0
        if max_value > 0:
            scale_factor = 10.0 / max_value
        else:
            scale_factor = 10.0
        print(f"Auto-scaling factor: {scale_factor:.6E}")
    else:
        print(f"Applying specified scaling factor: {scale_factor:.6E}")
    
    # Apply scaling
    scaled_data_3d = shifted_data_3d * scale_factor
    print(f"Scaled data maximum value: {np.max(np.abs(scaled_data_3d)):.6f}")
    
    # 6. Flatten Data
    scaled_data_flat = scaled_data_3d.flatten(order='F')

    # 7. Write Output XSF File
    try:
        with open(output_filename, 'w') as outfile:
            # Write original header and atom info (processing PRIMCOORD)
            in_primcoord = False
            primcoord_atom_count = 0
            primcoord_lines_processed = 0
            primcoord_header_line_processed = False # Flag to track if the atom count line is processed

            # Add tracking for PRIMVEC
            primvec_lines = []
            in_primvec = False
            primvec_lines_count = 0
            convvec_added = False

            for line in header_lines:
                if "PRIMVEC" in line:
                    in_primvec = True
                    primvec_lines = [line]
                    outfile.write(line + '\n')
                    continue
                
                if in_primvec:
                    primvec_lines.append(line)
                    outfile.write(line + '\n')
                    primvec_lines_count += 1
                    # After reading 3 lines (3 vectors), add CONVVEC block with the same values
                    if primvec_lines_count == 3:
                        in_primvec = False
                        # Add CONVVEC immediately after PRIMVEC with the same coordinates
                        outfile.write("CONVVEC\n")
                        # Write the same vector values from PRIMVEC to CONVVEC
                        for i in range(1, 4):  # Skip the PRIMVEC line itself
                            outfile.write(primvec_lines[i] + '\n')
                        convvec_added = True
                    continue

                if "PRIMCOORD" in line:
                    in_primcoord = True
                    outfile.write(line + '\n') # Add newline uniformly
                    continue

                if in_primcoord:
                    if not primcoord_header_line_processed:
                        # This is the line after PRIMCOORD, containing atom count
                        try:
                            parts = line.split()
                            if len(parts) >= 1:
                                primcoord_atom_count = int(parts[0])
                            # Modify the second parameter if it indicates forces (1=forces, 0=no forces)
                            if len(parts) > 1 and parts[1] == '1':
                                parts[1] = '0'  # Change force flag to 0
                                # Keep original spacing if possible, otherwise use a default
                                modified_line = f"  {parts[0]:<4} {parts[1]:>5}" # Example spacing
                                outfile.write(modified_line + '\n')
                            else:
                                outfile.write(line + '\n') # Write original line + newline
                            primcoord_header_line_processed = True
                        except (ValueError, IndexError):
                            # Handle cases where the line might not be the expected format
                            outfile.write(line + '\n')
                            in_primcoord = False # Assume invalid PRIMCOORD structure
                        continue

                    elif primcoord_lines_processed < primcoord_atom_count:
                        parts = line.split()
                        # Identify atom coordinate lines based on features: at least 4 columns
                        if len(parts) >= 4:
                            try:
                                # Try to convert atom type to element symbol
                                atom_type = parts[0]
                                try:
                                    atom_number = int(atom_type)
                                    # If successfully converted to number, look up element symbol
                                    if atom_number in ELEMENTS:
                                        atom_type = ELEMENTS[atom_number]
                                except ValueError:
                                    # If already an element symbol, keep it unchanged
                                    pass
                                    
                                x = float(parts[1])
                                y = float(parts[2])
                                z = float(parts[3])
                                # Example format: AtomType (left-aligned, 3 chars), Coords (fixed decimal)
                                modified_line = f"  {atom_type:<3} {x:>14.9f} {y:>14.9f} {z:>14.9f}"
                                outfile.write(modified_line + '\n')
                            except (ValueError, IndexError):
                                 # If conversion fails, write original line
                                 outfile.write(line + '\n')
                        else:
                            # Not a standard atom line, write as-is
                            outfile.write(line + '\n')
                        primcoord_lines_processed += 1
                        if primcoord_lines_processed == primcoord_atom_count:
                            in_primcoord = False # Finished processing atom lines
                        continue

                    else:
                         # Should not happen if count is correct, but handles extra lines
                         in_primcoord = False # Exit PRIMCOORD processing

                # Write lines outside PRIMCOORD or after finishing it
                if not in_primcoord:
                    outfile.write(line + '\n')

            # Write the start of the target DATAGRID block
            if datagrid_block_start:
                 outfile.write(datagrid_block_start + '\n') # BEGIN_BLOCK_DATAGRID_3D
            if target_grid_name: # Write grid name if found (e.g., 3D_field)
                 # Ensure grid name is not the BEGIN_DATAGRID line itself
                 if not target_grid_name.startswith("BEGIN_DATAGRID_3D"):
                     outfile.write(target_grid_name + '\n')
            
            # Write the DATAGRID_3D specific header (BEGIN_DATAGRID_3D..., dims, origin, vectors)
            # datagrid_header should contain [BEGIN_DATAGRID_3D..., dim, orig, vec1, vec2, vec3, END_DATAGRID_3D]
            if datagrid_header:
                # Write all header lines stored in datagrid_header *except* the last one (END_DATAGRID_3D)
                for header_line in datagrid_header[:-1]: 
                    outfile.write(header_line + '\n')
            else:
                print("Error: Internal processing error - datagrid_header is empty during write.")
                # Potentially exit or handle error

            # Write the scaled data
            data_points_per_line = 6 # Number of data points per line
            for i in range(0, len(scaled_data_flat), data_points_per_line):
                line_data = scaled_data_flat[i:min(i + data_points_per_line, len(scaled_data_flat))]
                # format_str = " {:16.8E}" * len(line_data) # Example format
                format_str = " ".join(["{:.8E}"] * len(line_data)) # Simpler formatting
                outfile.write(format_str.format(*line_data) + '\n') # Ensure only one newline at the end

            # Write the DATAGRID_3D end marker
            if datagrid_header and datagrid_header[-1].strip().startswith("END_DATAGRID_3D"):
                outfile.write(datagrid_header[-1] + '\n') # Write the captured END line
            else:
                print("Warning: END_DATAGRID_3D marker missing or incorrect in parsed header, adding standard marker.")
                outfile.write("END_DATAGRID_3D\n")

            
            # Write the end of the DATAGRID block
            if datagrid_block_end:
                outfile.write(datagrid_block_end + '\n')
            else:
                print("Warning: END_BLOCK_DATAGRID_3D marker missing, file might be incomplete.")

            
            # Write the file footer (any content after the target block)
            for footer_line in footer_lines:
                outfile.write(footer_line + '\n')

        print(f"Processing complete. Centered and scaled data written to '{output_filename}'")
        print(f"- Applied scaling factor: {scale_factor:.6E}")
        print(f"- Scaled data maximum value: {np.max(np.abs(scaled_data_3d)):.6f}")

    except IOError as e:
        print(f"Error: Could not write to output file '{output_filename}' - {e}")
    except Exception as e:
        print(f"An unexpected error occurred during file writing: {e}")
        import traceback
        traceback.print_exc()


# --- Main execution block --- 
if __name__ == "__main__":
    # --- Default Configuration --- 
    default_input_file = "psir_plrn.xsf"  # Default input filename
    default_output_file = "psir_plrn_centered.xsf" # Default output filename
    default_grid_to_process = None # Process the first found DATAGRID_3D
    default_scale_factor = None  # Auto-scaling by default

    input_file = default_input_file
    output_file = default_output_file
    grid_to_process = default_grid_to_process
    scale_factor = default_scale_factor

    # --- Command Line Argument Parsing --- 
    if len(sys.argv) >= 3:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
        
        if len(sys.argv) >= 4:
            # Third argument could be either grid name or scale factor
            try:
                # Try to interpret as scale factor (float)
                scale_factor = float(sys.argv[3])
                print(f"Using specified scaling factor: {scale_factor}")
                
                # If there's a 5th argument, it's the grid name
                if len(sys.argv) >= 5:
                    grid_to_process = sys.argv[4]
            except ValueError:
                # Not a number, interpret as grid name
                grid_to_process = sys.argv[3]
                
                # If there's a 5th argument, it's the scale factor
                if len(sys.argv) >= 5:
                    try:
                        scale_factor = float(sys.argv[4])
                        print(f"Using specified scaling factor: {scale_factor}")
                    except ValueError:
                        print(f"Warning: Could not parse '{sys.argv[4]}' as a scaling factor. Using auto-scaling.")
    elif len(sys.argv) != 1: # If run with arguments, but incorrect number
        print(f"Usage: python {sys.argv[0]} <input.xsf> <output.xsf> [scale_factor|datagrid_name] [datagrid_name|scale_factor]")
        sys.exit(1) # Exit if arguments are incorrect
    else:
        # No arguments provided, use defaults and inform the user
        print(f"Usage: python {sys.argv[0]} <input.xsf> <output.xsf> [scale_factor|datagrid_name] [datagrid_name|scale_factor]")
        print(f"Using default settings: Input='{input_file}', Output='{output_file}', Auto-scaling")
        
    # --- Execute Processing --- 
    process_xsf(input_file, output_file, datagrid_name=grid_to_process, scale_factor=scale_factor)