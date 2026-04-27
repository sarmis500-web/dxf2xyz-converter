DXF to XYZ Converter

What it does: converts DXF files (from your Cyclops scanner via InSpeck EM) into 
point cloud files for crystal engraving.

How to use:
1. Click Browse and pick the DXF file.
2. Click Save As, pick the output format (.xyz or .pts), and choose where to save.
3. Pick a preset:
   - UV laser (0.06 mm)   ← use for UV
   - Green laser (0.07 mm) ← use for green beam
   - No thinning           ← every point in the file
4. Click Convert. The stats panel shows points in vs. points written.
5. Open the output preview at the bottom to verify the format looks right
   before sending the file to the engraver.
6. If your engraver wants a different delimiter, units, intensity column, or
   RGB columns, click Advanced and adjust. Common engraver expectations:
   - Some want a comment header: "// X Y Z" on line 1 → set Header to "comment"
   - Some want a count header (PTS-style) → choose .pts as the format
   - Some want an intensity column → set Intensity to "1.0 constant"

If the bounds shown in the stats panel say span > 1000 or < 1, your file is 
probably in unexpected units. Use the scale buttons in Advanced to fix it 
(in→mm, µm→mm, m→mm).

If something doesn't work, the log file at:
- Mac:     ~/.dxf2xyz.log
- Windows: %USERPROFILE%\.dxf2xyz.log
will tell us why. Send that file along with the DXF.
