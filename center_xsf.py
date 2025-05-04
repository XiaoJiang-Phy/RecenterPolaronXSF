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

def process_xsf(input_filename, output_filename, datagrid_name=None):
    """
    Reads an XSF file, periodically shifts the specified 3D datagrid to center it,
    removes force components from PRIMCOORD, and writes the result to a new file.

    Args:
        input_filename (str): Path to the input XSF file.
        output_filename (str): Path to the output XSF file.
        datagrid_name (str, optional): If the file contains multiple DATAGRID_3D blocks,
                                       specify the name of the block to process (e.g., 'charge_density').
                                       If None or the file has only one block, the first found block is processed.
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
        # Optional: Print number of points read vs expected
        # print(f"Grid dimensions: {Nx}x{Ny}x{Nz} = {total_data_points} data points")
        # print(f"Data points read: {len(datagrid_data_str)}")

        # Data point count correction
        if len(datagrid_data_str) != total_data_points:
            # Print the warning message about the mismatch
            print(f"Warning: Data point mismatch ({len(datagrid_data_str)} read vs {total_data_points} expected). Adjusting...")
            if len(datagrid_data_str) > total_data_points:
                # Truncate extra data if more points were read
                # print(f"Truncating {len(datagrid_data_str) - total_data_points} extra data points")
                datagrid_data_str = datagrid_data_str[:total_data_points]
            else:
                # Pad with zeros if fewer points were read
                missing_points = total_data_points - len(datagrid_data_str)
                # print(f"Padding {missing_points} missing data points with 0.0")
                datagrid_data_str.extend(['0.0'] * missing_points)

        data_flat = np.array(datagrid_data_str, dtype=float)

        # Crucial: Determine reshape order
        # XSF usually has Z-axis changing fastest (Fortran/Column-major like for Z)
        # Reshaping to (Nx, Ny, Nz) requires order='F'
        # Reshaping to (Nz, Ny, Nx) could use order='C' (default)
        # Assume we want axes 0, 1, 2 to correspond to X, Y, Z
        # Therefore, use (Nx, Ny, Nz) with order='F'
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

    # 5. Flatten Data and Format
    # Crucial: Use the corresponding order when flattening
    shifted_data_flat = shifted_data_3d.flatten(order='F')

    # 6. Write Output XSF File
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
                            # Optional print: print(f"PRIMCOORD block: {primcoord_atom_count} atoms")
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
                                # Assume standard format: AtomType X Y Z (Forces...)
                                # Keep only the first 4 columns
                                # Use fixed-width formatting for better alignment
                                atom_type = parts[0]
                                x = float(parts[1])
                                y = float(parts[2])
                                z = float(parts[3])
                                # Example format: AtomType (left-aligned, 3 chars), Coords (fixed decimal)
                                modified_line = f"  {atom_type:<3} {x:>14.9f} {y:>14.9f} {z:>14.9f}"
                                outfile.write(modified_line + '\n')
                                # Optional print for first atom: 
                                # if primcoord_lines_processed == 0:
                                #    print(f"Processing atom line: '{line}' -> '{modified_line}'")
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

            # Write the shifted data
            data_points_per_line = 6 # Number of data points per line
            for i in range(0, len(shifted_data_flat), data_points_per_line):
                line_data = shifted_data_flat[i:min(i + data_points_per_line, len(shifted_data_flat))]
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

        print(f"Processing complete. Centered data written to '{output_filename}'")
        # print(f"- Force components removed from PRIMCOORD.")
        # print(f"- XSF block structure preserved.")

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

    input_file = default_input_file
    output_file = default_output_file
    grid_to_process = default_grid_to_process

    # --- Command Line Argument Parsing --- 
    if len(sys.argv) == 3:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
    elif len(sys.argv) == 4:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
        grid_to_process = sys.argv[3]
    elif len(sys.argv) != 1: # If run with arguments, but not 3 or 4
        print(f"Usage: python {sys.argv[0]} <input.xsf> <output.xsf> [datagrid_name]")
        sys.exit(1) # Exit if arguments are incorrect
    else:
        # No arguments provided, use defaults and inform the user
        print(f"Usage: python {sys.argv[0]} <input.xsf> <output.xsf> [datagrid_name]")
        print(f"Using default settings: Input='{input_file}', Output='{output_file}'")
        
    # --- Execute Processing --- 
    process_xsf(input_file, output_file, datagrid_name=grid_to_process)