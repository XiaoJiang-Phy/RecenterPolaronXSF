# RecenterPolaronXSF (or your chosen repository name)

A simple Python script to recenter 3D grid data, such as polaron real-space distributions from EPW calculations, within XSF files. It fixes visualization artifacts caused by periodic boundary condition (PBC) wrapping by applying a circular shift using NumPy.

When calculating properties like polaron distributions in periodic systems, the localized feature might be centered near the cell boundary or origin. Due to PBC, visualization tools showing only a single unit cell will often display this feature as fragmented across the corners or edges of the cell box. This script rearranges the data within the grid to present a centered, contiguous view of the feature within a single cell.

## Requirements

* Python 3.x
* NumPy

## Usage

Run the script from your terminal. You need to provide the input XSF file path and the desired output file path. Optionally, you can specify the name of the data grid if your XSF file contains multiple `DATAGRID_3D` blocks.

```bash
python center_xsf.py <input.xsf> <output_centered.xsf> [datagrid_name]
