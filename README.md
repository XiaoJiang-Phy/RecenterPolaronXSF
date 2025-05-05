# RecenterPolaronXSF

This Python script (`center_xsf.py`) processes XCrySDen Structure Format (XSF) files to facilitate visualization, particularly for data affected by periodic boundary conditions.

## Features

* **Recenter 3D Datagrid**: Reads a specified `DATAGRID_3D` block (or the first one found) and applies a periodic shift (`numpy.roll`) to center the data within the unit cell. This is useful for visualizing features like polarons that might wrap around boundaries.
* **Remove Atomic Forces**: Reads the `PRIMCOORD` block, removes force components (typically the last three columns) from each atom coordinate line, and sets the force flag (second number after `PRIMCOORD`) to `0`.
* **Data Scaling**: Automatically or manually scales data values to bring the maximum value close to 10.0. This helps achieve better display in visualization tools.
* **Atomic Number to Element Symbol Conversion**: Converts numeric atom types (e.g., 1, 8) to corresponding element symbols (e.g., H, O).
* **Preserve File Structure**: Retains the overall XSF format, including other data blocks and header/footer information.
* **Flexible Datagrid Selection**: Allows specifying a target `DATAGRID_3D` block by name if the input file contains multiple blocks.
* **Automatic CONVVEC Addition**: Automatically adds a CONVVEC block after the PRIMVEC block, using the same vector values.

## Dependencies

* Python 3.x
* NumPy (`pip install numpy`)

## Usage

The script is primarily designed to be run from the command line:

```bash
python center_xsf.py <input.xsf> <output.xsf> [scale_factor|datagrid_name] [datagrid_name|scale_factor]
```

**Arguments:**

* `<input.xsf>`: (Required) Path to the input XSF file.
* `<output.xsf>`: (Required) Path where the processed XSF file will be saved.
* `[scale_factor|datagrid_name]`: (Optional) Data scaling factor (float) or the specific name of the `DATAGRID_3D` block to process.
* `[datagrid_name|scale_factor]`: (Optional) If the third argument is a datagrid name, the fourth can be a scaling factor; vice versa.

**Examples:**

```bash
# Process the first datagrid in psir_plrn.xsf and save to psir_plrn_centered.xsf
python center_xsf.py psir_plrn.xsf psir_plrn_centered.xsf

# Process the first datagrid in psir_plrn.xsf, apply scaling factor 5.0, and save to psir_plrn_centered.xsf
python center_xsf.py psir_plrn.xsf psir_plrn_centered.xsf 5.0

# Process the datagrid named "charge_density" in psir_plrn.xsf and save to psir_plrn_centered.xsf
python center_xsf.py psir_plrn.xsf psir_plrn_centered.xsf charge_density
```

If run without any command-line arguments, the script will use default filenames (`psir_plrn.xsf` as input, `psir_plrn_centered.xsf` as output) and process the first datagrid found.

## Technical Notes

* **Data Order**: Assumes the 3D data in the XSF file is stored with the Z-axis changing fastest (Fortran-like order, `order='F'` in NumPy).
* **Atom Coordinate Parsing**: Identifies atom lines in `PRIMCOORD` as lines containing at least 4 columns. It retains the first 4 columns (AtomType, X, Y, Z) and discards the rest.
* **Element Mapping**: Includes complete mapping from atomic numbers (1-118) to element symbols.
* **Auto-scaling**: If no scaling factor is specified, the script will automatically calculate one to bring the maximum data value close to 10.0.
* **Error Handling**: Includes basic checks for file existence, datagrid presence, dimension parsing, and data point counts (with warnings/adjustments for mismatches).

## License

MIT License
